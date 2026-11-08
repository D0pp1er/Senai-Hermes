import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from senai.integrations.contract import TransportAdapter
from senai.integrations.telegram import TelegramAdapter
from senai.telegram.router import Router
from senai.telegram.service import BotService
from senai.telegram.store import JobStore


def update(identifier=1, user=7, text="Build hello.py"):
    return {"update_id": identifier, "message": {"from": {"id": user},
            "chat": {"id": user, "type": "private"}, "text": text}}


class TelegramAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.store = JobStore(self.project / "outputs" / "state.sqlite3")
        self.router = Router(self.store, {7, 8}, "test_bot", max_pending=1)
        self.api = Mock()
        self.api.redact.side_effect = lambda text: text.replace("secret", "[redacted]")
        self.adapter = TelegramAdapter(self.router, self.api, project=self.project, account="42")

    def test_contract_and_explicit_stable_identity(self):
        self.assertIsInstance(self.adapter, TransportAdapter)
        request = self.adapter.normalize(update())
        self.assertEqual(request.request_id, ("telegram", "42", str(self.project.resolve()), "1"))
        self.assertEqual(request.user_id, "7")
        self.assertEqual(request.delivery_target, "7")
        self.assertEqual(request.text, "Build hello.py")
        self.assertEqual(request.session_scope, self.adapter.normalize(update(user=8)).session_scope)
        other = TelegramAdapter(self.router, self.api, project=self.project, account="43")
        self.assertNotEqual(request.session_scope, other.normalize(update()).session_scope)
        other = TelegramAdapter(self.router, self.api, project=self.project / "other", account="42")
        self.assertNotEqual(request.session_scope, other.normalize(update()).session_scope)

    def test_normalization_does_not_grant_authorization(self):
        request = self.adapter.normalize(update(user=9))
        self.assertIsNotNone(request)
        self.assertFalse(self.adapter.is_authorized(request.user_id))
        self.assertEqual(self.adapter.handle(update(user=9)), [])
        self.assertIsNone(self.store.claim_next())

    def test_invalid_group_bot_and_malformed_updates_are_rejected(self):
        for value in (None, {}, {"update_id": True}, update(user=True)):
            self.assertIsNone(self.adapter.normalize(value))
        value = update()
        value["message"]["chat"]["type"] = "group"
        self.assertIsNone(self.adapter.normalize(value))
        value = update()
        value["message"]["from"]["is_bot"] = True
        self.assertIsNone(self.adapter.normalize(value))

    def test_existing_queue_bounds_and_duplicate_cursor_survive_reconnect(self):
        self.assertIn("Queued", self.adapter.handle(update())[0][1])
        restarted = TelegramAdapter(Router(JobStore(self.store.path), {7}, "test_bot", max_pending=1),
                                    self.api, project=self.project, account="42")
        self.assertEqual(restarted.handle(update()), [])
        self.assertIn("busy", restarted.handle(update(2))[0][1])
        self.assertEqual(self.store.claim_next()["id"], 1)
        self.assertIsNone(self.store.claim_next())

    def test_delivery_parts_are_redacted_and_unicode_bounded(self):
        parts = self.adapter.delivery_parts("secret" + "😀" * 4000)
        self.assertTrue(all(len(part.encode("utf-16-le")) // 2 <= 3500 for part in parts))
        self.assertEqual("".join(parts), "[redacted]" + "😀" * 4000)
        self.adapter.send_text("7", "secret")
        self.api.send_message.assert_called_once_with(7, "[redacted]")

    def test_adapter_reuses_worker_and_rechecks_revocation(self):
        runner = Mock(return_value=("succeeded", "Done"))
        service = BotService(self.api, self.store, self.adapter, runner, transport=self.adapter)
        self.adapter.handle(update())
        with self.store.connection() as db:
            db.execute("INSERT INTO paired_users VALUES (7, 0, 0)")
        self.assertTrue(service.run_one())
        runner.assert_not_called()
        service.deliver_results()
        self.api.send_message.assert_not_called()


    def test_worker_uses_transport_delivery_and_keeps_retry_cursor(self):
        runner = Mock(return_value=("succeeded", "😀" * 4000))
        service = BotService(self.api, self.store, self.adapter, runner, transport=self.adapter)
        self.adapter.handle(update())
        service.run_one()
        self.api.send_message.side_effect = [None, OSError("offline")]
        with self.assertRaises(OSError):
            service.deliver_results()
        self.assertEqual(self.store.pending_results()[0]["parts_sent"], 1)
        self.api.send_message.side_effect = None
        service.deliver_results()
        self.assertFalse(service.run_one())
        runner.assert_called_once()
        self.assertEqual(self.store.pending_results(), [])

    def test_delivery_failure_propagates_for_outbox_retry(self):
        self.api.send_message.side_effect = OSError("offline")
        with self.assertRaises(OSError):
            self.adapter.send_text("7", "hello")
