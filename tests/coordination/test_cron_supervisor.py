import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from datetime import timedelta

from tests.coordination import test_cron_runtime as fixtures
NOW = fixtures.NOW
from senai.cron_runtime import TelegramCron
from senai.cron_supervisor import Supervisor
from senai.processes import ExecutionUncertain
from senai.telegram.runner import CommandRunner
from senai.cron.worker import UncertainExecution


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.CronRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.manager = self.fixture.manager

    def test_delivery_continues_while_execution_is_blocked(self):
        self.fixture.create(name="completed")
        self.manager.worker.tick()
        entered, release = threading.Event(), threading.Event()
        def blocked(job):
            entered.set()
            release.wait(2)
            return "succeeded", "second result"
        self.manager.runner = blocked
        self.fixture.create(name="blocked")
        supervisor = Supervisor(self.manager, interval=0.01, status_interval=0.02)
        result = []
        thread = threading.Thread(target=lambda: result.append(supervisor.run(io.StringIO())))
        thread.start()
        try:
            self.assertTrue(entered.wait(1))
            deadline = time.monotonic() + 1
            while not self.fixture.api.sent and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertEqual(len(self.fixture.api.sent), 1)
            self.assertEqual(self.manager.store.deliveries()[0]["status"], "delivered")
            self.assertTrue(thread.is_alive())
        finally:
            supervisor.stop.set()
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result, [0])
        self.assertEqual(supervisor.status()["state"], "stopped")

    def test_restart_sends_pending_result_without_codex_and_paused_job_stays_idle(self):
        self.fixture.create()
        self.manager.worker.tick()
        self.fixture.create(name="paused")
        self.manager.store.pause(self.manager.store.list()[-1]["id"])
        manager = self.fixture.make_manager()
        before = len(self.fixture.executions)
        code = Supervisor(manager, interval=0.01).run(io.StringIO(), once=True)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.fixture.executions), before)
        self.assertEqual(manager.store.deliveries()[0]["status"], "delivered")

    def test_uncertain_execution_is_paused_and_not_retried(self):
        self.fixture.create(retries=3, every=1)
        def uncertain(job):
            raise ExecutionUncertain("deadline; effects unknown")
        self.manager.runner = uncertain
        self.manager.worker.tick()
        run = self.manager.store.runs()[0]
        self.assertEqual(run["status"], "unknown")
        self.assertEqual(self.manager.store.list()[0]["enabled"], 0)
        self.manager.store.clock = lambda: NOW + timedelta(days=1)
        self.assertIsNone(self.manager.worker.tick())
        self.assertEqual(len(self.manager.store.runs()), 1)

    def test_inflight_execution_and_send_are_not_reclaimed_after_restart(self):
        self.fixture.create()
        self.manager.store.claim()
        restarted = self.fixture.make_manager()
        self.assertIsNone(restarted.worker.tick())
        self.assertEqual(restarted.store.runs()[0]["status"], "running")
        self.assertEqual(self.fixture.executions, [])

    def test_timeout_stops_native_process_and_blocks_execution_retry(self):
        binary = self.root / "bin"
        binary.mkdir()
        code = "#!" + sys.executable + "\nimport time\ntime.sleep(20)\n"
        fake = binary / "codex"
        fake.write_text(code)
        fake.chmod(0o700)
        self.manager.runner = CommandRunner(self.root, self.root / "outputs/telegram",
            store=self.fixture.jobs, skip_git_repo_check=True, execution_timeout=0.15)
        self.fixture.create(retries=3)
        with patch.dict(os.environ, {"PATH": str(binary) + os.pathsep + os.environ["PATH"]}):
            started = time.monotonic()
            self.manager.worker.tick()
        self.assertLess(time.monotonic() - started, 7)
        self.assertEqual(self.manager.store.runs()[0]["status"], "unknown")
        self.assertEqual(self.manager.store.list()[0]["enabled"], 0)

    def test_supervisor_failure_is_visible_and_status_is_private(self):
        supervisor = Supervisor(self.manager, interval=0.01, status_interval=0.01)
        with patch.object(self.manager.worker, "tick", side_effect=RuntimeError("private-token")):
            code = supervisor.run(io.StringIO())
        self.assertEqual(code, 1)
        payload = json.loads(supervisor.status_path.read_text())
        self.assertEqual(payload["state"], "failed")
        self.assertNotIn("private-token", json.dumps(payload))
        self.assertEqual(supervisor.status_path.stat().st_mode & 0o777, 0o600)

    def test_worker_command_runs_disposable_pipeline_and_restart_does_not_rerun(self):
        from senai.cli import main
        from senai.telegram.store import JobStore
        from datetime import datetime, timezone
        sid = "11111111-1111-4111-8111-111111111111"
        state = self.root / "outputs/.senai-telegram/123"
        jobs = JobStore(state / "state.sqlite3")
        jobs.set_user_status(7, True)
        jobs.bind_shared_session(sid)
        self.fixture.create(at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat())
        binary = self.root / "bin"
        binary.mkdir()
        fake = binary / "codex"
        fake.write_text("#!" + sys.executable + "\n" + """
import json, sys
from pathlib import Path
args = sys.argv[1:]
sys.stdin.read()
with Path("execution-count.txt").open("a") as stream:
    stream.write("executed\\n")
Path(args[args.index("--output-last-message")+1]).write_text("Disposable scheduled result")
print(json.dumps({"type":"thread.started","thread_id":"11111111-1111-4111-8111-111111111111"}))
""")
        fake.chmod(0o700)
        arguments = ["cron", "worker", "--project", str(self.root), "--telegram-account", "123",
                     "--env-file", str(self.root/"unused-test.env"), "--once",
                     "--interval", "0.01", "--status-interval", "0.02",
                     "--execution-timeout", "2", "--skip-git-repo-check"]
        with patch("senai.telegram.config.load_credentials", return_value=("unused-token", frozenset({7}))), \
             patch("senai.telegram.api.BotAPI", return_value=self.fixture.api), \
             patch("senai.telegram.connection.identify_bot", return_value={"id":123,"username":"test_bot"}), \
             patch.dict(os.environ, {"PATH":str(binary)+os.pathsep+os.environ["PATH"],
                                      "SENAI_INSTALLATION_ROOT":""}):
            for _ in range(2):
                out, err = io.StringIO(), io.StringIO()
                self.assertEqual(main(arguments, stdout=out, stderr=err), 0, err.getvalue())
            status = io.StringIO()
            self.assertEqual(main(["cron","worker-status","--project",str(self.root),
                                   "--telegram-account","123"], stdout=status), 0)
        self.assertEqual((self.root/"outputs/execution-count.txt").read_text(), "executed\n")
        self.assertEqual(self.manager.store.runs()[0]["status"], "succeeded")
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "delivered")
        self.assertEqual(len(self.fixture.api.sent), 1)
        self.assertIn("Disposable scheduled result", self.fixture.api.sent[0][1])
        self.assertEqual(self.fixture.api.sent[0][0], 7)
        self.assertEqual(jobs.shared_session(), sid)
        self.assertTrue(jobs.user_status(7))
        self.assertEqual(jobs.offset(), 0)
        self.assertEqual(jobs.recent(7), [])
        self.assertEqual(json.loads(status.getvalue())["state"], "stopped")

    def test_unconfirmed_429_is_unknown_not_retryable(self):
        from senai.telegram.api import TelegramError
        self.fixture.create()
        self.fixture.api.failure = TelegramError("HTTP status without acceptance proof", status=429)
        self.manager.tick()
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "unknown")

    def test_inflight_send_is_not_reclaimed(self):
        self.fixture.create()
        self.manager.worker.tick()
        self.manager.store.claim_delivery()
        self.assertEqual(Supervisor(self.fixture.make_manager(), interval=0.01,
                                   status_interval=0.01).run(io.StringIO(), once=True), 0)
        self.assertEqual(self.manager.store.deliveries()[0]["status"], "delivering")
        self.assertEqual(self.fixture.api.sent, [])

    def test_standalone_worker_excludes_existing_bot_lock(self):
        from senai.cli import main
        from senai.telegram.store import JobStore
        from senai.telegram.service import instance_lock
        state = self.root / "outputs/.senai-telegram/123"
        JobStore(state / "state.sqlite3")
        with instance_lock(state/"bot.lock"), \
             patch("senai.telegram.config.load_credentials", return_value=("unused-token", frozenset({7}))), \
             patch("senai.telegram.api.BotAPI", return_value=self.fixture.api), \
             patch("senai.telegram.connection.identify_bot", return_value={"id":123,"username":"test_bot"}):
            err = io.StringIO()
            code = main(["cron","worker","--project",str(self.root),"--telegram-account","123",
                         "--env-file",str(self.root/"unused-test.env"),"--once"],
                        stdout=io.StringIO(),stderr=err)
        self.assertEqual(code, 2)
        self.assertIn("already running", err.getvalue())
        self.assertEqual(self.fixture.executions, [])

    def test_worker_command_sigterm_stops_and_records_status(self):
        # Test supervisor signals directly in a subprocess, without services or tokens.
        script = """
import io
from pathlib import Path
from senai.cron_supervisor import Supervisor
from tests.coordination import test_cron_runtime as fixtures
fixture = fixtures.CronRuntimeTests()
fixture.setUp()
manager = fixture.manager
manager.store.path = Path(manager.store.path)
Path(__import__('sys').argv[1]).write_text(str(manager.store.path.parent / 'worker-status.json'))
try:
    Supervisor(manager, interval=0.01, status_interval=0.01).run(io.StringIO(), signals=True)
finally:
    fixture.doCleanups()
"""
        marker = self.root/"signal-marker"
        child = subprocess.Popen([sys.executable,"-c",script,str(marker)],
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline = time.monotonic()+3
            while not marker.exists() and time.monotonic()<deadline:
                time.sleep(0.01)
            self.assertTrue(marker.exists())
            path = Path(marker.read_text())
            while (not path.exists()) and time.monotonic()<deadline:
                time.sleep(0.01)
            self.assertTrue(path.exists())
            child.terminate()
            out,err = child.communicate(timeout=3)
            self.assertEqual(child.returncode,0,err)
        finally:
            if child.poll() is None:
                child.kill()
                child.communicate()

    def test_transport_certainty_requires_valid_rejection_response(self):
        from unittest.mock import MagicMock
        from urllib.error import HTTPError
        from senai.telegram.api import BotAPI, TelegramError
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":false,"error_code":429}'
        with self.assertRaises(TelegramError) as known:
            BotAPI("unused-token", opener=lambda *a, **k: response).send_message(7, "test")
        self.assertTrue(known.exception.not_accepted)
        def malformed(*args, **kwargs):
            raise HTTPError("https://example.invalid",429,"test",{},io.BytesIO(b"not-json"))
        with self.assertRaises(TelegramError) as ambiguous:
            BotAPI("unused-token", opener=malformed).send_message(7, "test")
        self.assertEqual(ambiguous.exception.status,429)
        self.assertFalse(ambiguous.exception.not_accepted)

    def test_status_failure_still_stops_threads(self):
        supervisor = Supervisor(self.manager, interval=0.01, status_interval=0.01)
        def cleanup():
            supervisor.stop.set()
            for thread in supervisor.threads:
                if thread.ident is not None:
                    thread.join(2)
        self.addCleanup(cleanup)
        with patch.object(supervisor, "publish", side_effect=OSError("fixture storage error")):
            code = supervisor.run(io.StringIO())
        self.assertEqual(code,1)
        self.assertTrue(all(not thread.is_alive() for thread in supervisor.threads))
