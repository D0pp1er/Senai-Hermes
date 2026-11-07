import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli


class ChatTests(unittest.TestCase):
    def test_chat_inherits_terminal_and_uses_output_workspace(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', return_value=subprocess.CompletedProcess([], 0)) as run:
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(cli.main(['chat', '--project', project], out, err), 0)
            command = run.call_args.args[0]
            self.assertEqual(command[0], 'codex')
            self.assertIn('--no-alt-screen', command)
            self.assertEqual(command[command.index('--cd') + 1], str(Path(project) / 'outputs'))
            self.assertNotIn('input', run.call_args.kwargs)
            self.assertNotIn('capture_output', run.call_args.kwargs)
            self.assertIs(run.call_args.kwargs['stdout'], out)
            self.assertIs(run.call_args.kwargs['stderr'], err)

    def test_chat_preserves_native_exit_code(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', return_value=subprocess.CompletedProcess([], 7)):
            self.assertEqual(cli.main(['chat', '--project', project], io.StringIO(), io.StringIO()), 7)

    def test_chat_missing_codex_reports_install_hint(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.native.subprocess.run', side_effect=FileNotFoundError()):
            err = io.StringIO()
            self.assertEqual(cli.main(['chat', '--project', project], io.StringIO(), err), 2)
            self.assertIn('Install Codex CLI', err.getvalue())
