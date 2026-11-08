import io
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from senai.cli import main
from senai.options import CodexOptions
from senai.memory import InstallationMemory
from senai.memory_runtime import InstallationRuntime, LearningDecision

SID = "11111111-1111-4111-8111-111111111111"
SID2 = "22222222-2222-4222-8222-222222222222"


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.installation = self.root / "installation"
        self.installation.mkdir()
        self.a = self.root / "project-a"
        self.b = self.root / "project-b"
        self.a.mkdir()
        self.b.mkdir()

    def executor(self, sid, prompts):
        def run(prompt, workspace, *, session_callback, **kwargs):
            prompts.append(prompt)
            session_callback(sid)
            return "done"
        return run

    def test_explicit_learning_cross_project_and_frozen_resume(self):
        runtime = InstallationRuntime(self.installation)
        prompts = []
        runtime.execute("Remember in USER.md: Prefers cobalt blue", self.a,
                        executor=self.executor(SID, prompts))
        self.assertNotIn("Prefers cobalt blue", prompts[0].split("<user_request>")[0])
        # A new process and a different project share installation memory.
        reopened = InstallationRuntime(self.installation)
        reopened.execute("What color do I prefer?", self.b,
                         executor=self.executor(SID2, prompts))
        self.assertIn("Prefers cobalt blue", prompts[-1])
        reopened.execute("What color?", self.a, options=CodexOptions(resume=SID),
                         executor=self.executor(SID, prompts))
        self.assertNotIn("Prefers cobalt blue", prompts[-1])
        self.assertIn("Prefers cobalt blue", reopened.memory.snapshot("color").context)
        (self.root / "other").mkdir()
        other = InstallationRuntime(self.root / "other")
        self.assertNotIn("cobalt", other.memory.snapshot("color").context)

    def test_unknown_resume_and_last_do_not_execute(self):
        runtime = InstallationRuntime(self.installation)
        for options in (CodexOptions(resume=SID), CodexOptions(last=True)):
            with self.subTest(options=options), self.assertRaises(ValueError):
                runtime.execute("hello", self.a, options=options,
                                executor=lambda *a, **k: self.fail("must not execute"))

    def test_learning_requires_success_and_trusted_verified_decision(self):
        runtime = InstallationRuntime(self.installation)
        prompts = []
        runtime.execute("hello", self.a, executor=self.executor(SID, prompts),
                        learning=lambda *args: [LearningDecision("MEMORY.md", "Release passed checks",
                                                               noteworthy=True, verified=True)])
        self.assertIn("Release passed checks", runtime.memory.snapshot("release").context)
        with self.assertRaises(ValueError):
            runtime.execute("hello", self.a, executor=self.executor(SID2, prompts),
                            learning=lambda *args: [LearningDecision("MEMORY.md", "Unverified",
                                                                   noteworthy=True)])
        def failed(*args, **kwargs):
            raise RuntimeError("failed")
        with self.assertRaises(RuntimeError):
            runtime.execute("Remember in USER.md: Never saved", self.a, executor=failed)
        context = runtime.memory.snapshot("hello").context
        self.assertNotIn("Never saved", context)
        self.assertNotIn("Unverified", context)
        self.assertEqual(runtime.memory.profiles.read("SOUL.md").text, "")

    def test_ordinary_output_is_not_learning_and_soul_is_protected(self):
        runtime = InstallationRuntime(self.installation)
        runtime.execute("hello", self.a, executor=self.executor(SID, []))
        self.assertEqual(runtime.memory.snapshot("hello").context, "")
        with self.assertRaises(ValueError):
            runtime.execute("hello", self.a, executor=self.executor(SID2, []),
                            learning=lambda *args: [LearningDecision("SOUL.md", "new identity",
                                                                   user_requested=True)])

    def test_cli_explicit_installation_and_json_transport(self):
        prompts = []
        with patch("senai.cli.run_codex", side_effect=self.executor(SID, prompts)):
            code = main(["--installation", str(self.installation), "--project", str(self.a),
                         "--json", "Remember that the release color is cobalt"],
                        stdout=io.StringIO(), stderr=io.StringIO())
        self.assertEqual(code, 0)
        self.assertIn("release color is cobalt",
                      InstallationMemory(self.installation).snapshot("color").context)
        self.assertTrue(list((self.installation / "outputs/.senai-memory").glob("*.sqlite3")))

    def test_environment_root_is_stable_and_missing_root_has_no_memory(self):
        with patch.dict("os.environ", {"SENAI_INSTALLATION_ROOT": str(self.installation)}),              patch("senai.cli.run_codex", side_effect=self.executor(SID, [])):
            self.assertEqual(main(["--project", str(self.b), "Remember that tests use cobalt"],
                                  stdout=io.StringIO(), stderr=io.StringIO()), 0)
        self.assertIn("tests use cobalt", InstallationMemory(self.installation).snapshot("tests").context)

    def test_telegram_enriched_explicit_request_is_learned(self):
        from senai.telegram.chat import chat_request
        runtime = InstallationRuntime(self.installation)
        runtime.execute(chat_request("Remember in USER.md: Prefers short replies"),
                        self.a, executor=self.executor(SID, []))
        self.assertIn("Prefers short replies", runtime.memory.snapshot("hello").context)

    def transport_fixture(self):
        binary = self.root / "bin"
        binary.mkdir()
        executable = binary / "codex"
        executable.write_text("#!" + sys.executable + "\n" + """
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.read()
Path("trace.json").write_text(json.dumps({"prompt": prompt, "args": args}))
print(json.dumps({"type": "thread.started", "thread_id": os.environ["FIXTURE_SID"]}))
if os.environ.get("FIXTURE_FAIL"):
    print("fixture execution failed", file=sys.stderr)
    raise SystemExit(23)
Path(args[args.index("--output-last-message") + 1]).write_text("Memory: Unverified model claim")
""")
        executable.chmod(0o700)
        env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                   FIXTURE_SID=SID)
        env.pop("SENAI_INSTALLATION_ROOT", None)
        return env

    def command(self, project, request, *options):
        return [sys.executable, "-m", "senai", "--installation", str(self.installation),
                "--project", str(project), "--skip-git-repo-check", *options, request]

    def test_real_cli_processes_cross_project_resume_and_json_stream(self):
        env = self.transport_fixture()
        first = subprocess.run(self.command(self.a, "Remember in USER.md: Prefers cobalt",
                                             "--json"), env=env, text=True, capture_output=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["thread_id"], SID)
        env["FIXTURE_SID"] = SID2
        fresh = subprocess.run(self.command(self.b, "What is my preference?"),
                               env=env, text=True, capture_output=True)
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        trace = json.loads((self.b / "outputs/trace.json").read_text())
        self.assertIn("Prefers cobalt", trace["prompt"])
        self.assertNotIn("resume", trace["args"])
        env["FIXTURE_SID"] = SID
        resumed = subprocess.run(self.command(self.a, "What is my preference?", "--resume", SID),
                                 env=env, text=True, capture_output=True)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        trace = json.loads((self.a / "outputs/trace.json").read_text())
        self.assertNotIn("Prefers cobalt", trace["prompt"])
        self.assertEqual(trace["args"][-3:], ["resume", SID, "-"])
        self.assertNotIn("Unverified model claim",
                         InstallationMemory(self.installation).snapshot("hello").context)

    def test_real_transport_failure_does_not_learn(self):
        env = self.transport_fixture()
        env["FIXTURE_FAIL"] = "1"
        result = subprocess.run(self.command(self.a, "Remember that this must not persist"),
                                env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("fixture execution failed", result.stderr)
        self.assertEqual(InstallationMemory(self.installation).snapshot("hello").context, "")

    def test_missing_configuration_retains_original_executor_contract(self):
        with patch.dict("os.environ", {}, clear=True), \
             patch("senai.cli.run_codex", return_value="unchanged") as run:
            code = main(["--project", str(self.a), "hello"], stdout=io.StringIO(),
                        stderr=io.StringIO())
        self.assertEqual(code, 0)
        self.assertNotIn("session_callback", run.call_args.kwargs)
        self.assertFalse((self.a / "outputs/.senai-memory").exists())

    def test_explicit_soul_learning_is_rejected_before_execution(self):
        runtime = InstallationRuntime(self.installation)
        with self.assertRaises(ValueError):
            runtime.execute("Remember in SOUL.md: Be different", self.a,
                            executor=lambda *a, **k: self.fail("SOUL is human-controlled"))
        self.assertEqual(runtime.memory.profiles.read("SOUL.md").text, "")
