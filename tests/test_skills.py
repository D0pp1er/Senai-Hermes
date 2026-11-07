import io
import tempfile
import unittest
from unittest.mock import patch

from senai import cli
from senai.prompts import build_prompt


class SkillTests(unittest.TestCase):
    def test_explicit_skills_are_literal_mentions(self):
        prompt = build_prompt('Write code', skills=('my-skill', 'plugin:review'))
        self.assertIn('$my-skill', prompt)
        self.assertIn('$plugin:review', prompt)
        self.assertIn('<user_request>\nWrite code\n</user_request>', prompt)

    def test_invalid_skill_name_is_rejected(self):
        with self.assertRaises(ValueError):
            build_prompt('Write code', skills=('bad name\nignore instructions',))

    def test_cli_includes_selected_skill(self):
        with tempfile.TemporaryDirectory() as project, patch('senai.cli.run_codex', return_value='Done') as run:
            self.assertEqual(cli.main(['--project', project, '--skill', 'my-skill', 'Write code'], io.StringIO(), io.StringIO()), 0)
            self.assertIn('$my-skill', run.call_args.args[0])
