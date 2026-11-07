"""Offline Telegram-to-installed-senai integration with a real fake-Codex child."""

import json
import runpy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from senai.telegram.runner import CommandRunner
from senai.telegram.router import Router
from senai.telegram.service import BotService
from senai.telegram.store import JobStore


class TelegramIntegrationTests(unittest.TestCase):
    def test_authorized_message_executes_once_and_result_returns_to_its_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / 'bin'
            binary.mkdir()
            executable = binary / 'codex'
            executable.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.read()
Path('telegram_smoke.py').write_text('VALUE = 42\\n')
Path('telegram_trace.json').write_text(json.dumps({'prompt': prompt, 'args': args, 'token_present': 'TELEGRAM_BOT_TOKEN' in os.environ}))
Path(args[args.index('--output-last-message') + 1]).write_text('Created telegram_smoke.py')
""")
            executable.chmod(0o755)
            store = JobStore(root / 'outputs/state/state.sqlite3')
            router = Router(store, frozenset({7}), 'test_bot')
            runner = CommandRunner(root, root / 'outputs/state', skip_git_repo_check=True)
            def update(identifier, user, text):
                return {'update_id': identifier, 'message': {'from': {'id': user}, 'chat': {'id': user, 'type': 'private'}, 'text': text}}
            authorized = update(2, 7, '/run Create telegram_smoke.py')
            class API:
                def __init__(self):
                    self.sent = []
                    self.updates = [update(1, 99, 'Unauthorized request'), authorized]
                def get_updates(self, *args, **kwargs):
                    updates, self.updates = self.updates, []
                    return updates
                def send_message(self, chat_id, text):
                    self.sent.append((chat_id, text))
                def redact(self, text):
                    return text.replace('123:private-token', '[redacted]')
            api = API()
            service = BotService(api, store, router, runner)
            environment = {'PATH': str(binary) + os.pathsep + os.environ['PATH'], 'TELEGRAM_BOT_TOKEN': '123:private-token'}
            with patch.dict(os.environ, environment):
                service.poll_once()
                self.assertTrue(service.run_one())
                self.assertFalse(service.run_one())
                service.deliver_results()
                api.updates = [authorized]
                service.poll_once()
                self.assertFalse(service.run_one())
            self.assertEqual(runpy.run_path(str(root / 'outputs/telegram_smoke.py'))['VALUE'], 42)
            trace = json.loads((root / 'outputs/telegram_trace.json').read_text())
            self.assertIn('Create telegram_smoke.py', trace['prompt'])
            self.assertFalse(trace['token_present'])
            self.assertIn('--skip-git-repo-check', trace['args'])
            self.assertTrue(all(chat == 7 for chat, text in api.sent))
            self.assertEqual(sum('Created telegram_smoke.py' in text for chat, text in api.sent), 1)
            self.assertEqual(store.pending_results(), [])
