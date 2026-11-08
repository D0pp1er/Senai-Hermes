import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from senai.cli import main
from senai.cron_runtime import TelegramCron
from senai.telegram.router import Router
from senai.telegram.service import BotService
from senai.telegram.store import JobStore
from senai.telegram.api import TelegramError

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


class API:
    def __init__(self):
        self.sent = []
        self.failure = None
    def redact(self, text):
        return str(text).replace("private-token", "[redacted]")
    def send_message(self, chat, text):
        if self.failure:
            raise self.failure
        self.sent.append((chat, text))
        return {"message_id": len(self.sent)}
    def get_updates(self, *args, **kwargs):
        return []


class CronRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.jobs = JobStore(self.root / "outputs/telegram/state.sqlite3")
        self.router = Router(self.jobs, frozenset({7, 8}), "test_bot")
        self.api = API()
        self.executions = []
        def run(job):
            self.executions.append(job)
            return "succeeded", "Verified scheduled answer"
        self.runner = run
        self.manager = self.make_manager()
        self.update_id = 0

    def make_manager(self):
        return TelegramCron(project=self.root, account="123", router=self.router,
                            runner=self.runner, api=self.api, clock=lambda: NOW)

    def message(self, text, user=7):
        self.update_id += 1
        return {"update_id": self.update_id, "message": {"from": {"id": user},
                "chat": {"id": user, "type": "private"}, "text": text}}

    def create(self, **changes):
        spec = {"name": "reminder", "prompt": "Check the project",
                "at": NOW.isoformat(), **changes}
        reply = self.manager.handle(self.message("/cron create " + json.dumps(spec)))
        self.assertTrue(reply, spec)
        self.assertIn("revision", reply[0][1])
        return self.manager.store.list()[-1]

    def test_authorized_chat_create_run_and_delivery_survive_restart(self):
        schedule = self.create()
        self.assertEqual(schedule["misfire"], "skip")
        self.assertEqual(schedule["timezone"], "Asia/Dhaka")
        restarted = self.make_manager()
        self.assertTrue(restarted.tick())
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(self.executions[0]["user_id"], 7)
        self.assertEqual(restarted.store.runs()[0]["status"], "succeeded")
        self.assertEqual(restarted.store.deliveries()[0]["status"], "delivered")
        self.assertEqual(self.api.sent[0][0], 7)
        self.assertFalse(restarted.tick())
        self.assertEqual(len(self.executions), 1)

    def test_revoked_user_cannot_execute_or_receive(self):
        self.create()
        self.jobs.set_user_status(7, False)
        self.manager.tick()
        self.assertEqual(self.executions, [])
        self.assertEqual(self.api.sent, [])
        self.assertEqual(self.manager.store.runs()[0]["status"], "failed")
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "unknown")

    def test_cross_user_management_and_destination_override_are_rejected(self):
        schedule = self.create()
        for command in ("show", "pause", "resume", "delete"):
            reply = self.manager.handle(self.message("/cron " + command + " " + schedule["id"], user=8))
            self.assertIn("rejected", reply[0][1])
        self.assertEqual(self.manager.store.get(schedule["id"])["enabled"], 1)
        reply = self.manager.handle(self.message("/cron create " + json.dumps(
            {"name": "bad", "prompt": "do not run", "at": NOW.isoformat(),
             "delivery_target": {"chat_id": 99}})))
        self.assertIn("rejected", reply[0][1])
        self.assertEqual(len(self.manager.store.list()), 1)
        self.assertEqual(self.manager.handle(self.message("/cron list", user=99)), [])

    def test_replayed_update_does_not_create_or_edit_twice(self):
        event = self.message("/cron create " + json.dumps(
            {"name": "once", "prompt": "test", "at": NOW.isoformat()}))
        self.manager.handle(event)
        self.assertEqual(self.manager.handle(event), [])
        self.assertEqual(len(self.manager.store.list()), 1)

    def test_revision_edit_and_local_time_confirmation(self):
        schedule = self.create()
        response = self.manager.handle(self.message("/cron edit " + schedule["id"] +
                          " 1 " + json.dumps({"prompt": "Updated request"})))
        self.assertIn("revision 2", response[0][1])
        response = self.manager.handle(self.message("/cron edit " + schedule["id"] +
                          " 1 " + json.dumps({"prompt": "Stale request"})))
        self.assertIn("rejected", response[0][1])
        self.assertEqual(self.manager.store.get(schedule["id"])["prompt"], "Updated request")

    def test_unknown_transport_outcome_is_not_retried(self):
        self.create()
        self.api.failure = TelegramError("ambiguous network failure")
        self.manager.tick()
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "unknown")
        self.api.failure = None
        self.manager.tick()
        self.assertEqual(self.api.sent, [])
        self.assertEqual(len(self.executions), 1)

    def test_delivery_resume_does_not_reexecute_completed_job(self):
        self.create()
        self.manager.worker.tick()
        self.assertEqual(self.api.sent, [])
        self.make_manager().tick()
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(len(self.api.sent), 1)

    def test_foreign_account_project_and_scope_cannot_execute(self):
        for field, value in (("account", "456"), ("project", "/wrong"), ("scope", "wrong")):
            with self.subTest(field=field):
                manager = self.make_manager()
                target = manager.target(7)
                target[field] = value
                manager.store.create(name=field, prompt="never execute", project=self.root,
                    scope="telegram-shared", at=NOW, delivery_target=target)
                manager.tick()
        self.assertEqual(self.executions, [])
        self.assertEqual(self.api.sent, [])

    def test_idle_worker_preserves_foreground_priority(self):
        self.create()
        service = BotService(self.api, self.jobs, self.router, self.runner,
                             idle_work=self.manager.tick)
        self.jobs.consume(100, {"chat_id": 7, "user_id": 7, "prompt": "Foreground"})
        self.assertTrue(service.run_one())
        self.assertEqual(self.executions[0]["prompt"], "Foreground")
        self.assertEqual(self.manager.store.runs(), [])
        self.assertTrue(service.run_one())
        self.assertEqual(len(self.executions), 2)

    def test_shared_cli_management_is_nonexecuting(self):
        out, err = io.StringIO(), io.StringIO()
        result = main(["cron", "--project", str(self.root), "list"], stdout=out, stderr=err)
        self.assertEqual(result, 0, err.getvalue())
        self.assertEqual(json.loads(out.getvalue()), [])
        self.assertEqual(self.executions, [])

    def test_safe_rate_limit_retries_are_bounded_without_execution_retry(self):
        self.create()
        self.api.failure = TelegramError("rejected before acceptance", status=429)
        for attempt in range(3):
            self.manager.store.clock = lambda attempt=attempt: NOW + timedelta(seconds=61 * attempt)
            self.manager.tick()
        delivery = self.manager.store.deliveries()[0]
        self.assertEqual(delivery["status"], "failed")
        self.assertEqual(delivery["attempt"], 3)
        self.assertEqual(len(self.executions), 1)

    def test_partial_send_rate_limit_is_unknown_and_never_replayed(self):
        self.runner = lambda job: ("succeeded", "x" * 6000)
        self.manager = self.make_manager()
        self.create()
        def send(chat, text):
            if self.api.sent:
                raise TelegramError("second chunk rejected", status=429)
            self.api.sent.append((chat, text))
            return {"message_id": 1}
        self.api.send_message = send
        self.manager.tick()
        self.assertEqual(len(self.api.sent), 1)
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "unknown")
        self.manager.store.clock = lambda: NOW + timedelta(days=1)
        self.manager.tick()
        self.assertEqual(len(self.api.sent), 1)

    def test_revocation_between_chunks_blocks_remaining_delivery(self):
        self.runner = lambda job: ("succeeded", "x" * 6000)
        self.manager = self.make_manager()
        self.create()
        def send(chat, text):
            self.api.sent.append((chat, text))
            self.jobs.set_user_status(7, False)
            return {"message_id": 1}
        self.api.send_message = send
        self.manager.tick()
        self.assertEqual(len(self.api.sent), 1)
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "unknown")

    def test_bot_requires_explicit_enable_and_creates_no_cron_state_by_default(self):
        from senai.telegram.cli import telegram_main
        project = self.root / "disabled-project"
        project.mkdir()
        with patch("senai.telegram.cli.load_credentials", return_value=("unused-test-token", frozenset({7}))), \
             patch("senai.telegram.cli.identify_bot", return_value={"id": 123, "username": "test_bot"}), \
             patch("senai.telegram.cli.BotService.run_forever", return_value=0), \
             patch("senai.telegram.cli.BotService.skip_pending"):
            code = telegram_main(["--project", str(project)], io.StringIO(), io.StringIO())
        self.assertEqual(code, 0)
        self.assertFalse((project / "outputs/.senai-cron").exists())

    def test_native_runner_reuses_shared_session_and_installation_memory(self):
        from senai.telegram.runner import CommandRunner
        from senai.memory_runtime import InstallationRuntime
        sid = "11111111-1111-4111-8111-111111111111"
        installation = self.root / "installation"
        installation.mkdir()
        memory = InstallationRuntime(installation)
        memory.memory.remember("USER.md", "Prefers concise scheduled reports", user_requested=True)
        def seed(prompt, workspace, *, session_callback, **kwargs):
            session_callback(sid)
            return "seeded"
        memory.execute("seed", self.root / "outputs", executor=seed)
        self.jobs.bind_shared_session(sid)
        self.jobs.set_user_status(7, True)
        binary = self.root / "bin"
        binary.mkdir()
        executable = binary / "codex"
        executable.write_text("#!" + sys.executable + "\n" + """
import os, json, sys
from pathlib import Path
args = sys.argv[1:]
Path("cron-native-trace.json").write_text(json.dumps({
    "args": args, "prompt": sys.stdin.read(),
    "telegram_key_present": "TELEGRAM_BOT_TOKEN" in os.environ,
    "speech_key_present": "SENAI_TTS_API_KEY" in os.environ}))
Path("cron-artifact.txt").write_text("scheduled output")
Path(args[args.index("--output-last-message") + 1]).write_text("Scheduled done")
print(json.dumps({"type": "thread.started", "thread_id": "11111111-1111-4111-8111-111111111111"}))
""")
        executable.chmod(0o700)
        self.runner = CommandRunner(self.root, self.root / "outputs/telegram",
                                    store=self.jobs, skip_git_repo_check=True, chat_style=True)
        self.manager = self.make_manager()
        self.create()
        with patch.dict(os.environ, {"PATH": str(binary) + os.pathsep + os.environ["PATH"],
                         "SENAI_INSTALLATION_ROOT": str(installation),
                         "TELEGRAM_BOT_TOKEN": "unused-test-token", "SENAI_TTS_API_KEY": "unused-test-key"}):
            self.manager.tick()
        trace = json.loads((self.root / "outputs/cron-native-trace.json").read_text())
        self.assertEqual(trace["args"][-3:], ["resume", sid, "-"])
        self.assertIn("Prefers concise scheduled reports", trace["prompt"])
        self.assertFalse(trace["telegram_key_present"])
        self.assertFalse(trace["speech_key_present"])
        self.assertEqual(self.jobs.shared_session(), sid)
        self.assertTrue(self.jobs.user_status(7))
        self.assertEqual(self.jobs.recent(7), [])
        self.assertEqual((self.root / "outputs/cron-artifact.txt").read_text(), "scheduled output")
        self.assertEqual(self.manager.store.runs()[0]["status"], "succeeded")
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "delivered")

    def test_local_cli_can_inspect_chat_account_store_without_executing(self):
        self.create()
        out, err = io.StringIO(), io.StringIO()
        code = main(["cron", "--project", str(self.root), "--telegram-account", "123", "list"],
                    stdout=out, stderr=err)
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(json.loads(out.getvalue())[0]["name"], "reminder")
        self.assertEqual(self.executions, [])
