import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli, codex
from senai.options import CodexOptions


class ConfigurationTests(unittest.TestCase):
    def test_model_profile_and_repeated_config_preserve_values(self):
        options = CodexOptions(model='my-model', profile='dev', config=('a=1', 'b="hello world"'))
        self.assertEqual(options.to_args(), ['--model', 'my-model', '--profile', 'dev', '--config', 'a=1', '--config', 'b="hello world"'])

    def test_cli_passes_configuration(self):
        with tempfile.TemporaryDirectory() as project:
            with patch('senai.cli.run_codex', return_value='Done') as run:
                self.assertEqual(cli.main(['--project', project, '-m', 'my-model', '-p', 'dev', '-c', 'x=1', 'Write code'], io.StringIO(), io.StringIO()), 0)
                self.assertEqual(run.call_args.kwargs['options'].model, 'my-model')
                self.assertEqual(run.call_args.kwargs['options'].profile, 'dev')
                self.assertEqual(run.call_args.kwargs['options'].config, ('x=1',))

    def test_adapter_includes_configuration(self):
        def execute(command, **kwargs):
            self.assertIn('--model', command)
            self.assertEqual(command[command.index('--model') + 1], 'my-model')
            Path(command[command.index('--output-last-message') + 1]).write_text('Done')
            return subprocess.CompletedProcess(command, 0, '', '')
        import subprocess
        with tempfile.TemporaryDirectory() as workspace, patch('senai.codex.subprocess.run', side_effect=execute):
            self.assertEqual(codex.run_codex('Write code', Path(workspace), options=CodexOptions(model='my-model')), 'Done')
