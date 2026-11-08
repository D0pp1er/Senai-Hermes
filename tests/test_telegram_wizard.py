import io
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from senai import cli
from senai.telegram.api import TelegramError
from senai.telegram.config import default_env_file, write_token_file
from senai.telegram.store import JobStore
from senai.telegram.wizard import configure_project


class TelegramWizardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'project'
        self.project.mkdir()
        self.path = self.root / 'config/telegram.env'
        self.api = Mock()
        self.api.get_me.return_value = {'id': 123, 'is_bot': True, 'username': 'test_bot'}
        self.api.get_webhook_info.return_value = {'url': ''}
        self.out = io.StringIO()
        def poll(offset=None, **kwargs):
            if offset == -1:
                return []
            code = re.findall(r'/pair ([A-Za-z0-9_-]+)', self.out.getvalue())[-1]
            return [{'update_id': 10, 'message': {'from': {'id': 654321}, 'chat': {'id': 654321, 'type': 'private'}, 'text': '/pair ' + code}}]
        self.api.get_updates.side_effect = poll

    def configure(self, prompt=lambda message: '123:private-token'):
        return configure_project(self.project, env_file=self.path, stdout=self.out, prompt=prompt, api_factory=lambda token: self.api, environ={})

    def test_setup_automates_token_check_pairing_and_private_file(self):
        result = self.configure()
        self.assertEqual(result.token, '123:private-token')
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertIn('TELEGRAM_BOT_TOKEN=123:private-token', self.path.read_text())
        self.assertNotIn('private-token', self.out.getvalue())
        self.assertNotIn('private-token', repr(result))
        store = JobStore(self.project / 'outputs/.senai-telegram/123/state.sqlite3')
        self.assertTrue(store.user_status(654321))
        self.api.send_message.assert_not_called()

    def test_saved_token_can_be_reused_without_an_export(self):
        write_token_file(self.path, '123:existing-token')
        result = self.configure(prompt=lambda message: '')
        self.assertEqual(result.token, '123:existing-token')

    def test_invalid_remote_credentials_are_not_saved(self):
        self.api.get_me.side_effect = TelegramError('Telegram getMe failed (status 401).', status=401)
        with self.assertRaises(TelegramError):
            self.configure()
        self.assertFalse(self.path.exists())

    def test_secret_file_inside_project_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            configure_project(self.project, env_file=self.project / 'token.env', stdout=self.out, prompt=lambda message: '123:secret', api_factory=lambda token: self.api, environ={})

    def test_auto_config_is_per_project_and_not_personalized(self):
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.root / 'xdg')}):
            first = default_env_file(self.project)
            second = default_env_file(self.root / 'another-project')
        self.assertNotEqual(first, second)
        self.assertTrue(first.is_relative_to(self.root / 'xdg'))

    def test_private_file_refuses_symlink_target(self):
        self.path.parent.mkdir(parents=True)
        target = self.root / 'target'
        target.write_text('preserve')
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):
            write_token_file(self.path, '123:secret')
        self.assertEqual(target.read_text(), 'preserve')

    def test_check_auto_loads_saved_configuration(self):
        write_token_file(self.path, '123:saved-token')
        with patch.dict(os.environ, {}, clear=True), patch('senai.telegram.cli.default_env_file', return_value=self.path), patch('senai.telegram.cli.BotAPI', return_value=self.api):
            self.assertEqual(cli.main(['telegram', '--project', str(self.project), '--check'], self.out, io.StringIO()), 0)
        self.assertIn('@test_bot', self.out.getvalue())

    def test_backlog_is_drained_before_pair_code_is_shown(self):
        original = self.api.get_updates.side_effect
        def poll(offset=None, **kwargs):
            if offset == -1:
                self.assertNotIn('/pair ', self.out.getvalue())
            return original(offset, **kwargs)
        self.api.get_updates.side_effect = poll
        self.configure()

    def test_setup_script_has_valid_syntax_and_help_needs_no_token(self):
        root = Path(__file__).resolve().parents[1]
        script = root / 'scripts/setup_telegram.sh'
        subprocess.run(['bash', '-n', str(script)], check=True)
        result = subprocess.run(['bash', str(script), '--help'], cwd=root, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--configure', result.stdout)
        self.assertNotIn('/home/rk', script.read_text())
