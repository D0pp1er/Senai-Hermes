import io
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from senai import cli, codex
from senai.options import CodexOptions


class GitOptionTests(unittest.TestCase):
    def test_git_check_bypass_is_explicit_and_forwarded(self):
        self.assertNotIn('--skip-git-repo-check', CodexOptions().to_args())
        self.assertIn('--skip-git-repo-check', CodexOptions(skip_git_repo_check=True).to_args())

    def test_flag_is_accepted_before_or_after_request(self):
        request = 'make a directory named Testbench and create a helloworldcpp to print tumi kemon acho'
        for arguments in [['--skip-git-repo-check', request], [request, '--skip-git-repo-check']]:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
                self.assertEqual(cli.main(['--project', project, *arguments], io.StringIO(), io.StringIO()), 0)
                self.assertTrue(run.call_args.kwargs['options'].skip_git_repo_check)
                self.assertIn(request, run.call_args.args[0])

    def test_trusted_directory_error_explains_supported_fix(self):
        result = subprocess.CompletedProcess([], 1, '', 'Not inside a trusted directory and --skip-git-repo-check was not specified.')
        with tempfile.TemporaryDirectory() as workspace, patch('senai.codex.subprocess.run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'Use --skip-git-repo-check'):
                codex.run_codex('Write code', Path(workspace))
