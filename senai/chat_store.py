"""Project-local durable CLI chat transcripts, isolated from Telegram state."""
from contextlib import closing, contextmanager
import fcntl
import os
from pathlib import Path
import sqlite3
import uuid


class ChatStore:
    def __init__(self, workspace):
        self.directory = Path(workspace) / ".senai-chat"
        if self.directory.is_symlink():
            raise ValueError("Chat history directory cannot be a symlink.")
        self.directory.mkdir(mode=0o700, exist_ok=True)
        self.directory.chmod(0o700)
        self.path = self.directory / "history.sqlite3"
        self._private_file(self.path)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, installation TEXT NOT NULL,
                    native_id TEXT, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE TABLE IF NOT EXISTS active (
                    installation TEXT PRIMARY KEY, session TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY, session TEXT NOT NULL,
                    request TEXT NOT NULL, response TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL CHECK(status IN ('pending','completed','unknown')),
                    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """)

    @staticmethod
    def _private_file(path):
        if path.is_symlink():
            raise ValueError("Chat state cannot be a symlink.")
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(fd, 0o600)
        finally:
            os.close(fd)

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            with db:
                yield db

    @contextmanager
    def exclusive(self):
        path = self.directory / "chat.lock"
        self._private_file(path)
        with path.open('r+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError("Another Senai chat is running for this project.") from None
            try:
                # Only after obtaining the execution lock: never rewrite a live turn.
                with self.connection() as db:
                    db.execute("UPDATE turns SET status='unknown', response='Interrupted; effects unknown. Inspect before starting new work.' WHERE status='pending'")
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def session(self, identifier, installation):
        with self.connection() as db:
            row = db.execute("SELECT * FROM sessions WHERE id=? AND installation=?",
                             (identifier, installation)).fetchone()
        if row is None:
            raise ValueError("Unknown chat session for this project/installation. Use /sessions.")
        return dict(row)

    def select(self, installation, *, identifier=None, fresh=False):
        with self.connection() as db:
            if identifier is None and not fresh:
                row = db.execute("SELECT session FROM active WHERE installation=?", (installation,)).fetchone()
                identifier = row[0] if row else None
            if identifier is None:
                identifier = str(uuid.uuid4())
                db.execute("INSERT INTO sessions(id,installation) VALUES (?,?)", (identifier, installation))
            else:
                self.session(identifier, installation)
            db.execute("INSERT OR REPLACE INTO active(installation,session) VALUES (?,?)", (installation, identifier))
        return self.session(identifier, installation)

    def sessions(self, installation):
        with self.connection() as db:
            return [dict(row) for row in db.execute("SELECT * FROM sessions WHERE installation=? ORDER BY rowid", (installation,))]

    def bind(self, identifier, installation, native_id):
        if not isinstance(native_id, str):
            raise ValueError("Codex did not return a valid native session ID.")
        native_id = str(uuid.UUID(native_id))
        with self.connection() as db:
            row = db.execute("SELECT native_id FROM sessions WHERE id=? AND installation=?", (identifier, installation)).fetchone()
            if row is None or (row[0] is not None and row[0] != native_id):
                raise ValueError("Native session changed unexpectedly; original chat mapping preserved.")
            db.execute("UPDATE sessions SET native_id=? WHERE id=?", (native_id, identifier))

    def begin(self, identifier, request):
        with self.connection() as db:
            if db.execute("SELECT 1 FROM turns WHERE session=? AND status!='completed'", (identifier,)).fetchone():
                raise ValueError("Chat has an unknown turn. Inspect /history and its effects; use /new explicitly. It will not be repeated automatically.")
            return db.execute("INSERT INTO turns(session,request,status) VALUES (?,?,'pending')", (identifier, request)).lastrowid

    def finish(self, turn, response, *, status='completed'):
        with self.connection() as db:
            changed = db.execute("UPDATE turns SET response=?,status=? WHERE id=? AND status='pending'", (response, status, turn)).rowcount
            if changed != 1:
                raise ValueError("Chat turn already finalized; history was preserved.")

    def history(self, installation, identifier=None, *, limit=200):
        query = "SELECT t.*,s.native_id FROM turns t JOIN sessions s ON s.id=t.session WHERE s.installation=?"
        values = [installation]
        if identifier is not None:
            query += " AND t.session=?"
            values.append(identifier)
        query += " ORDER BY t.id DESC LIMIT ?"
        values.append(limit)
        with self.connection() as db:
            return list(reversed([dict(row) for row in db.execute(query, values)]))
