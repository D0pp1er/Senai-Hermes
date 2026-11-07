import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli, codex, prompts


class ExecutionTests(unittest.TestCase):
    def test_exec_uses_stdin_and_returns_final_message(self):
        def execute(command, **kwargs):
            self.assertEqual(command[:2], ['codex', 'exec'])
            self.assertIn('workspace-write', command)
            self.assertEqual(command[-1], '-')
            self.assertEqual(command[command.index('--cd') + 1], str(Path.cwd()))
            response_path = Path(command[command.index('--output-last-message') + 1])
            self.assertTrue(response_path.is_relative_to(Path.cwd()))
            self.assertEqual(kwargs['input'], 'a request with "quotes"; $stuff')
            self.assertNotIn('shell', kwargs)
            Path(command[command.index('--output-last-message') + 1]).write_text('Done', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0, 'progress', '')

        with patch('senai.codex.subprocess.run', side_effect=execute):
            self.assertEqual(codex.run_codex('a request with "quotes"; $stuff', Path.cwd()), 'Done')

    def test_codex_failure_reports_diagnostics(self):
        with patch('senai.codex.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'Login required')):
            with self.assertRaisesRegex(RuntimeError, 'Login required'):
                codex.run_codex('Edit app.py', Path.cwd())

    def test_empty_response_is_error(self):
        with patch('senai.codex.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            with self.assertRaisesRegex(RuntimeError, 'final response'):
                codex.run_codex('Edit app.py', Path.cwd())

    def test_missing_codex_has_actionable_error(self):
        with patch('senai.codex.subprocess.run', side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(RuntimeError, 'Install Codex CLI'):
                codex.run_codex('Edit app.py', Path.cwd())

    def test_execution_error_reaches_cli(self):
        with patch('senai.cli.run_codex', side_effect=RuntimeError('Login required')):
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(cli.main(['Edit app.py'], out, err), 2)
            self.assertEqual(out.getvalue(), '')
            self.assertIn('Login required', err.getvalue())
