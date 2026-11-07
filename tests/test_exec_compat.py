import io
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli, codex
from senai.options import CodexOptions


class ExecCompatibilityTests(unittest.TestCase):
    def invoke(self, flags):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
            status = cli.main(['--project', project, 'Write code', *flags], io.StringIO(), io.StringIO())
            self.assertEqual(status, 0)
            return run.call_args.kwargs['options']

    def test_native_boolean_and_value_flags_are_forwarded(self):
        flags = ['--strict-config', '--ephemeral', '--ignore-user-config', '--ignore-rules', '--oss', '--local-provider', 'ollama', '--enable', 'fixture_feature', '--disable', 'other_feature', '--thread-source', 'fixture', '--cyber-access-program', 'standard']
        options = self.invoke(flags)
        for flag in flags:
            self.assertIn(flag, options.to_args())

    def test_sandbox_and_color_are_explicit_options(self):
        options = self.invoke(['-s', 'read-only', '--color', 'always'])
        self.assertEqual(options.sandbox, 'read-only')
        self.assertEqual(options.color, 'always')

    def test_approval_policies_do_not_add_conflicting_default_sandbox(self):
        for flag in ['--approve-for-me', '--dangerously-bypass-approvals-and-sandbox']:
            with self.subTest(flag=flag):
                options = self.invoke([flag])
                self.assertIsNone(options.sandbox)
                self.assertIn(flag, options.to_args())

    def test_global_approval_option_goes_before_exec(self):
        def execute(command, **kwargs):
            self.assertEqual(command[:4], ['codex', '--ask-for-approval', 'never', 'exec'])
            Path(command[command.index('--output-last-message') + 1]).write_text('Done')
            return subprocess.CompletedProcess(command, 0, '', '')
        with tempfile.TemporaryDirectory() as workspace, patch('senai.codex.subprocess.run', side_effect=execute):
            self.assertEqual(codex.run_codex('Write code', Path(workspace), options=CodexOptions(approval='never')), 'Done')

    def test_cd_is_an_alias_for_parent_project(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
            self.assertEqual(cli.main(['-C', project, 'Write code'], io.StringIO(), io.StringIO()), 0)
            self.assertEqual(run.call_args.args[1], Path(project) / 'outputs')

    def test_schema_paths_are_resolved_from_caller(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
            schema = Path(project) / 'schema.json'
            schema.write_text('{"type":"object"}')
            self.assertEqual(cli.main(['--project', project, 'Write code', '--output-schema', str(schema)], io.StringIO(), io.StringIO()), 0)
            args = run.call_args.kwargs['options'].to_args()
            self.assertEqual(args[args.index('--output-schema') + 1], str(schema.resolve()))

    def test_conflicting_workspace_flags_have_targeted_error(self):
        for flags in [['--worktree'], ['--add-dir', '/tmp']]:
            with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex') as run:
                err = io.StringIO()
                self.assertEqual(cli.main(['--project', project, 'Write code', *flags], io.StringIO(), err), 2)
                self.assertIn('outputs/', err.getvalue())
                run.assert_not_called()

    def test_installed_exec_option_names_are_all_recognized(self):
        executable = Path.home() / '.local/bin/codex'
        if not executable.is_file():
            self.skipTest('Installed Codex is unavailable for help compatibility check')
        result = subprocess.run([str(executable), 'exec', '--help'], capture_output=True, text=True, check=True)
        expected = set(re.findall(r'(?<!\S)--[a-z][a-z0-9-]*', result.stdout))
        supported = set(cli.build_parser()._option_string_actions)
        self.assertFalse(expected - supported, f'Unrecognized installed Codex flags: {sorted(expected - supported)}')
