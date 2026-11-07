import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli, codex
from senai.options import CodexOptions


class OutputOptionTests(unittest.TestCase):
    def test_saved_response_is_retained_inside_outputs(self):
        def execute(command, **kwargs):
            output = Path(command[command.index('--output-last-message') + 1])
            output.write_text('Saved response')
            return subprocess.CompletedProcess(command, 0, '', '')
        with tempfile.TemporaryDirectory() as workspace, patch('senai.codex.subprocess.run', side_effect=execute):
            output = Path(workspace) / 'answer.txt'
            self.assertEqual(codex.run_codex('Write code', Path(workspace), options=CodexOptions(output_last_message=str(output))), 'Saved response')
            self.assertEqual(output.read_text(), 'Saved response')

    def test_cli_rejects_response_path_outside_outputs(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex') as run:
            err = io.StringIO()
            self.assertEqual(cli.main(['--project', project, 'Write code', '-o', '../outside.txt'], io.StringIO(), err), 2)
            self.assertIn('outputs/', err.getvalue())
            run.assert_not_called()

    def test_cli_resolves_response_path_inside_workspace(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
            self.assertEqual(cli.main(['--project', project, 'Write code', '-o', 'answer.txt'], io.StringIO(), io.StringIO()), 0)
            self.assertEqual(run.call_args.kwargs['options'].output_last_message, str(Path(project) / 'outputs/answer.txt'))

    def test_json_mode_forwards_streams_without_duplicate_final_text(self):
        def execute(command, **kwargs):
            self.assertIn('--json', command)
            self.assertNotIn('capture_output', kwargs)
            kwargs['stdout'].write('{"type":"thread.started"}\n')
            Path(command[command.index('--output-last-message') + 1]).write_text('Done')
            return subprocess.CompletedProcess(command, 0, None, None)
        with tempfile.TemporaryDirectory() as project, patch('senai.codex.subprocess.run', side_effect=execute):
            out, err = io.StringIO(), io.StringIO()
            self.assertEqual(cli.main(['--project', project, 'Write code', '--json'], out, err), 0)
            self.assertEqual(out.getvalue(), '{"type":"thread.started"}\n')

    def test_existing_response_does_not_hide_missing_new_output(self):
        with tempfile.TemporaryDirectory() as workspace, patch('senai.codex.subprocess.run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            output = Path(workspace) / 'answer.txt'
            output.write_text('Stale response')
            with self.assertRaisesRegex(RuntimeError, 'final response'):
                codex.run_codex('Write code', Path(workspace), options=CodexOptions(output_last_message=str(output)))
