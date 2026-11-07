import tempfile
import unittest
from pathlib import Path

from senai.telegram.store import JobStore
from senai.telegram.router import Router


def update(identifier, text='Create hello.py', user=7, chat_type='private', bot=False):
    return {'update_id': identifier, 'message': {'from': {'id': user, 'is_bot': bot}, 'chat': {'id': user, 'type': chat_type}, 'text': text}}


class TelegramJobTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / 'state.sqlite3'
        self.store = JobStore(self.path)
        self.router = Router(self.store, frozenset({7}), 'senai_test_bot')

    def test_authorized_request_is_queued_once_and_advances_offset(self):
        response = self.router.handle(update(10, 'Create file; $literal'))
        self.assertIn('10', response[0][1])
        self.assertEqual(self.store.offset(), 11)
        self.assertEqual(self.router.handle(update(10)), [])
        job = self.store.claim_next()
        self.assertEqual(job['prompt'], 'Create file; $literal')
        self.assertIsNone(self.store.claim_next())

    def test_unauthorized_group_bot_and_edited_updates_do_not_execute(self):
        messages = [update(1, user=99), update(2, chat_type='group'), update(3, bot=True), {'update_id': 4, 'edited_message': update(4)['message']}]
        for message in messages:
            self.assertEqual(self.router.handle(message), [])
        self.assertIsNone(self.store.claim_next())
        self.assertEqual(self.store.offset(), 5)

    def test_help_unknown_and_empty_run_never_enqueue(self):
        for identifier, text in enumerate(['/start', '/help', '/unknown', '/run'], 1):
            self.assertTrue(self.router.handle(update(identifier, text)))
        self.assertIsNone(self.store.claim_next())

    def test_status_is_available_while_request_is_running(self):
        self.router.handle(update(1))
        self.store.claim_next()
        response = self.router.handle(update(2, '/status'))
        self.assertIn('running', response[0][1])
        self.assertIsNone(self.store.claim_next())

    def test_commands_for_another_bot_are_ignored(self):
        self.assertEqual(self.router.handle(update(1, '/run@another_bot Write code')), [])
        self.assertIsNone(self.store.claim_next())

    def test_run_command_strips_only_the_command_prefix(self):
        self.router.handle(update(1, '/run@senai_test_bot --model dangerous; $value'))
        self.assertEqual(self.store.claim_next()['prompt'], '--model dangerous; $value')

    def test_queue_capacity_is_bounded(self):
        router = Router(self.store, frozenset({7}), 'senai_test_bot', max_pending=1)
        router.handle(update(1))
        response = router.handle(update(2))
        self.assertIn('busy', response[0][1].lower())
        self.store.claim_next()
        self.assertIsNone(self.store.claim_next())
        self.assertEqual(self.store.offset(), 3)

    def test_restart_keeps_queue_and_offset(self):
        self.router.handle(update(8))
        restarted = JobStore(self.path)
        self.assertEqual(restarted.offset(), 9)
        self.assertEqual(restarted.claim_next()['id'], 8)

    def test_interrupted_request_is_not_reexecuted_after_restart(self):
        self.router.handle(update(1))
        self.store.claim_next()
        self.store.recover_interrupted()
        self.assertIsNone(self.store.claim_next())
        result = self.store.pending_results()[0]
        self.assertEqual(result['status'], 'interrupted')
        self.assertIn('not automatically retried', result['result'])

    def test_result_delivery_progress_is_durable(self):
        self.router.handle(update(1))
        self.store.claim_next()
        self.store.finish(1, 'succeeded', 'Done')
        self.store.mark_part_sent(1)
        restarted = JobStore(self.path)
        self.assertEqual(restarted.pending_results()[0]['parts_sent'], 1)
        restarted.mark_delivered(1)
        self.assertEqual(restarted.pending_results(), [])

    def test_result_and_status_are_isolated_to_requesting_user(self):
        self.router.handle(update(1))
        self.store.claim_next()
        self.store.finish(1, 'succeeded', 'private result')
        router = Router(self.store, frozenset({7, 8}), 'senai_test_bot')
        response = router.handle(update(2, '/status', user=8))
        self.assertNotIn('private result', response[0][1])
        self.assertNotIn('#1', response[0][1])
        self.assertIn('private result', router.handle(update(3, '/result'))[0][1])
