import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import senai


class InputTests(unittest.TestCase):
    def test_prompt_separates_instructions_and_request(self):
        prompt = senai.build_prompt('Create add.py')
        self.assertIn('write and edit code', prompt)
        self.assertIn('All generated files must stay inside this workspace', prompt)
        self.assertIn('<user_request>\nCreate add.py\n</user_request>', prompt)

    def test_reject_empty_request(self):
        with self.assertRaises(ValueError):
            senai.build_prompt('  ')

    def test_cli_passes_request_and_resolved_project(self):
        with tempfile.TemporaryDirectory() as project:
            with patch('senai.run_codex', return_value='Created add.py') as run:
                out, err = io.StringIO(), io.StringIO()
                result = senai.main(['--project', project, 'Create add.py'], out, err)
                self.assertEqual(result, 0)
                self.assertEqual(out.getvalue(), 'Created add.py\n')
                self.assertEqual(run.call_args.args[1], Path(project).resolve() / 'outputs')
                self.assertIn('Create add.py', run.call_args.args[0])
                self.assertTrue((Path(project) / 'outputs').is_dir())

    def test_output_symlink_outside_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as outside:
            (Path(project) / 'outputs').symlink_to(outside, target_is_directory=True)
            with patch('senai.run_codex') as run:
                out, err = io.StringIO(), io.StringIO()
                self.assertEqual(senai.main(['--project', project, 'Create app.py'], out, err), 2)
                run.assert_not_called()

    def test_blank_request_does_not_create_outputs(self):
        with tempfile.TemporaryDirectory() as project:
            self.assertEqual(senai.main(['--project', project, ' '], io.StringIO(), io.StringIO()), 2)
            self.assertFalse((Path(project) / 'outputs').exists())

    def test_missing_project_returns_error(self):
        with tempfile.TemporaryDirectory() as root:
            out, err = io.StringIO(), io.StringIO()
            result = senai.main(['--project', str(Path(root) / 'missing'), 'Edit app.py'], out, err)
            self.assertEqual(result, 2)
            self.assertIn('directory', err.getvalue())


class ExecutionTests(unittest.TestCase):
    def test_exec_uses_stdin_and_returns_final_message(self):
        def execute(command, **kwargs):
            self.assertEqual(command[:2], ['codex', 'exec'])
            self.assertIn('workspace-write', command)
            self.assertEqual(command[-1], '-')
            self.assertEqual(kwargs['input'], 'a request with "quotes"; $stuff')
            self.assertNotIn('shell', kwargs)
            Path(command[command.index('--output-last-message') + 1]).write_text('Done', encoding='utf-8')
            return subprocess.CompletedProcess(command, 0, 'progress', '')

        with patch('senai.subprocess.run', side_effect=execute):
            self.assertEqual(senai.run_codex('a request with "quotes"; $stuff', Path.cwd()), 'Done')

    def test_codex_failure_reports_diagnostics(self):
        with patch('senai.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'Login required')):
            with self.assertRaisesRegex(RuntimeError, 'Login required'):
                senai.run_codex('Edit app.py', Path.cwd())

    def test_empty_response_is_error(self):
        with patch('senai.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            with self.assertRaisesRegex(RuntimeError, 'final response'):
                senai.run_codex('Edit app.py', Path.cwd())

    def test_missing_codex_has_actionable_error(self):
        with patch('senai.subprocess.run', side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(RuntimeError, 'Install Codex CLI'):
                senai.run_codex('Edit app.py', Path.cwd())

    def test_execution_error_reaches_cli(self):
        with patch('senai.run_codex', side_effect=RuntimeError('Login required')):
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(senai.main(['Edit app.py'], out, err), 2)
            self.assertEqual(out.getvalue(), '')
            self.assertIn('Login required', err.getvalue())


if __name__ == '__main__':
    unittest.main()
