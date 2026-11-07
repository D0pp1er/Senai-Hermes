import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli, codex
from senai.options import CodexOptions


class ResumeTests(unittest.TestCase):
    def test_resume_by_id_preserves_prompt_stdin(self):
        def execute(command, **kwargs):
            self.assertEqual(command[-3:], ['resume', 'saved-session', '-'])
            self.assertEqual(kwargs['input'], 'Continue code')
            Path(command[command.index('--output-last-message') + 1]).write_text('Continued')
            return subprocess.CompletedProcess(command, 0, '', '')
        with tempfile.TemporaryDirectory() as workspace, patch('senai.codex.subprocess.run', side_effect=execute):
            self.assertEqual(codex.run_codex('Continue code', Path(workspace), options=CodexOptions(resume='saved-session')), 'Continued')

    def test_last_uses_native_session_selection(self):
        self.assertEqual(CodexOptions(last=True).session_args(), ['resume', '--last'])

    def test_cli_passes_resume_selector(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
            self.assertEqual(cli.main(['--project', project, '--resume', 'saved-session', 'Continue'], io.StringIO(), io.StringIO()), 0)
            self.assertEqual(run.call_args.kwargs['options'].resume, 'saved-session')

    def test_rejects_session_option_injection(self):
        with self.assertRaises(ValueError):
            CodexOptions(resume='--all').session_args()

    def test_rejects_conflicting_selectors(self):
        with self.assertRaises(ValueError):
            CodexOptions(resume='session', last=True).session_args()
