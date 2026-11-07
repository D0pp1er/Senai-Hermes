import io
import tempfile
import unittest
from unittest.mock import patch

from senai import cli
from senai.options import CodexOptions


class SearchTests(unittest.TestCase):
    def test_search_is_opt_in(self):
        self.assertNotIn('web_search="live"', CodexOptions().to_args())
        self.assertEqual(CodexOptions(search=True).to_args(), ['--config', 'web_search="live"'])

    def test_cli_forwards_search_choice(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
            self.assertEqual(cli.main(['--project', project, '--search', 'Use current docs'], io.StringIO(), io.StringIO()), 0)
            self.assertTrue(run.call_args.kwargs['options'].search)
