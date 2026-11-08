import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .calendar import next_after, advance


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
                CREATE TABLE IF NOT EXISTS deliveries (
                    id TEXT PRIMARY KEY, run_id TEXT UNIQUE NOT NULL,
                    target TEXT NOT NULL, status TEXT NOT NULL,
                    attempt INTEGER NOT NULL DEFAULT 0, ready_at REAL NOT NULL,
                    token TEXT, error TEXT);
            """)
            db.execute("BEGIN IMMEDIATE")
            columns = {r['name'] for r in db.execute("PRAGMA table_info(schedules)")}
            additions = {'delivery_target': 'TEXT', 'cron': 'TEXT',
                         'misfire': "TEXT NOT NULL DEFAULT 'coalesce'",
                         'grace_seconds': 'INTEGER NOT NULL DEFAULT 120'}
            for name, definition in additions.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE schedules ADD COLUMN {name} {definition}")
            db.execute("""CREATE TABLE IF NOT EXISTS misfires (
                id TEXT PRIMARY KEY, schedule_id TEXT NOT NULL, first_due REAL NOT NULL,
                observed_at REAL NOT NULL, missed_count INTEGER NOT NULL,
                count_capped INTEGER NOT NULL, reason TEXT NOT NULL)""")

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
               every=None, retries=0, retry_delay=60, delivery_target=None,
               cron=None, misfire="coalesce", grace_seconds=120):
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, TypeError) as exc:
            raise ValueError("invalid timezone") from exc
        if delivery_target is not None:
            if not isinstance(delivery_target, dict) or not delivery_target:
                raise ValueError("delivery_target must be a nonempty JSON object")
            delivery_target = json.dumps(delivery_target, allow_nan=False)
        due = timestamp(at)
        if misfire not in ('coalesce', 'skip'):
            raise ValueError('misfire must be coalesce or skip')
        if type(grace_seconds) is not int or not 0 <= grace_seconds <= 86400:
            raise ValueError('grace_seconds must be an integer from 0 to 86400')
        if cron is not None:
            if every is not None:
                raise ValueError('cron and every are mutually exclusive')
            due = next_after(cron, timezone, due-0.000001)
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
            db.execute("INSERT INTO schedules (id,name,prompt,project,scope,timezone,enabled,next_due,every,retries,retry_delay,delivery_target,cron,misfire,grace_seconds) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                       (ident, name, prompt, project, scope, timezone, 1, due,
                        every, retries, retry_delay, delivery_target, cron, misfire, grace_seconds))
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
            jobs = db.execute("""SELECT * FROM schedules s WHERE enabled=1 AND next_due<=?
                AND NOT EXISTS (SELECT 1 FROM runs r WHERE r.schedule_id=s.id
                    AND r.status IN ('running','retry')) ORDER BY next_due LIMIT 100""", (now,)).fetchall()
            for job in jobs:
                job = dict(job)
                due = job['next_due']
                next_due, count, capped = advance(job, now)
                skip = job['misfire'] == 'skip' and now-due > job['grace_seconds']
                db.execute("UPDATE schedules SET next_due=? WHERE id=?", (next_due, job['id']))
                if skip or count > 1 or now-due > job['grace_seconds']:
                    db.execute("INSERT INTO misfires VALUES (?,?,?,?,?,?,?)",
                        (uuid.uuid4().hex, job['id'], due, now, count if skip else count-1,
                         int(capped), 'skip' if skip else 'coalesce'))
                if skip:
                    continue
                row = dict(id=uuid.uuid4().hex, schedule_id=job['id'], scheduled_at=due,
                           snapshot=json.dumps(job), status='running', attempt=1, ready_at=now,
                           result=None, error=None, delivery_error=None)
                db.execute("INSERT INTO runs VALUES (:id,:schedule_id,:scheduled_at,:snapshot,:status,:attempt,:ready_at,:result,:error,:delivery_error)", row)
                return row
            return None

    def misfires(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM misfires ORDER BY rowid")]

    def finish(self, ident, *, result=None, error=None, enqueue_delivery=False):
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
            target = policy.get('delivery_target')
            if status in ('succeeded', 'failed') and (target or enqueue_delivery):
                db.execute("INSERT INTO deliveries (id,run_id,target,status,ready_at) VALUES (?,?,?,'pending',?)",
                           (uuid.uuid4().hex, ident, target or '{}', now))

    def interrupt(self, ident):
        # Operator must first establish the old worker has stopped.
        with self.connection() as db:
            if not db.execute("UPDATE runs SET status='interrupted' WHERE id=? AND status='running'", (ident,)).rowcount:
                raise ValueError("run is not running")

    def delivery_failed(self, ident, error):
        with self.connection() as db:
            db.execute("UPDATE runs SET delivery_error=? WHERE id=?", (error, ident))

    def deliveries(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM deliveries ORDER BY rowid")]

    def claim_delivery(self):
        now = timestamp(self.clock())
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM deliveries WHERE status='pending' AND ready_at<=? ORDER BY ready_at,rowid LIMIT 1", (now,)).fetchone()
            if row is None:
                return None
            token = uuid.uuid4().hex
            db.execute("UPDATE deliveries SET status='delivering',attempt=attempt+1,token=? WHERE id=?", (token, row['id']))
            item = dict(row)
            item.update(status='delivering', attempt=item['attempt']+1, token=token)
            item['target'] = json.loads(item['target'])
            item['run'] = dict(db.execute("SELECT * FROM runs WHERE id=?", (item['run_id'],)).fetchone())
            return item

    def finish_delivery(self, ident, token, *, status, error=None, retry_delay=60):
        if status not in ('delivered', 'failed', 'unknown', 'pending') or retry_delay < 1:
            raise ValueError("invalid delivery outcome")
        with self.connection() as db:
            row = db.execute("UPDATE deliveries SET status=?,error=?,ready_at=?,token=NULL WHERE id=? AND token=? AND status='delivering'",
                (status, error, timestamp(self.clock())+retry_delay, ident, token))
            if not row.rowcount:
                raise ValueError("delivery claim is no longer owned")
            db.execute("UPDATE runs SET delivery_error=? WHERE id=(SELECT run_id FROM deliveries WHERE id=?)", (error, ident))

    def abandon_delivery(self, ident):
        # Only after the operator establishes that the claiming sender has stopped.
        with self.connection() as db:
            if not db.execute("UPDATE deliveries SET status='unknown',token=NULL,error='sender stopped; outcome unknown' WHERE id=? AND status='delivering'", (ident,)).rowcount:
                raise ValueError("delivery is not in flight")
            db.execute("UPDATE runs SET delivery_error='sender stopped; outcome unknown' WHERE id=(SELECT run_id FROM deliveries WHERE id=?)", (ident,))
