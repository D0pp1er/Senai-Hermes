import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from tests.cron import test_store as fixtures
from senai.cron import Store

class CalendarTests(unittest.TestCase):
    setUp = fixtures.CronTests.setUp
    create = fixtures.CronTests.create

    def calendar(self, at, expr='0 9 * * *', zone='Asia/Dhaka', **kwargs):
        return self.store.create(name='calendar', prompt='remind', project=self.tmp.name,
            scope='qa', at=at, cron=expr, timezone=zone, **kwargs)

    def test_dhaka_wall_clock_after_restart(self):
        start = datetime(2026, 11, 9, 0, tzinfo=timezone.utc)
        self.calendar(start)
        self.assertEqual(self.store.list()[0]['next_due'], start.timestamp()+3*3600)
        self.now = start + timedelta(hours=3)
        restarted = Store(self.path, clock=lambda: self.now)
        self.assertIsNotNone(restarted.claim())
        self.assertIsNone(restarted.claim())

    def test_daily_keeps_hour_across_spring_dst(self):
        zone = ZoneInfo('America/New_York')
        self.now = datetime(2026, 3, 7, 9, tzinfo=zone)
        self.calendar(self.now, zone=zone.key)
        run = self.store.claim()
        self.store.finish(run['id'], result='ok')
        due = self.store.list()[0]['next_due']
        self.assertEqual(datetime.fromtimestamp(due, zone).hour, 9)
        self.assertEqual(due-self.now.timestamp(), 23*3600)

    def test_nonexistent_wall_time_is_skipped(self):
        zone = ZoneInfo('America/New_York')
        self.calendar(datetime(2026, 3, 8, 0, tzinfo=zone), expr='30 2 * * *', zone=zone.key)
        due = datetime.fromtimestamp(self.store.list()[0]['next_due'], zone)
        self.assertEqual((due.day, due.hour, due.minute), (9, 2, 30))

    def test_repeated_hour_runs_once_at_earlier_fold(self):
        zone = ZoneInfo('America/New_York')
        self.now = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
        self.calendar(self.now, expr='30 1 * * *', zone=zone.key)
        run = self.store.claim()
        self.store.finish(run['id'], result='ok')
        self.now = self.now.replace(fold=1)
        self.assertIsNone(self.store.claim())
        due = datetime.fromtimestamp(self.store.list()[0]['next_due'], zone)
        self.assertEqual((due.day, due.hour), (2, 1))

    def test_skip_stale_oneshot_records_reason_without_delivery(self):
        self.create(misfire='skip', grace_seconds=30, delivery_target={'channel':'fake'})
        self.now += timedelta(seconds=31)
        self.assertIsNone(self.store.claim())
        self.assertEqual(self.store.runs(), [])
        self.assertEqual(self.store.deliveries(), [])
        self.assertIsNone(self.store.list()[0]['next_due'])
        self.assertEqual(self.store.misfires()[0]['reason'], 'skip')
        self.assertEqual(self.store.misfires()[0]['missed_count'], 1)
        self.assertIsNone(self.store.claim())
        self.assertEqual(len(self.store.misfires()), 1)

    def test_grace_boundary_runs_at_limit(self):
        self.create(misfire='skip', grace_seconds=30)
        self.now += timedelta(seconds=30)
        self.assertIsNotNone(self.store.claim())

    def test_skip_interval_preserves_grid(self):
        self.create(every=60, misfire='skip', grace_seconds=10)
        self.now += timedelta(seconds=181)
        self.assertIsNone(self.store.claim())
        self.assertEqual(self.store.list()[0]['next_due'], self.now.timestamp()+59)
        self.assertEqual(self.store.misfires()[0]['missed_count'], 4)

    def test_coalescing_accounts_for_collapsed_occurrences(self):
        self.create(every=60)
        self.now += timedelta(seconds=180)
        run = self.store.claim()
        self.assertIsNotNone(run)
        event = self.store.misfires()[0]
        self.assertEqual((event['missed_count'],event['reason']), (3,'coalesce'))

    def test_calendar_skip_moves_after_now(self):
        self.calendar(self.now, expr='0 6 * * *', misfire='skip', grace_seconds=0)
        self.now += timedelta(days=3, seconds=1)
        self.assertIsNone(self.store.claim())
        self.assertGreater(self.store.list()[0]['next_due'], self.now.timestamp())
        self.assertEqual(self.store.misfires()[0]['missed_count'],4)

    def test_invalid_cron_policy_and_conflicting_recurrence(self):
        for kwargs in ({'cron':'bad'}, {'cron':'0 0 31 2 *'}, {'cron':'* * * * * *'}, {'cron':'R * * * *'},
                       {'cron':'0 9 * * *','every':60}, {'misfire':'replay'},
                       {'grace_seconds':-1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.create(**kwargs)
        self.assertEqual(self.store.list(), [])

    def test_skip_does_not_starve_other_due_job(self):
        self.create(misfire='skip', grace_seconds=0)
        self.now += timedelta(seconds=1)
        self.store.create(name='other', prompt='x', project=self.tmp.name, scope='qa', at=self.now)
        run = self.store.claim()
        self.assertEqual(__import__('json').loads(run['snapshot'])['name'], 'other')

    def test_calendar_large_backlog_count_is_explicitly_bounded(self):
        self.calendar(self.now, expr='* * * * *')
        self.now += timedelta(days=2)
        run = self.store.claim()
        self.assertIsNotNone(run)
        event = self.store.misfires()[0]
        self.assertEqual(event['count_capped'], 1)
        self.assertEqual(event['missed_count'], 999)
        self.assertGreater(self.store.list()[0]['next_due'], self.now.timestamp())

    def test_misfire_rollback_preserves_due_instant(self):
        self.create(misfire='skip', grace_seconds=0)
        due = self.store.list()[0]['next_due']
        self.now += timedelta(seconds=1)
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER reject_misfire BEFORE INSERT ON misfires BEGIN SELECT RAISE(ABORT, 'failure'); END")
        with self.assertRaises(__import__('sqlite3').IntegrityError):
            self.store.claim()
        self.assertEqual(self.store.list()[0]['next_due'], due)
        self.assertEqual(self.store.misfires(), [])

    def test_skip_accounting_is_once_under_competing_workers(self):
        from concurrent.futures import ThreadPoolExecutor
        self.create(misfire='skip', grace_seconds=0)
        self.now += timedelta(seconds=1)
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(lambda _: Store(self.path, clock=lambda: self.now).claim(), range(4)))
        self.assertEqual(claims, [None]*4)
        self.assertEqual(len(self.store.misfires()),1)

    def test_weekday_expression_uses_pinned_zone(self):
        self.calendar(datetime(2026,11,9,4,tzinfo=timezone.utc), expr='0 9 * * mon-fri')
        due = datetime.fromtimestamp(self.store.list()[0]['next_due'],ZoneInfo('Asia/Dhaka'))
        self.assertEqual((due.day,due.hour), (10,9))

    def test_legacy_rows_keep_default_catchup(self):
        import sqlite3
        path = self.path.parent/'legacy.db'
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE schedules (id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, prompt TEXT NOT NULL, project TEXT NOT NULL, scope TEXT NOT NULL, timezone TEXT NOT NULL, enabled INTEGER NOT NULL, next_due REAL, every REAL, retries INTEGER, retry_delay REAL)")
            db.execute("INSERT INTO schedules VALUES ('old','old','x',?,'qa','Asia/Dhaka',1,0,NULL,0,60)",(self.tmp.name,))
        migrated = Store(path,clock=lambda: self.now)
        self.assertEqual(migrated.list()[0]['misfire'],'coalesce')
        self.assertIsNotNone(migrated.claim())
