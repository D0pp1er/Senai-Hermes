import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def timestamp(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("an aware datetime is required")
    return value.timestamp()


class Store:
    def __init__(self, path, *, clock=None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock or (lambda: datetime.now(dt_timezone.utc))
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL,
                    prompt TEXT NOT NULL, project TEXT NOT NULL, scope TEXT NOT NULL,
                    timezone TEXT NOT NULL, enabled INTEGER NOT NULL,
                    next_due REAL, every REAL, retries INTEGER, retry_delay REAL);
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL,
                    scheduled_at REAL NOT NULL, snapshot TEXT NOT NULL,
                    status TEXT NOT NULL, attempt INTEGER NOT NULL,
                    ready_at REAL NOT NULL, result TEXT, error TEXT,
                    delivery_error TEXT);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, *, name, prompt, project, scope, at, timezone="Asia/Dhaka",
               every=None, retries=0, retry_delay=60):
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, TypeError) as exc:
            raise ValueError("invalid timezone") from exc
        due = timestamp(at)
        if not all(isinstance(x, str) and x.strip() for x in (name, prompt, scope)):
            raise ValueError("name, prompt and scope are required")
        if every is not None and (not isinstance(every, int) or every < 1):
            raise ValueError("every must be positive seconds")
        if not isinstance(retries, int) or not 0 <= retries <= 10 or retry_delay < 1:
            raise ValueError("invalid retry policy")
        project = str(Path(project).resolve(strict=True))
        if not Path(project).is_dir():
            raise ValueError("project must be a directory")
        ident = uuid.uuid4().hex
        with self.connection() as db:
            db.execute("INSERT INTO schedules VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (ident, name, prompt, project, scope, timezone, 1, due,
                        every, retries, retry_delay))
        return ident

    def list(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM schedules ORDER BY rowid")]

    def runs(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM runs ORDER BY rowid")]

    def pause(self, ident):
        self._enabled(ident, False)

    def resume(self, ident):
        self._enabled(ident, True)

    def _enabled(self, ident, enabled):
        with self.connection() as db:
            if not db.execute("UPDATE schedules SET enabled=? WHERE id=?", (enabled, ident)).rowcount:
                raise KeyError(ident)

    def delete(self, ident):
        with self.connection() as db:
            if not db.execute("DELETE FROM schedules WHERE id=?", (ident,)).rowcount:
                raise KeyError(ident)

    def claim(self):
        now = timestamp(self.clock())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            retry = db.execute("""SELECT r.* FROM runs r JOIN schedules s ON s.id=r.schedule_id
                WHERE r.status='retry' AND r.ready_at<=? AND s.enabled=1
                ORDER BY r.ready_at LIMIT 1""", (now,)).fetchone()
            if retry:
                db.execute("UPDATE runs SET status='running', attempt=attempt+1 WHERE id=?", (retry['id'],))
                row = dict(retry)
                row.update(status='running', attempt=row['attempt']+1)
                return row
            job = db.execute("""SELECT * FROM schedules s WHERE enabled=1 AND next_due<=?
                AND NOT EXISTS (SELECT 1 FROM runs r WHERE r.schedule_id=s.id
                    AND r.status IN ('running','retry')) ORDER BY next_due LIMIT 1""", (now,)).fetchone()
            if job is None:
                return None
            job = dict(job)
            due = job['next_due']
            next_due = None if job['every'] is None else due + (int((now-due)//job['every'])+1)*job['every']
            db.execute("UPDATE schedules SET next_due=? WHERE id=?", (next_due, job['id']))
            row = dict(id=uuid.uuid4().hex, schedule_id=job['id'], scheduled_at=due,
                       snapshot=json.dumps(job), status='running', attempt=1, ready_at=now,
                       result=None, error=None, delivery_error=None)
            db.execute("INSERT INTO runs VALUES (:id,:schedule_id,:scheduled_at,:snapshot,:status,:attempt,:ready_at,:result,:error,:delivery_error)", row)
            return row

    def finish(self, ident, *, result=None, error=None):
        now = timestamp(self.clock())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM runs WHERE id=? AND status='running'", (ident,)).fetchone()
            if row is None:
                raise ValueError("run is not running")
            policy = json.loads(row['snapshot'])
            status = 'succeeded' if error is None else 'failed'
            if error is not None and row['attempt'] <= policy['retries']:
                status = 'retry'
            db.execute("UPDATE runs SET status=?,result=?,error=?,ready_at=? WHERE id=?",
                       (status, result, error, now+policy['retry_delay'], ident))

    def interrupt(self, ident):
        # Operator must first establish the old worker has stopped.
        with self.connection() as db:
            if not db.execute("UPDATE runs SET status='interrupted' WHERE id=? AND status='running'", (ident,)).rowcount:
                raise ValueError("run is not running")

    def delivery_failed(self, ident, error):
        with self.connection() as db:
            db.execute("UPDATE runs SET delivery_error=? WHERE id=?", (error, ident))
