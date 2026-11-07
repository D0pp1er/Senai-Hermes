"""SQLite update cursor, single-worker queue, and result-delivery outbox."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time


class JobStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as database:
            database.executescript("""
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value INTEGER NOT NULL);
                INSERT OR IGNORE INTO settings VALUES ('offset', 0);
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                    prompt TEXT NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL DEFAULT '',
                    parts_sent INTEGER NOT NULL DEFAULT 0, delivered INTEGER NOT NULL DEFAULT 0,
                    created REAL NOT NULL, updated REAL NOT NULL
                );
            """)
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

    def pending_results(self):
        with self.connection() as database:
            return [dict(row) for row in database.execute("SELECT * FROM jobs WHERE status IN ('succeeded','failed','interrupted') AND delivered=0 ORDER BY id LIMIT 10")]

    def mark_part_sent(self, identifier):
        with self.connection() as database:
            database.execute('UPDATE jobs SET parts_sent=parts_sent+1 WHERE id=?', (identifier,))

    def mark_delivered(self, identifier):
        with self.connection() as database:
            database.execute('UPDATE jobs SET delivered=1 WHERE id=?', (identifier,))
