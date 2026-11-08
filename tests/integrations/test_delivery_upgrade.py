import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from senai.telegram.api import TelegramError
from senai.telegram.formatting import split_message
from senai.telegram.router import Router
from senai.telegram.service import BotService
from senai.telegram.store import JobStore

SID = '11111111-1111-4111-8111-111111111111'


class DeliveryUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'state.sqlite3'
        self.store = JobStore(self.path)
        self.store.bind_shared_session(SID)
        self.text = 'start ' + '😀' * 4000 + ' end'
        self.store.consume(1, {'chat_id': 7, 'user_id': 7, 'prompt': 'original request'})
        self.store.claim_next()
        self.store.finish(1, 'succeeded', self.text)
        self.api = Mock()
        self.api.redact.side_effect = lambda text: text
        self.runner = Mock()
        self.service = BotService(self.api, self.store, Router(self.store, {7}, 'test_bot'), self.runner)

    def test_partial_legacy_reply_keeps_exact_remaining_chunks_after_upgrade(self):
        expected = split_message('Request #1: succeeded\n\n' + self.text)
        self.store.mark_part_sent(1)
        self.service.deliver_results()
        self.assertEqual([call.args[1] for call in self.api.send_message.call_args_list], expected[1:])
        self.assertEqual(self.store.shared_session(), SID)
        self.assertEqual(self.store.offset(), 2)
        self.assertEqual(self.store.latest_completed(7)['prompt'], 'original request')
        self.runner.assert_not_called()

    def test_new_reply_retry_uses_saved_chunks_even_after_formatter_changes(self):
        expected = split_message(self.text)
        self.api.send_message.side_effect = [None, TelegramError('offline')]
        with self.assertRaises(TelegramError):
            self.service.deliver_results()
        self.assertEqual(self.store.pending_results()[0]['parts_sent'], 1)
        restarted = JobStore(self.path)
        api = Mock()
        api.redact.side_effect = lambda text: text
        service = BotService(api, restarted, Router(restarted, {7}, 'test_bot'), self.runner)
        with patch('senai.telegram.service.result_text', return_value='different future formatting'):
            service.deliver_results()
        self.assertEqual([call.args[1] for call in api.send_message.call_args_list], expected[1:])
        self.assertEqual(restarted.shared_session(), SID)
        self.runner.assert_not_called()
