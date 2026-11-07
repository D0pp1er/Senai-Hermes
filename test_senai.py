import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import senai


class InputTests(unittest.TestCase):
    def test_prompt_separates_instructions_and_request(self):
        prompt = senai.build_prompt('Create add.py')
        self.assertIn('write and edit code', prompt)
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
                self.assertEqual(run.call_args.args[1], Path(project).resolve())
                self.assertIn('Create add.py', run.call_args.args[0])

    def test_missing_project_returns_error(self):
        with tempfile.TemporaryDirectory() as root:
            out, err = io.StringIO(), io.StringIO()
            result = senai.main(['--project', str(Path(root) / 'missing'), 'Edit app.py'], out, err)
            self.assertEqual(result, 2)
            self.assertIn('directory', err.getvalue())


if __name__ == '__main__':
    unittest.main()
