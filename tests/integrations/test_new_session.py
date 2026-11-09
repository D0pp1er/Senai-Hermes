import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from senai.telegram.conversation import create_conversation_router
from senai.telegram.session_policy import SessionGate
from senai.telegram.router import Router
from senai.telegram.store import JobStore

SID = "11111111-1111-4111-8111-111111111111"
NEW = "22222222-2222-4222-8222-222222222222"


def update(identifier, text, user=7):
    return {"update_id": identifier, "message": {"from": {"id": user},
            "chat": {"id": user, "type": "private"}, "text": text}}


class FreshSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = JobStore(self.root / "outputs/state/state.sqlite3")
        self.store.bind_shared_session(SID)
        self.base = Router(self.store, {7, 8}, "test_bot")
        self.now = datetime(2030, 11, 9, tzinfo=timezone.utc)
        self.gate = SessionGate()
        self.router = self.make_router()
        self.ident = 0

    def make_router(self, **kwargs):
        return create_conversation_router(self.base, project=self.root, account="123",
                clock=lambda: self.now, new_session_users=kwargs.get("users", {7}),
                session_guard=kwargs.get("guard", self.gate.idle))

    def say(self, text, user=7):
        self.ident += 1
        result = self.router.handle(update(self.ident, text, user))
        return result[0][1] if result else ""

    def queue(self, user=8):
        self.ident += 1
        self.store.consume(self.ident, {"chat_id": user, "user_id": user, "prompt": "Existing request"})

    def test_explicit_confirmation_archives_mapping_and_next_turn_can_bind_new_uuid(self):
        result = self.say("/new")
        self.assertIn("all authorized", result)
        self.assertIn("Confirm", result)
        self.assertEqual(self.store.shared_session(), SID)
        self.assertIn("fresh", self.say("Confirm").lower())
        self.assertIsNone(self.store.shared_session())
        self.assertEqual(self.store.session_history()[0]["session_id"], SID)
        self.store.bind_shared_session(NEW)
        self.assertEqual(self.store.shared_session(), NEW)
        self.say("Confirm")
        self.assertEqual(self.store.shared_session(), NEW)

    def test_default_policy_and_missing_execution_guard_refuse_reset(self):
        self.router = self.make_router(users=set())
        self.assertIn("operator", self.say("/new"))
        self.router = self.make_router(guard=None)
        self.assertIn("operator", self.say("/new"))
        self.assertEqual(self.store.shared_session(), SID)

    def test_paired_non_operator_cannot_reset_shared_history(self):
        self.assertIn("operator", self.say("/new", user=8))
        self.assertEqual(self.store.shared_session(), SID)
        self.assertEqual(self.store.session_history(), [])

    def test_cancel_expiry_and_restart_never_reset_silently(self):
        self.say("/new")
        self.say("/cancel")
        self.assertEqual(self.store.shared_session(), SID)
        self.say("/new")
        self.router = self.make_router()
        self.assertEqual(self.store.shared_session(), SID)
        self.now += timedelta(minutes=11)
        self.assertIn("expired", self.say("Confirm"))
        self.assertEqual(self.store.shared_session(), SID)

    def test_queued_or_running_jobs_from_any_user_block_reset(self):
        self.queue()
        self.assertIn("busy", self.say("/new").lower())
        self.store.claim_next()
        self.assertIn("busy", self.say("/new").lower())
        self.assertEqual(self.store.shared_session(), SID)

    def test_job_queued_after_preview_blocks_confirmation_atomically(self):
        self.say("/new")
        self.queue()
        self.assertIn("busy", self.say("Confirm").lower())
        self.assertEqual(self.store.shared_session(), SID)
        self.assertEqual(self.store.session_history(), [])

    def test_cron_or_foreground_execution_gate_blocks_preview_and_confirmation(self):
        with self.gate.execution():
            self.assertIn("busy", self.say("/new").lower())
        self.say("/new")
        with self.gate.execution():
            self.assertIn("busy", self.say("Confirm").lower())
        self.assertEqual(self.store.shared_session(), SID)
        self.say("Confirm")
        self.assertIsNone(self.store.shared_session())

    def test_current_mapping_change_invalidates_old_confirmation(self):
        self.say("/new")
        with self.store.connection() as db:
            db.execute("UPDATE sessions SET session_id=? WHERE name='telegram-shared'", (NEW,))
        self.assertIn("changed", self.say("Confirm").lower())
        self.assertEqual(self.store.shared_session(), NEW)
        self.assertEqual(self.store.session_history(), [])

    def test_revoked_confirmation_and_duplicate_events_do_not_reset_again(self):
        self.say("/new")
        self.store.set_user_status(7, False)
        self.assertEqual(self.say("Confirm"), "")
        self.assertEqual(self.store.shared_session(), SID)
        self.store.set_user_status(7, True)
        self.say("/new")
        self.say("Confirm")
        confirmed = update(self.ident, "Confirm")
        self.store.bind_shared_session(NEW)
        self.assertEqual(self.router.handle(confirmed), [])
        self.assertEqual(self.store.shared_session(), NEW)

    def test_pairing_completed_jobs_and_media_are_unchanged(self):
        self.store.set_user_status(8, True)
        self.queue()
        job = self.store.claim_next()
        self.store.finish(job["id"], "succeeded", "Old result")
        marker = self.store.path.parent / "media.bin"
        marker.write_bytes(b"keep media")
        before = self.store.recent(8)
        self.say("/new")
        self.say("Confirm")
        self.assertEqual(self.store.recent(8), before)
        self.assertTrue(self.store.user_status(8))
        self.assertEqual(marker.read_bytes(), b"keep media")

    def test_archived_uuid_cannot_be_silently_rebound_as_fresh(self):
        self.say("/new")
        self.say("Confirm")
        with self.assertRaises(ValueError):
            self.store.bind_shared_session(SID)
        self.assertIsNone(self.store.shared_session())

    def test_no_existing_mapping_does_not_make_fake_history(self):
        with self.store.connection() as db:
            db.execute("DELETE FROM sessions")
        self.assertIn("next request", self.say("/new").lower())
        self.assertEqual(self.store.session_history(), [])

    def test_gate_supports_additional_scheduled_work_idle_check(self):
        gate = SessionGate(is_idle=lambda: False)
        self.router = self.make_router(guard=gate.idle)
        self.assertIn("busy", self.say("/new").lower())
        self.assertEqual(self.store.shared_session(), SID)


    def test_wrapped_execution_holds_gate_and_preserves_runner_attributes(self):
        from unittest.mock import Mock
        runner = Mock()
        runner.store = self.store
        runner.side_effect = lambda job: self.say("/new")
        wrapped = self.gate.wrap(runner)
        self.assertIs(wrapped.store, self.store)
        self.assertIn("busy", wrapped({"id": 1}).lower())
        self.assertEqual(self.store.shared_session(), SID)

    def test_atomic_store_transition_rechecks_permission(self):
        with self.assertRaises(PermissionError):
            self.store.fresh_shared_session(expected_session=SID, authorize=lambda: False)
        self.assertEqual(self.store.shared_session(), SID)
        self.assertEqual(self.store.session_history(), [])


    def test_cancel_after_interrupted_committed_reset_preserves_archived_history(self):
        from unittest.mock import patch
        self.say("/new")
        original = self.store.fresh_shared_session
        def interrupted(**kwargs):
            original(**kwargs)
            raise KeyboardInterrupt
        with patch.object(self.store, "fresh_shared_session", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                self.say("Confirm")
        self.router = self.make_router()
        self.now += timedelta(hours=1)
        result = self.say("/cancel")
        self.assertIn("/session", result)
        self.assertIsNone(self.router.state.get(7, 7))
        self.assertIsNone(self.store.shared_session())
        self.assertEqual(self.store.session_history()[0]["session_id"], SID)
