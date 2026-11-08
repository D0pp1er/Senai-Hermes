import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from senai.cron import Store, Worker

class CronTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'cron.db'
        self.now = datetime(2026, 11, 9, tzinfo=timezone.utc)
        self.store = Store(self.path, clock=lambda: self.now)

    def create(self, **kwargs):
        return self.store.create(name='daily', prompt='report', project=self.tmp.name,
                                 scope='private', at=self.now, **kwargs)

    def test_restart_competing_claims(self):
        self.create()
        def claim(_):
            return Store(self.path, clock=lambda: self.now).claim()
        with ThreadPoolExecutor(max_workers=4) as pool:
            claims = list(pool.map(claim, range(4)))
        self.assertEqual(sum(x is not None for x in claims), 1)

    def test_pause_resume_delete(self):
        job = self.create()
        self.store.pause(job)
        self.assertIsNone(self.store.claim())
        self.store.resume(job)
        self.assertIsNotNone(self.store.claim())
        self.store.delete(job)
        self.assertEqual(self.store.list(), [])
        self.assertEqual(len(self.store.runs()), 1)

    def test_coalescing_overlap(self):
        self.create(every=60)
        self.now += timedelta(hours=1)
        run = self.store.claim()
        self.assertIsNone(self.store.claim())
        self.store.finish(run['id'], result='done')
        self.assertIsNone(self.store.claim())
        self.now += timedelta(seconds=60)
        self.assertIsNotNone(self.store.claim())

    def test_bounded_retry(self):
        self.create(retries=1, retry_delay=10)
        calls = []
        def fail(run):
            calls.append(run['id'])
            raise RuntimeError('failed')
        worker = Worker(self.store, fail)
        worker.tick()
        self.assertIsNone(self.store.claim())
        self.now += timedelta(seconds=10)
        worker.tick()
        self.now += timedelta(seconds=10)
        self.assertIsNone(self.store.claim())
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.store.runs()[0]['status'], 'failed')

    def test_explicit_recovery(self):
        self.create()
        run = self.store.claim()
        restarted = Store(self.path, clock=lambda: self.now)
        self.assertIsNone(restarted.claim())
        restarted.interrupt(run['id'])
        self.assertEqual(restarted.runs()[0]['status'], 'interrupted')
        self.assertIsNone(restarted.claim())

    def test_delivery_failure(self):
        self.create()
        def delivery(run):
            raise RuntimeError('offline')
        Worker(self.store, lambda run: 'ok', delivery).tick()
        self.assertEqual(self.store.runs()[0]['status'], 'succeeded')
        self.assertEqual(self.store.runs()[0]['delivery_error'], 'offline')
        self.assertIsNone(self.store.claim())

    def test_validation(self):
        self.create()
        self.assertEqual(self.store.list()[0]['timezone'], 'Asia/Dhaka')
        for kwargs in ({'every': 0}, {'timezone': 'Invalid/Zone'}, {'retries': -1}):
            with self.assertRaises(ValueError):
                self.create(**kwargs)
        with self.assertRaises(ValueError):
            self.store.create(name='bad', prompt='x', project=self.tmp.name,
                              scope='x', at=datetime(2026, 1, 1))

    def test_dst_fold(self):
        from zoneinfo import ZoneInfo
        zone = ZoneInfo('America/New_York')
        for fold in (0, 1):
            self.store.create(name=str(fold), prompt='x', project=self.tmp.name,
                scope='x', at=datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=fold),
                timezone='America/New_York')
        rows = self.store.list()
        self.assertEqual(rows[1]['next_due'] - rows[0]['next_due'], 3600)
