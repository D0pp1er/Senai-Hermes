import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import subprocess
import threading

from senai import cli
from senai.telegram.api import TelegramError
from senai.telegram.store import JobStore
from senai.telegram.router import Router
from senai.telegram.service import BotService, instance_lock
from senai.telegram.runner import CommandRunner


def update(identifier, text='Create hello.py', user=7):
    return {'update_id': identifier, 'message': {'from': {'id': user}, 'chat': {'id': user, 'type': 'private'}, 'text': text}}


class TelegramServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.store = JobStore(self.root / 'state.sqlite3')
        self.router = Router(self.store, frozenset({7}), 'test_bot')
        self.api = Mock()
        self.api.redact.side_effect = lambda value: value.replace('secret', '[redacted]')
        self.api.get_updates.return_value = []
        self.runner = Mock(return_value=('succeeded', 'Done'))
        self.service = BotService(self.api, self.store, self.router, self.runner)

    def test_poll_enqueues_without_blocking_on_execution(self):
        self.api.get_updates.return_value = [update(1)]
        self.service.poll_once()
        self.runner.assert_not_called()
        self.assertIn('Queued', self.api.send_message.call_args.args[1])
        self.assertTrue(self.service.run_one())
        self.runner.assert_called_once()
        self.service.deliver_results()
        self.assertIn('Done', self.api.send_message.call_args.args[1])
        self.assertEqual(self.store.pending_results(), [])

    def test_first_boot_discards_offline_messages_without_execution(self):
        self.api.get_updates.return_value = [update(50)]
        self.service.skip_pending()
        self.assertEqual(self.store.offset(), 51)
        self.assertIsNone(self.store.claim_next())

    def test_send_failure_does_not_reexecute_job(self):
        self.router.handle(update(1))
        self.service.run_one()
        self.api.send_message.side_effect = TelegramError('offline')
        with self.assertRaises(TelegramError):
            self.service.deliver_results()
        self.assertFalse(self.service.run_one())
        self.api.send_message.side_effect = None
        self.service.deliver_results()
        self.runner.assert_called_once()
        self.assertEqual(self.store.pending_results(), [])

    def test_long_result_is_split_redacted_and_resumed(self):
        self.runner.return_value = ('succeeded', 'secret ' + '😀' * 4000)
        self.router.handle(update(1))
        self.service.run_one()
        sent = []
        def send(chat, text):
            sent.append(text)
            if len(sent) == 2:
                raise TelegramError('offline')
        self.api.send_message.side_effect = send
        with self.assertRaises(TelegramError):
            self.service.deliver_results()
        self.assertEqual(self.store.pending_results()[0]['parts_sent'], 1)
        self.api.send_message.side_effect = None
        self.service.deliver_results()
        self.assertNotIn('secret', sent[0])
        self.assertTrue(all(len(text.encode('utf-16-le')) // 2 <= 4096 for text in sent))

    def test_revoked_user_cannot_execute_queued_request(self):
        self.router.handle(update(1))
        self.router.allowed_users = frozenset({8})
        self.service.run_one()
        self.runner.assert_not_called()
        self.service.deliver_results()
        self.api.send_message.assert_not_called()

    def test_runner_exception_becomes_terminal_result(self):
        self.runner.side_effect = RuntimeError('secret internal details')
        self.router.handle(update(1))
        self.service.run_one()
        result = self.store.pending_results()[0]
        self.assertEqual(result['status'], 'failed')
        self.assertNotIn('secret', result['result'])

    def test_polling_status_stays_responsive_during_real_worker_thread(self):
        started, release = threading.Event(), threading.Event()
        def slow_runner(job):
            started.set()
            release.wait(3)
            return 'succeeded', 'Done'
        self.service.runner = slow_runner
        self.router.handle(update(1))
        worker = threading.Thread(target=self.service.run_one)
        worker.start()
        try:
            self.assertTrue(started.wait(2))
            self.api.get_updates.return_value = [update(2, '/status')]
            self.service.poll_once()
            self.assertIn('running', self.api.send_message.call_args.args[1])
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())

    def test_single_instance_lock(self):
        with instance_lock(self.root / 'bot.lock'):
            with self.assertRaisesRegex(ValueError, 'already running'):
                with instance_lock(self.root / 'bot.lock'):
                    pass


class TelegramRunnerTests(unittest.TestCase):
    def test_child_uses_literal_request_and_does_not_inherit_bot_token(self):
        with tempfile.TemporaryDirectory() as project:
            root = Path(project)
            runner = CommandRunner(root, root / 'outputs/state', skip_git_repo_check=True)
            def execute(command, **kwargs):
                self.assertEqual(command[-2:], ['--', '--model malicious; $literal'])
                self.assertIn('--skip-git-repo-check', command)
                self.assertEqual(command[command.index('--ask-for-approval') + 1], 'never')
                self.assertNotIn('TELEGRAM_BOT_TOKEN', kwargs['env'])
                self.assertNotIn('shell', kwargs)
                kwargs['stdout'].write('Done')
                return subprocess.CompletedProcess(command, 0)
            with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': '123:secret'}), patch('senai.telegram.runner.subprocess.run', side_effect=execute):
                self.assertEqual(runner({'id': 1, 'prompt': '--model malicious; $literal'}), ('succeeded', 'Done'))
            self.assertTrue((root / 'outputs/state/jobs/1/stdout.txt').exists())

    def test_nonzero_child_returns_failure_diagnostics(self):
        with tempfile.TemporaryDirectory() as project:
            root = Path(project)
            runner = CommandRunner(root, root / 'outputs/state')
            def execute(command, **kwargs):
                kwargs['stderr'].write('Codex failed')
                return subprocess.CompletedProcess(command, 2)
            with patch('senai.telegram.runner.subprocess.run', side_effect=execute):
                self.assertEqual(runner({'id': 1, 'prompt': 'Write code'}), ('failed', 'Codex failed'))


class TelegramCLITests(unittest.TestCase):
    def test_telegram_help_needs_no_credentials(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(SystemExit) as result:
            cli.main(['telegram', '--help'])
        self.assertEqual(result.exception.code, 0)

    def test_missing_credentials_fail_before_network(self):
        with patch.dict('os.environ', {}, clear=True), patch('senai.telegram.cli.BotAPI') as api:
            err = io.StringIO()
            self.assertEqual(cli.main(['telegram'], io.StringIO(), err), 2)
            api.assert_not_called()
            self.assertIn('TELEGRAM_BOT_TOKEN', err.getvalue())

    def test_check_reports_username_without_token_or_execution(self):
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': '123:secret'}, clear=True), patch('senai.telegram.cli.BotAPI') as api:
            api.return_value.redact.side_effect = lambda text: text.replace('123:secret', '[redacted]')
            api.return_value.get_me.return_value = {'id': 123, 'is_bot': True, 'username': 'test_bot'}
            api.return_value.get_webhook_info.return_value = {'url': ''}
            out = io.StringIO()
            self.assertEqual(cli.main(['telegram', '--check'], out, io.StringIO()), 0)
            self.assertIn('@test_bot', out.getvalue())
            self.assertNotIn('secret', out.getvalue())
            api.return_value.get_updates.assert_not_called()

    def test_existing_webhook_is_not_deleted_automatically(self):
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': '123:secret'}, clear=True), patch('senai.telegram.cli.BotAPI') as api:
            api.return_value.redact.side_effect = lambda text: text.replace('123:secret', '[redacted]')
            api.return_value.get_me.return_value = {'id': 123, 'is_bot': True, 'username': 'test_bot'}
            api.return_value.get_webhook_info.return_value = {'url': 'https://example.invalid/hook'}
            err = io.StringIO()
            self.assertEqual(cli.main(['telegram', '--check'], io.StringIO(), err), 2)
            self.assertIn('webhook', err.getvalue())
            api.return_value.delete_webhook.assert_not_called()

    def test_setup_prints_private_user_id_without_sending_or_execution(self):
        with patch.dict('os.environ', {'TELEGRAM_BOT_TOKEN': '123:secret'}, clear=True), patch('senai.telegram.cli.BotAPI') as api, patch('senai.telegram.cli.secrets.token_hex', return_value='fixture'):
            api.return_value.get_me.return_value = {'id': 123, 'is_bot': True, 'username': 'test_bot'}
            api.return_value.get_webhook_info.return_value = {'url': ''}
            api.return_value.get_updates.return_value = [update(1, 'senai-setup-fixture')]
            out = io.StringIO()
            self.assertEqual(cli.main(['telegram', '--setup'], out, io.StringIO()), 0)
            self.assertIn('TELEGRAM_ALLOWED_USER_IDS=7', out.getvalue())
            self.assertNotIn('123:secret', out.getvalue())
            api.return_value.send_message.assert_not_called()
