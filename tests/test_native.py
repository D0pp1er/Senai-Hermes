import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli


class NativeTests(unittest.TestCase):
    def test_native_preserves_arguments_and_process_status(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', return_value=subprocess.CompletedProcess([], 9)) as run:
            arguments = ['exec', '--json', '--future-flag', 'a value with spaces; $literal']
            self.assertEqual(cli.main(['codex', '--project', project, '--', *arguments], io.StringIO(), io.StringIO()), 9)
            self.assertEqual(run.call_args.args[0][-len(arguments):], arguments)
            self.assertEqual(run.call_args.kwargs['cwd'], Path(project) / 'outputs')

    def test_native_blocks_workspace_relocation(self):
        for flag in ['--cd=/tmp', '-C/tmp', '--add-dir', '--worktree']:
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run') as run:
                err = io.StringIO()
                self.assertEqual(cli.main(['codex', '--project', project, '--', flag], io.StringIO(), err), 2)
                run.assert_not_called()
                self.assertIn('outputs', err.getvalue())

    def test_native_blocks_external_response_file(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run') as run:
            err = io.StringIO()
            self.assertEqual(cli.main(['codex', '--project', project, '--', 'exec', '-o', '/tmp/external.txt', 'Write code'], io.StringIO(), err), 2)
            run.assert_not_called()

    def test_native_accepts_response_inside_outputs(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(cli.main(['codex', '--project', project, '--', 'exec', '-o', 'response.txt', 'Write code'], io.StringIO(), io.StringIO()), 0)
            self.assertIn('response.txt', run.call_args.args[0])

    def test_literal_prompt_after_separator_is_not_reparsed(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(cli.main(['codex', '--project', project, '--', 'exec', '--', '--worktree'], io.StringIO(), io.StringIO()), 0)
            self.assertEqual(run.call_args.args[0][-2:], ['--', '--worktree'])
