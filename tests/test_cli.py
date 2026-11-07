import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli, codex, prompts


class InputTests(unittest.TestCase):
    def test_prompt_separates_instructions_and_request(self):
        prompt = prompts.build_prompt('Create add.py')
        self.assertIn('write and edit code', prompt)
        self.assertIn('All generated files must stay inside this workspace', prompt)
        self.assertIn('<user_request>\nCreate add.py\n</user_request>', prompt)

    def test_reject_empty_request(self):
        with self.assertRaises(ValueError):
            prompts.build_prompt('  ')

    def test_cli_passes_request_and_resolved_project(self):
        with tempfile.TemporaryDirectory() as project:
            with patch('senai.cli.run_codex', return_value='Created add.py') as run:
                out, err = io.StringIO(), io.StringIO()
                result = cli.main(['--project', project, 'Create add.py'], out, err)
                self.assertEqual(result, 0)
                self.assertEqual(out.getvalue(), 'Created add.py\n')
                self.assertEqual(run.call_args.args[1], Path(project).resolve() / 'outputs')
                self.assertIn('Create add.py', run.call_args.args[0])
                self.assertTrue((Path(project) / 'outputs').is_dir())

    def test_output_symlink_outside_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as project, tempfile.TemporaryDirectory() as outside:
            (Path(project) / 'outputs').symlink_to(outside, target_is_directory=True)
            with patch('senai.cli.run_codex') as run:
                out, err = io.StringIO(), io.StringIO()
                self.assertEqual(cli.main(['--project', project, 'Create app.py'], out, err), 2)
                run.assert_not_called()

    def test_blank_request_does_not_create_outputs(self):
        with tempfile.TemporaryDirectory() as project:
            self.assertEqual(cli.main(['--project', project, ' '], io.StringIO(), io.StringIO()), 2)
            self.assertFalse((Path(project) / 'outputs').exists())

    def test_missing_project_returns_error(self):
        with tempfile.TemporaryDirectory() as root:
            out, err = io.StringIO(), io.StringIO()
            result = cli.main(['--project', str(Path(root) / 'missing'), 'Edit app.py'], out, err)
            self.assertEqual(result, 2)
            self.assertIn('directory', err.getvalue())
