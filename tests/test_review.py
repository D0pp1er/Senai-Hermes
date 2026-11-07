import io
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from senai import cli


class ReviewTests(unittest.TestCase):
    def test_defaults_to_read_only_uncommitted_review(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(cli.main(['review', '--project', project], io.StringIO(), io.StringIO()), 0)
            command = run.call_args.args[0]
            self.assertEqual(command[-2:], ['review', '--uncommitted'])
            self.assertEqual(command[command.index('--sandbox') + 1], 'read-only')

    def test_base_and_commit_are_forwarded_separately(self):
        for selector, value in [('--base', 'main'), ('--commit', 'abc123')]:
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
                self.assertEqual(cli.main(['review', '--project', project, selector, value], io.StringIO(), io.StringIO()), 0)
                self.assertEqual(run.call_args.args[0][-3:], ['review', selector, value])

    def test_conflicting_review_targets_fail_before_execution(self):
        with patch('senai.native.subprocess.run') as run:
            with self.assertRaises(SystemExit) as result:
                cli.main(['review', '--base', 'main', '--commit', 'abc123'], io.StringIO(), io.StringIO())
            self.assertEqual(result.exception.code, 2)
            run.assert_not_called()
