import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from senai.cron.__main__ import main

class CLITests(unittest.TestCase):
    def test_dry_run_preserves_due_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = ['--project', tmp]
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(args + ['create', '--name', 'qa', '--prompt', 'test',
                    '--scope', 'qa', '--at', '2020-01-01T00:00:00+06:00']), 0)
                self.assertEqual(main(args + ['dry-run']), 0)
            from senai.cron import Store
            store = Store(Path(tmp)/'outputs/.senai-cron/cron.db')
            self.assertEqual(store.runs(), [])
            self.assertIsNotNone(store.claim())
            self.assertIn('qa', output.getvalue())

    def test_calendar_and_skip_preview_are_non_mutating(self):
        import json
        from senai.cron import Store
        with tempfile.TemporaryDirectory() as tmp:
            args = ['--project', tmp]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args+['create', '--name','calendar','--prompt','test',
                    '--scope','qa','--at','2020-01-01T00:00:00+06:00',
                    '--cron','0 9 * * *','--misfire','skip','--grace-seconds','0']),0)
            store = Store(Path(tmp)/'outputs/.senai-cron/cron.db')
            before = store.list()
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(args+['dry-run']),0)
            preview = json.loads(output.getvalue())
            self.assertEqual(len(preview['would_skip']),1)
            self.assertEqual(preview['due'],[])
            self.assertEqual(store.list(),before)
            self.assertEqual(store.misfires(),[])

    def test_show_edit_and_stale_revision(self):
        import json
        from senai.cron import Store
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'outputs/.senai-cron/cron.db')
            ident=store.create(name='edit-demo',prompt='old',project=tmp,scope='qa',
                at=datetime(2030,1,1,tzinfo=timezone.utc))
            args=['--project',tmp]
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(args+['show',ident]),0)
            shown=json.loads(output.getvalue())
            self.assertEqual(shown['next_due_local'],'2030-01-01T06:00:00+06:00')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args+['edit',ident,'--expected-revision',str(shown['revision']),
                    '--prompt','new','--at','2030-01-02T00:00:00+06:00','--cron','0 9 * * *']),0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args+['edit',ident,'--expected-revision',str(shown['revision']),
                    '--prompt','stale']),2)
            self.assertEqual(store.get(ident)['prompt'],'new')
            self.assertEqual(store.get(ident)['next_due_local'],'2030-01-02T09:00:00+06:00')
