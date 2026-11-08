import json
from concurrent.futures import ThreadPoolExecutor
import unittest
from tests.cron import test_store as fixtures
from senai.cron import Store, DeliveryWorker, RetryDelivery

class DeliveryTests(unittest.TestCase):
    setUp = fixtures.CronTests.setUp
    create = fixtures.CronTests.create
    def test_completion_survives_restart(self):
        self.create(delivery_target={'channel': 'fake', 'recipient': 'alice'})
        run = self.store.claim()
        self.store.finish(run['id'], result='hello')
        restarted = Store(self.path, clock=lambda: self.now)
        sent = []
        DeliveryWorker(restarted, lambda item: sent.append(item)).tick()
        self.assertEqual(sent[0]['target']['recipient'], 'alice')
        self.assertEqual(sent[0]['run']['result'], 'hello')
        self.assertEqual(restarted.deliveries()[0]['status'], 'delivered')
        self.assertIsNone(restarted.claim())

    def test_competing_delivery_claims(self):
        self.create(delivery_target={'channel': 'fake'})
        run = self.store.claim()
        self.store.finish(run['id'], result='ok')
        with ThreadPoolExecutor(max_workers=4) as pool:
            claimed = list(pool.map(lambda _: Store(self.path, clock=lambda: self.now).claim_delivery(), range(4)))
        self.assertEqual(sum(x is not None for x in claimed), 1)

    def test_uncertain_send_is_never_retried(self):
        self.create(delivery_target={'channel': 'fake'})
        run = self.store.claim()
        self.store.finish(run['id'], result='ok')
        def uncertain(item):
            raise RuntimeError('connection lost after send')
        DeliveryWorker(self.store, uncertain).tick()
        self.assertEqual(self.store.deliveries()[0]['status'], 'unknown')
        self.assertIsNone(self.store.claim_delivery())

    def test_abandoned_claim_requires_explicit_recovery(self):
        self.create(delivery_target={'channel': 'fake'})
        run = self.store.claim()
        self.store.finish(run['id'], result='ok')
        claim = self.store.claim_delivery()
        restarted = Store(self.path, clock=lambda: self.now)
        self.assertIsNone(restarted.claim_delivery())
        restarted.abandon_delivery(claim['id'])
        self.assertEqual(restarted.deliveries()[0]['status'], 'unknown')
        with self.assertRaises(ValueError):
            self.store.finish_delivery(claim['id'], claim['token'], status='delivered')

    def test_confirmed_transient_retry_is_bounded(self):
        from datetime import timedelta
        self.create(delivery_target={'channel': 'fake'})
        run = self.store.claim()
        self.store.finish(run['id'], result='ok')
        def unavailable(item):
            raise RetryDelivery('definitely not accepted')
        worker = DeliveryWorker(self.store, unavailable, max_attempts=2, retry_delay=5)
        worker.tick()
        self.assertIsNone(self.store.claim_delivery())
        self.now += timedelta(seconds=5)
        worker.tick()
        self.assertEqual(self.store.deliveries()[0]['status'], 'failed')
        self.assertIsNone(self.store.claim())

    def test_queue_insert_failure_rolls_back_result(self):
        self.create(delivery_target={'channel': 'fake'})
        run = self.store.claim()
        with self.store.connection() as db:
            db.execute("CREATE TRIGGER reject_delivery BEFORE INSERT ON deliveries BEGIN SELECT RAISE(ABORT, 'disk simulation'); END")
        with self.assertRaises(Exception):
            self.store.finish(run['id'], result='ok')
        self.assertEqual(self.store.runs()[0]['status'], 'running')

    def test_old_database_migration_preserves_jobs(self):
        import sqlite3
        old = self.path.parent / 'old.db'
        with sqlite3.connect(old) as db:
            db.execute("CREATE TABLE schedules (id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, prompt TEXT NOT NULL, project TEXT NOT NULL, scope TEXT NOT NULL, timezone TEXT NOT NULL, enabled INTEGER NOT NULL, next_due REAL, every REAL, retries INTEGER, retry_delay REAL)")
            db.execute("INSERT INTO schedules VALUES ('old','old','prompt',?,'qa','Asia/Dhaka',1,0,NULL,0,60)", (self.tmp.name,))
        migrated = Store(old, clock=lambda: self.now)
        self.assertEqual(migrated.list()[0]['name'], 'old')
        run = migrated.claim()
        migrated.finish(run['id'], result='ok')
        self.assertEqual(migrated.deliveries(), [])

    def test_legacy_callback_recovers_on_idle_tick(self):
        from senai.cron import Worker
        self.create()
        run = self.store.claim()
        self.store.finish(run['id'], result='done', enqueue_delivery=True)
        sent = []
        def forbidden(run):
            self.fail('execution must not repeat')
        Worker(Store(self.path, clock=lambda: self.now), forbidden, sent.append).tick()
        self.assertEqual(sent[0]['result'], 'done')

    def test_retry_does_not_enqueue_until_terminal(self):
        self.create(retries=1, delivery_target={'channel': 'fake'})
        run = self.store.claim()
        self.store.finish(run['id'], error='temporary')
        self.assertEqual(self.store.deliveries(), [])
