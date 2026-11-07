import io
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError

from senai.telegram.api import BotAPI, TelegramError
from senai.telegram.config import load_credentials
from senai.telegram.formatting import split_message


class TelegramAPITests(unittest.TestCase):
    def response(self, value):
        class Response(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()
        return Response(json.dumps(value).encode())

    def test_polling_sends_offset_timeout_and_message_filter(self):
        seen = []
        def opener(request, timeout):
            seen.append((request, timeout))
            return self.response({'ok': True, 'result': [{'update_id': 42}]})
        api = BotAPI('123:private-secret', opener=opener)
        self.assertEqual(api.get_updates(42, timeout=10), [{'update_id': 42}])
        payload = json.loads(seen[0][0].data)
        self.assertEqual(payload['offset'], 42)
        self.assertEqual(payload['timeout'], 10)
        self.assertEqual(payload['allowed_updates'], ['message'])
        self.assertGreater(seen[0][1], payload['timeout'])

    def test_replies_use_plain_text_and_disable_link_previews(self):
        seen = []
        def opener(request, timeout):
            seen.append(json.loads(request.data))
            return self.response({'ok': True, 'result': {'message_id': 1}})
        BotAPI('123:private-secret', opener=opener).send_message(7, '<literal>&text')
        self.assertEqual(seen[0]['text'], '<literal>&text')
        self.assertNotIn('parse_mode', seen[0])
        self.assertTrue(seen[0]['link_preview_options']['is_disabled'])

    def test_errors_never_expose_token_or_request_url(self):
        def opener(request, timeout):
            raise URLError('https://api.telegram.org/bot123:private-secret/getUpdates')
        with self.assertRaises(TelegramError) as error:
            BotAPI('123:private-secret', opener=opener).get_updates(0)
        self.assertNotIn('private-secret', str(error.exception))
        self.assertNotIn('https://', str(error.exception))

    def test_rate_limit_retains_retry_after_without_token(self):
        def opener(request, timeout):
            body = io.BytesIO(json.dumps({'ok': False, 'error_code': 429, 'parameters': {'retry_after': 3}}).encode())
            raise HTTPError(request.full_url, 429, 'Rate limited', {}, body)
        with self.assertRaises(TelegramError) as error:
            BotAPI('123:private-secret', opener=opener).send_message(7, 'Hello')
        self.assertEqual(error.exception.retry_after, 3)
        self.assertEqual(error.exception.status, 429)

    def test_malformed_response_has_sanitized_error(self):
        api = BotAPI('123:private-secret', opener=lambda *a, **k: io.BytesIO(b'not json'))
        with self.assertRaises(TelegramError):
            api.get_updates(0)


class TelegramConfigTests(unittest.TestCase):
    def test_token_and_allowlist_are_required(self):
        for values in [{}, {'TELEGRAM_BOT_TOKEN': '123:secret'}, {'TELEGRAM_BOT_TOKEN': '123:secret', 'TELEGRAM_ALLOWED_USER_IDS': '0,-1'}]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                load_credentials(values)

    def test_environment_overrides_local_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'telegram.env'
            path.write_text('TELEGRAM_BOT_TOKEN=123:secret\nTELEGRAM_ALLOWED_USER_IDS=7,8\n')
            token, users = load_credentials({'TELEGRAM_ALLOWED_USER_IDS': '9'}, env_file=path)
            self.assertEqual(token, '123:secret')
            self.assertEqual(users, frozenset({9}))

    def test_setup_requires_only_token(self):
        self.assertEqual(load_credentials({'TELEGRAM_BOT_TOKEN': '123:secret'}, require_users=False), ('123:secret', frozenset()))

    def test_env_file_is_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'telegram.env'
            path.write_text('UNEXPECTED=$(touch should-not-exist)\n')
            with self.assertRaises(ValueError):
                load_credentials({}, env_file=path)
            self.assertFalse((Path(directory) / 'should-not-exist').exists())


class TelegramFormattingTests(unittest.TestCase):
    def test_long_unicode_messages_preserve_every_character(self):
        text = 'hello <&> বাংলা ' + '😀' * 3000 + 'end'
        parts = split_message(text)
        self.assertEqual(''.join(parts), text)
        self.assertTrue(all(len(part.encode('utf-16-le')) // 2 <= 3500 for part in parts))

    def test_empty_text_still_produces_sendable_content(self):
        self.assertTrue(split_message('')[0])
