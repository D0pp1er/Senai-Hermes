"""Protected per-bot conversation drafts, separate from queue and scheduler DBs."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3


class ConversationState:
    def __init__(self, path, namespace):
        self.path = Path(path).absolute()
        if any(parent.is_symlink() for parent in (self.path, *self.path.parents)):
            raise ValueError('Conversation state cannot be symlinked.')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS namespace (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS drafts (user_id INTEGER NOT NULL, chat_id INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(user_id,chat_id))')
            value = json.dumps(namespace, sort_keys=True)
            db.execute('INSERT OR IGNORE INTO namespace VALUES (1,?)', (value,))
            if db.execute('SELECT value FROM namespace WHERE id=1').fetchone()[0] != value:
                raise ValueError('Conversation state belongs to a different bot/project.')
        self.path.chmod(0o600)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, user, chat):
        with self.connection() as db:
            row = db.execute('SELECT data FROM drafts WHERE user_id=? AND chat_id=?', (user, chat)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, user, chat, value):
        with self.connection() as db:
            db.execute('INSERT INTO drafts VALUES (?,?,?) ON CONFLICT(user_id,chat_id) DO UPDATE SET data=excluded.data',
                       (user, chat, json.dumps(value, allow_nan=False)))

    def delete(self, user, chat):
        with self.connection() as db:
            db.execute('DELETE FROM drafts WHERE user_id=? AND chat_id=?', (user, chat))

    def claim_confirmation(self, user, chat, draft_id):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM drafts WHERE user_id=? AND chat_id=?', (user, chat)).fetchone()
            value = json.loads(row[0]) if row else None
            if value is None or value['id'] != draft_id or value['phase'] != 'confirm':
                return False
            value['phase'] = 'creating'
            db.execute('UPDATE drafts SET data=? WHERE user_id=? AND chat_id=?', (json.dumps(value), user, chat))
            return True
