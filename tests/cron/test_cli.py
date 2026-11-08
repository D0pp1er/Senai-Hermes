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
