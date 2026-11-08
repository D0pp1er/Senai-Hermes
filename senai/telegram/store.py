"""SQLite update cursor, single-worker queue, and result-delivery outbox."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
import uuid


class JobStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as database:
            database.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
                INSERT OR IGNORE INTO settings VALUES ('offset', 0);
                CREATE TABLE IF NOT EXISTS sessions (name TEXT PRIMARY KEY, session_id TEXT NOT NULL, updated REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                    prompt TEXT NOT NULL, session_id TEXT, status TEXT NOT NULL, result TEXT NOT NULL DEFAULT '',
                    parts_sent INTEGER NOT NULL DEFAULT 0, delivered INTEGER NOT NULL DEFAULT 0,
                    created REAL NOT NULL, updated REAL NOT NULL
                );
            """)
            columns = {row['name'] for row in database.execute('PRAGMA table_info(jobs)')}
            if 'session_id' not in columns:
                database.execute('ALTER TABLE jobs ADD COLUMN session_id TEXT')
        self.path.chmod(0o600)

    @contextmanager
    def connection(self):
        database = sqlite3.connect(self.path, timeout=10)
        database.row_factory = sqlite3.Row
        try:
            with database:
                yield database
        finally:
            database.close()

    def offset(self):
        with self.connection() as database:
            return database.execute("SELECT value FROM settings WHERE key='offset'").fetchone()[0]

    def set_offset(self, value):
        with self.connection() as database:
            database.execute("UPDATE settings SET value=? WHERE key='offset'", (value,))

    def consume(self, identifier, job=None, *, max_pending=4):
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            cursor = database.execute("SELECT value FROM settings WHERE key='offset'").fetchone()[0]
            if identifier < cursor:
                return 'duplicate'
            result = 'ignored'
            if job is not None:
                if database.execute('SELECT 1 FROM jobs WHERE id=?', (identifier,)).fetchone():
                    database.execute("UPDATE settings SET value=? WHERE key='offset'", (identifier + 1,))
                    return 'duplicate'
                count = database.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
                if count >= max_pending:
                    result = 'busy'
                else:
                    now = time.time()
                    database.execute(
                        'INSERT INTO jobs(id,chat_id,user_id,prompt,status,created,updated) VALUES (?,?,?,?,?,?,?)',
                        (identifier, job['chat_id'], job['user_id'], job['prompt'], 'queued', now, now),
                    )
                    result = 'queued'
            database.execute("UPDATE settings SET value=? WHERE key='offset'", (identifier + 1,))
            return result

    def claim_next(self):
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            job = database.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1").fetchone()
            if job is None:
                return None
            database.execute("UPDATE jobs SET status='running',updated=? WHERE id=?", (time.time(), job['id']))
            result = dict(job)
            result['status'] = 'running'
            return result

    def finish(self, identifier, status, result):
        if status not in ('succeeded', 'failed', 'interrupted'):
            raise ValueError('Invalid terminal job status.')
        with self.connection() as database:
            database.execute(
                "UPDATE jobs SET status=?,result=?,parts_sent=0,delivered=0,updated=? WHERE id=? AND status='running'",
                (status, result, time.time(), identifier),
            )

    def recover_interrupted(self):
        with self.connection() as database:
            database.execute(
                "UPDATE jobs SET status='interrupted',result=?,parts_sent=0,delivered=0,updated=? WHERE status='running'",
                ('The bot stopped during this request. It was not automatically retried. Inspect outputs/ before resubmitting.', time.time()),
            )

    def recent(self, chat_id):
        with self.connection() as database:
            return [dict(row) for row in database.execute('SELECT * FROM jobs WHERE chat_id=? ORDER BY id DESC LIMIT 3', (chat_id,))]

    def latest_completed(self, chat_id):
        with self.connection() as database:
            row = database.execute("SELECT * FROM jobs WHERE chat_id=? AND status IN ('succeeded','failed','interrupted') ORDER BY id DESC LIMIT 1", (chat_id,)).fetchone()
            return dict(row) if row is not None else None

    def pending_results(self):
        with self.connection() as database:
            return [dict(row) for row in database.execute("SELECT * FROM jobs WHERE status IN ('succeeded','failed','interrupted') AND delivered=0 ORDER BY id LIMIT 10")]

    def mark_part_sent(self, identifier):
        with self.connection() as database:
            database.execute('UPDATE jobs SET parts_sent=parts_sent+1 WHERE id=?', (identifier,))

    def mark_delivered(self, identifier):
        with self.connection() as database:
            database.execute('UPDATE jobs SET delivered=1 WHERE id=?', (identifier,))

    def shared_session(self):
        with self.connection() as database:
            row = database.execute("SELECT session_id FROM sessions WHERE name='telegram-shared'").fetchone()
            return row[0] if row else None

    def bind_shared_session(self, session_id, job_id=None):
        session_id = str(uuid.UUID(session_id))
        with self.connection() as database:
            database.execute('BEGIN IMMEDIATE')
            row = database.execute("SELECT session_id FROM sessions WHERE name='telegram-shared'").fetchone()
            if row and row[0] != session_id:
                raise ValueError('Codex returned a different session; the shared session mapping was preserved.')
            database.execute("INSERT OR IGNORE INTO sessions(name,session_id,updated) VALUES ('telegram-shared',?,?)", (session_id, time.time()))
            if job_id is not None:
                database.execute('UPDATE jobs SET session_id=? WHERE id=?', (session_id, job_id))

    def unbound_running_jobs(self):
        with self.connection() as database:
            return [dict(row) for row in database.execute("SELECT * FROM jobs WHERE status='running' AND session_id IS NULL ORDER BY created,id")]
