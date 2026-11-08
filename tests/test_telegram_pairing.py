import tempfile
import unittest
from pathlib import Path

from senai.telegram.store import JobStore
from senai.telegram.pairing import PairingManager
from senai.telegram.router import Router
from senai.telegram.service import BotService
from unittest.mock import Mock


def update(identifier, user, text, chat_type='private'):
    return {'update_id': identifier, 'message': {'from': {'id': user}, 'chat': {'id': user, 'type': chat_type}, 'text': text}}


class PairingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = JobStore(Path(self.temporary.name) / 'state.sqlite3')
        self.now = 1000
        self.pairing = PairingManager(self.store, clock=lambda: self.now)

    def test_pairing_is_single_use_and_not_stored_as_plaintext(self):
        code = self.pairing.issue()
        self.assertTrue(self.pairing.redeem(code, 7, 7))
        self.assertFalse(self.pairing.redeem(code, 8, 8))
        self.assertTrue(self.store.user_status(7))
        self.assertNotIn(code.encode(), self.store.path.read_bytes())

    def test_expired_code_never_grants_access(self):
        code = self.pairing.issue(ttl=10)
        self.now += 11
        self.assertFalse(self.pairing.redeem(code, 7, 7))
        self.assertIsNone(self.store.user_status(7))

    def test_new_code_invalidates_previous_unused_code(self):
        old, new = self.pairing.issue(), self.pairing.issue()
        self.assertFalse(self.pairing.redeem(old, 7, 7))
        self.assertTrue(self.pairing.redeem(new, 7, 7))

    def test_any_private_user_can_pair_with_local_code_and_survive_restart(self):
        router = Router(self.store, frozenset(), 'test_bot')
        self.assertEqual(router.handle(update(1, 12345, 'Write code')), [])
        code = PairingManager(self.store).issue()
        reply = router.handle(update(2, 12345, '/pair ' + code))
        self.assertIn('paired', reply[0][1].lower())
        restarted = Router(JobStore(self.store.path), frozenset(), 'test_bot')
        self.assertTrue(restarted.is_authorized(12345))
        self.assertIn('Queued', restarted.handle(update(3, 12345, 'Write code'))[0][1])

    def test_group_cannot_redeem_pairing_code(self):
        code = PairingManager(self.store).issue()
        router = Router(self.store, frozenset(), 'test_bot')
        self.assertEqual(router.handle(update(1, 7, '/pair ' + code, 'group')), [])
        self.assertIsNone(self.store.user_status(7))

    def test_revocation_overrides_legacy_allowlist(self):
        router = Router(self.store, frozenset({7}), 'test_bot')
        self.assertTrue(router.is_authorized(7))
        self.store.set_user_status(7, False)
        self.assertFalse(router.is_authorized(7))
        self.assertEqual(router.handle(update(1, 7, 'Write code')), [])

    def test_revoked_pair_cannot_execute_queued_work(self):
        code = PairingManager(self.store).issue()
        PairingManager(self.store).redeem(code, 7, 7)
        router = Router(self.store, frozenset(), 'test_bot')
        router.handle(update(1, 7, 'Write code'))
        self.store.set_user_status(7, False)
        runner = Mock()
        service = BotService(Mock(), self.store, router, runner)
        service.run_one()
        runner.assert_not_called()

    def test_session_command_shows_one_shared_id_to_paired_users(self):
        self.store.bind_shared_session('11111111-1111-4111-8111-111111111111')
        router = Router(self.store, frozenset({7, 8}), 'test_bot')
        self.assertEqual(router.handle(update(1, 7, '/session'))[0][1], router.handle(update(2, 8, '/session'))[0][1])
