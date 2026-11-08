import json
import unittest
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from tests.cron import test_store as fixtures
from senai.cron import Store

class ManagementTests(unittest.TestCase):
    setUp = fixtures.CronTests.setUp
    create = fixtures.CronTests.create

    def test_edit_and_restart_preserve_identity_and_new_time(self):
        ident = self.create()
        before = self.store.get(ident)
        later = self.now+timedelta(hours=2)
        changed = self.store.update(ident, expected_revision=before['revision'], prompt='new task', at=later)
        self.assertEqual(changed['id'],ident)
        self.assertEqual(changed['revision'],before['revision']+1)
        restarted=Store(self.path,clock=lambda:self.now)
        self.assertIsNone(restarted.claim())
        self.now=later
        run=restarted.claim()
        self.assertEqual(json.loads(run['snapshot'])['prompt'],'new task')

    def test_active_run_and_waiting_retry_refuse_edit(self):
        ident=self.create(retries=1)
        before=self.store.get(ident)
        run=self.store.claim()
        with self.assertRaises(ValueError):
            self.store.update(ident,expected_revision=before['revision'],prompt='changed')
        self.store.finish(run['id'],error='transient')
        current=self.store.get(ident)
        with self.assertRaises(ValueError):
            self.store.update(ident,expected_revision=current['revision'],prompt='changed')

    def test_two_stale_editors_cannot_overwrite_each_other(self):
        ident=self.create()
        revision=self.store.get(ident)['revision']
        def edit(prompt):
            try:
                return Store(self.path).update(ident,expected_revision=revision,prompt=prompt)
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            changed=list(pool.map(edit,['first','second']))
        self.assertEqual(sum(x is not None for x in changed),1)

    def test_invalid_edit_rolls_back_all_fields(self):
        ident=self.create()
        before=self.store.get(ident)
        with self.assertRaises(ValueError):
            self.store.update(ident,expected_revision=before['revision'],prompt='new',cron='bad',at=self.now)
        self.assertEqual(self.store.get(ident),before)

    def test_completed_oneshot_is_not_rearmed_by_text_edit(self):
        ident=self.create()
        run=self.store.claim()
        self.store.finish(run['id'],result='done')
        old=self.store.get(ident)
        self.store.update(ident,expected_revision=old['revision'],prompt='new text')
        self.assertIsNone(self.store.claim())
        self.assertEqual(json.loads(self.store.runs()[0]['snapshot'])['prompt'],'report')

    def test_recurrence_change_requires_explicit_start(self):
        ident=self.create()
        before=self.store.get(ident)
        with self.assertRaises(ValueError):
            self.store.update(ident,expected_revision=before['revision'],cron='0 9 * * *')
        self.store.update(ident,expected_revision=before['revision'],cron='0 9 * * *',at=self.now)
        self.assertEqual(self.store.get(ident)['next_due_local'],'2026-11-09T09:00:00+06:00')

    def test_pause_invalidates_old_revision_and_edit_preserves_pause(self):
        ident=self.create()
        before=self.store.get(ident)
        self.store.pause(ident)
        with self.assertRaises(ValueError):
            self.store.update(ident,expected_revision=before['revision'],prompt='stale')
        current=self.store.get(ident)
        self.store.update(ident,expected_revision=current['revision'],prompt='new')
        self.assertFalse(self.store.get(ident)['enabled'])

    def test_completed_result_keeps_original_delivery_destination(self):
        ident=self.create(delivery_target={'recipient':'alice'})
        run=self.store.claim()
        self.store.finish(run['id'],result='done')
        current=self.store.get(ident)
        self.store.update(ident,expected_revision=current['revision'],delivery_target={'recipient':'bob'})
        self.assertEqual(self.store.claim_delivery()['target'],{'recipient':'alice'})

    def test_project_scope_and_unknown_fields_are_not_editable(self):
        ident=self.create()
        for changes in ({'project':'/tmp'},{'scope':'someone-else'},{'enabled':True},{'next_due':0}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.store.update(ident,expected_revision=1,**changes)

    def test_run_claim_invalidates_previously_read_revision(self):
        ident=self.create()
        before=self.store.get(ident)
        run=self.store.claim()
        self.store.finish(run['id'],result='done')
        with self.assertRaises(ValueError):
            self.store.update(ident,expected_revision=before['revision'],prompt='stale')

    def test_edit_and_execution_claim_are_serialized(self):
        import threading
        ident=self.create()
        revision=self.store.get(ident)['revision']
        barrier=threading.Barrier(2)
        def edit():
            barrier.wait()
            try:
                Store(self.path,clock=lambda:self.now).update(ident,expected_revision=revision,prompt='edited')
                return True
            except ValueError:
                return False
        def claim():
            barrier.wait()
            return Store(self.path,clock=lambda:self.now).claim()
        with ThreadPoolExecutor(max_workers=2) as pool:
            edit_future=pool.submit(edit)
            claim_future=pool.submit(claim)
            edited,run=edit_future.result(),claim_future.result()
        self.assertEqual(json.loads(run['snapshot'])['prompt'],'edited' if edited else 'report')
        self.assertEqual(len(self.store.runs()),1)

    def test_empty_and_invalid_revision_edits_do_not_mutate(self):
        ident=self.create()
        before=self.store.get(ident)
        for revision,changes in ((1,{}),(True,{'prompt':'x'}),(0,{'prompt':'x'})):
            with self.assertRaises(ValueError):
                self.store.update(ident,expected_revision=revision,**changes)
        self.assertEqual(self.store.get(ident),before)
