import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

from senai.telegram.conversation import create_conversation_router, DraftFieldError
from senai.telegram.router import Router
from senai.telegram.store import JobStore


def update(identifier, text, user=7, kind="private", mention=None):
    return {"update_id": identifier, "message": {"from": {"id": user},
            "chat": {"id": user, "type": kind}, "text": text}}


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.store = JobStore(self.project / "outputs/state/state.sqlite3")
        self.base = Router(self.store, {7, 8}, "test_bot")
        self.now = datetime(2030, 11, 9, 10, tzinfo=timezone.utc)
        self.parser = Mock(side_effect=self.parse)
        self.create = Mock(return_value="schedule-1")
        self.advanced = Mock(return_value=[(7, "Existing schedules")])
        self.router = self.make_router()
        self.ident = 0

    def make_router(self):
        return create_conversation_router(self.base, project=self.project, account="123",
                parse_schedule=self.parser, create_schedule=self.create,
                advanced_handler=self.advanced, clock=lambda: self.now, timezone="Asia/Dhaka")

    def parse(self, when, repeat, *, now, timezone):
        if when == "bad":
            raise ValueError("server detail must not leak")
        if repeat == "bad":
            raise DraftFieldError("repeat", "Choose once or daily.")
        return {"at": now + timedelta(minutes=2), "timezone": timezone,
                "every": 86400 if repeat == "daily" else None, "cron": None}

    def say(self, text, user=7):
        self.ident += 1
        result = self.router.handle(update(self.ident, text, user))
        return result[0][1] if result else ""

    def preview(self, user=7):
        for text in ("/cron create", "Tea", "Remind me to make tea", "in 2 minutes"):
            self.say(text, user)
        return self.say("daily", user)

    def test_sequential_wizard_requires_full_preview_and_explicit_confirmation(self):
        self.assertIn("name", self.say("/cron create").lower())
        self.assertIn("task", self.say("Tea").lower())
        self.assertIn("tomorrow", self.say("Remind me to make tea"))
        self.assertIn("repeat", self.say("in 2 minutes").lower())
        preview = self.say("daily")
        for expected in ("Tea", "Remind me to make tea", "2030-11-09", "16:02", "Asia/Dhaka", "daily", "this private chat", "Confirm", "/cancel"):
            self.assertIn(expected, preview)
        self.create.assert_not_called()
        self.say("maybe")
        self.create.assert_not_called()
        self.assertIn("created", self.say("Confirm").lower())
        self.create.assert_called_once()
        spec = self.create.call_args.args[0]
        self.assertEqual(spec["name"], "Tea")
        self.assertEqual(spec["every"], 86400)
        self.assertEqual(self.create.call_args.kwargs["target"]["user_id"], 7)
        self.assertIsNone(self.store.claim_next())

    def test_duplicate_updates_do_not_advance_or_create_twice(self):
        first = update(1, "/cron create")
        self.router.handle(first)
        self.assertEqual(self.router.handle(first), [])
        self.ident = 1
        for text in ("Tea", "Make tea", "in 2 minutes", "once"):
            self.say(text)
        confirmed = update(6, "Confirm")
        self.router.handle(confirmed)
        self.assertEqual(self.router.handle(confirmed), [])
        self.ident = 6
        self.say("Confirm")
        self.create.assert_called_once()

    def test_per_user_concurrent_drafts_are_isolated(self):
        self.say("/cron create", 7)
        self.say("/cron create", 8)
        self.say("Alice", 7)
        self.say("Bob", 8)
        self.assertIn("when", self.say("Task A", 7).lower())
        self.assertIn("when", self.say("Task B", 8).lower())
        self.say("/cancel", 7)
        self.assertIn("repeat", self.say("in 2 minutes", 8).lower())
        self.create.assert_not_called()

    def test_invalid_fields_have_actionable_retry_messages(self):
        self.say("/cron create")
        self.assertIn("name", self.say("x" * 81).lower())
        self.say("Tea")
        self.assertIn("task", self.say(" ").lower())
        self.say("Task")
        retry = self.say("bad")
        self.assertIn("tomorrow", retry)
        self.assertNotIn("server detail", retry)
        self.say("in 2 minutes")
        self.assertIn("repeat", self.say("bad").lower())
        self.create.assert_not_called()

    def test_expiry_and_cancel_never_queue_model_work(self):
        self.say("/cron create")
        self.now += timedelta(minutes=11)
        self.assertIn("expired", self.say("Tea").lower())
        self.say("/cron create")
        self.assertIn("cancel", self.say("/cancel").lower())
        self.assertIsNone(self.store.claim_next())
        self.create.assert_not_called()

    def test_restart_preserves_draft_and_confirmation_time_is_frozen(self):
        self.preview()
        self.router = self.make_router()
        self.now += timedelta(seconds=20)
        self.say("Confirm")
        self.assertEqual(self.create.call_args.args[0]["at"], self.now - timedelta(seconds=20) + timedelta(minutes=2))

    def test_past_preview_requires_time_retry_not_creation(self):
        self.preview()
        self.now += timedelta(minutes=3)
        self.assertIn("when", self.say("Confirm").lower())
        self.create.assert_not_called()

    def test_revocation_unauthorized_group_and_wrong_bot_never_create(self):
        self.preview()
        self.store.set_user_status(7, False)
        self.assertEqual(self.say("Confirm"), "")
        self.store.set_user_status(7, True)
        self.say("Confirm")
        self.create.assert_not_called()
        self.assertEqual(self.router.handle(update(100, "/cron create", 9)), [])
        self.assertEqual(self.router.handle(update(101, "/cron create", 8, kind="group")), [])
        self.assertEqual(self.router.handle(update(102, "/cron@test_other create", 8)), [])

    def test_creation_failure_is_uncertain_and_never_automatically_retried(self):
        self.preview()
        self.create.side_effect = RuntimeError("private backend diagnostics")
        result = self.say("Confirm")
        self.assertIn("/cron list", result)
        self.assertNotIn("private backend", result)
        self.say("Confirm")
        self.create.assert_called_once()

    def test_creation_field_error_returns_to_correct_question(self):
        self.preview()
        self.create.side_effect = DraftFieldError("name", "That name is already used.")
        self.assertIn("name", self.say("Confirm").lower())
        self.assertIn("task", self.say("Different name").lower())

    def test_advanced_json_also_previews_before_creation(self):
        result = self.say('/cron create {"name":"Tea","prompt":"Make tea","at":"2030-11-10T09:00:00+06:00"}')
        self.assertIn("Confirm", result)
        self.create.assert_not_called()
        self.say("Confirm")
        self.create.assert_called_once()

    def test_malformed_json_has_field_level_help_and_advanced_commands_delegate(self):
        self.assertIn("JSON", self.say('/cron create {bad'))
        self.assertEqual(self.say("/cron list"), "Existing schedules")
        self.advanced.assert_called_once()

    def test_missing_parser_is_actionable_and_cannot_create_unsendable_schedule(self):
        router = create_conversation_router(self.base, project=self.project, account="123")
        result = router.handle(update(1, "/cron create"))[0][1]
        self.assertIn("operator", result)
        self.assertIsNone(self.store.claim_next())

    def test_normal_text_and_voice_commands_still_reach_existing_router(self):
        self.assertIn("Queued", self.say("Write hello.py"))
        self.assertEqual(self.store.claim_next()["prompt"], "Write hello.py")

    def test_generic_advanced_rejection_is_replaced_with_actionable_help(self):
        self.advanced.return_value = [(7, "Cron command rejected; check arguments, ownership or current revision. Use /cron show ID to review.")]
        result = self.say("/cron edit nope")
        self.assertNotIn("command rejected", result)
        self.assertIn("revision", result.lower())


    def test_calendar_json_preview_uses_actual_next_occurrence(self):
        result = self.say('/cron create {"name":"Tea","prompt":"Make tea","at":"2030-11-10T09:07:00+06:00","cron":"0 9 * * *"}')
        self.assertIn("2030-11-11 09:00:00", result)
        self.create.assert_not_called()

    def test_real_merged_store_creator_keeps_explicit_authorized_destination(self):
        from senai.cron.store import Store
        from senai.telegram.conversation import bind_schedule_creator
        cron = Store(self.project / "outputs/cron.db", clock=lambda: self.now)
        authorization = Mock()
        self.router.create_schedule = bind_schedule_creator(cron, project=self.project, authorize_target=authorization)
        self.preview()
        self.say("Confirm")
        schedule = cron.list()[0]
        import json
        destination = json.loads(schedule["delivery_target"])
        self.assertEqual(destination["project"], str(self.project))
        self.assertEqual(destination["chat_id"], 7)
        self.assertEqual(destination["account"], "123")
        authorization.assert_called_once_with(destination)

    def test_naive_parser_output_is_rejected_with_time_examples(self):
        for text in ("/cron create", "Tea", "Make tea"):
            self.say(text)
        self.parser.side_effect = None
        self.parser.return_value = {"at": self.now.replace(tzinfo=None), "timezone": "Asia/Dhaka"}
        self.assertIn("tomorrow", self.say("in 2 minutes"))
        self.create.assert_not_called()
