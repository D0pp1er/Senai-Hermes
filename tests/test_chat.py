"""Persistent chat must reuse the ordinary Senai execution pipeline."""
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai import cli
from senai.defaults import save_defaults
from senai.memory import setup_profiles

FIRST = "11111111-1111-4111-8111-111111111111"
SECOND = "22222222-2222-4222-8222-222222222222"


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.installation = self.root / "installation"
        self.installation.mkdir()
        setup_profiles(self.installation)
        env = patch.dict(os.environ, {"SENAI_CONFIG": str(self.root / "defaults.json"),
                                    "SENAI_INSTALLATION_ROOT": ""})
        env.start()
        self.addCleanup(env.stop)
        save_defaults({"project": str(self.project), "installation": str(self.installation),
                       "skip_git_repo_check": True})
        self.calls = []

    def executor(self, prompt, workspace, *, options, session_callback, **kwargs):
        self.calls.append((prompt, workspace, options))
        session_callback(options.resume or (FIRST if len(self.calls) == 1 else SECOND))
        return "reply " + str(len(self.calls))

    def chat(self, text="", args=()):
        out, err = io.StringIO(), io.StringIO()
        code = cli.main(["chat", *args], out, err, io.StringIO(text))
        return code, out.getvalue(), err.getvalue()

    def test_turns_use_memory_pipeline_and_exact_native_resume(self):
        cli.main(["user", "add", "Favorite color is cobalt blue"], io.StringIO(), io.StringIO())
        with patch("senai.cli.run_codex", side_effect=self.executor), patch("senai.native.run_native") as native:
            code, out, err = self.chat("Hello\nFollow up\n/exit\n")
        self.assertEqual(code, 0, err)
        self.assertFalse(native.called)
        self.assertIn("cobalt blue", self.calls[0][0])
        self.assertIn("Installation profiles are managed", self.calls[0][0])
        self.assertEqual(self.calls[0][1], self.project / "outputs")
        self.assertTrue(self.calls[0][2].skip_git_repo_check)
        self.assertIsNone(self.calls[0][2].resume)
        self.assertEqual(self.calls[1][2].resume, FIRST)
        self.assertIn("reply 1", out)
        self.assertIn("reply 2", out)

    def test_reopen_resumes_and_history_survives_new_sessions(self):
        with patch("senai.cli.run_codex", side_effect=self.executor):
            self.assertEqual(self.chat("original message\n")[0], 0)
            self.assertEqual(self.chat("another message\n")[0], 0)
            self.assertEqual(self.calls[-1][2].resume, FIRST)
            self.assertEqual(self.chat("fresh message\n", ["--new"])[0], 0)
            self.assertIsNone(self.calls[-1][2].resume)
        code, out, err = self.chat("/history all\n/sessions\n/exit\n")
        self.assertEqual(code, 0, err)
        self.assertIn("original message", out)
        self.assertIn("another message", out)
        self.assertIn("fresh message", out)
        self.assertIn(FIRST, out)
        self.assertIn(SECOND, out)

    def test_frozen_resume_and_new_profile_loading(self):
        with patch("senai.cli.run_codex", side_effect=self.executor):
            self.chat("seed\n")
            cli.main(["user", "add", "Prefers numbered examples"], io.StringIO(), io.StringIO())
            self.chat("follow up\n")
            self.assertNotIn("Prefers numbered examples", self.calls[-1][0])
            self.chat("fresh\n", ["--new"])
            self.assertIn("Prefers numbered examples", self.calls[-1][0])

    def test_explicit_user_memory_is_saved_via_success_learning(self):
        with patch("senai.cli.run_codex", side_effect=self.executor):
            code, _, err = self.chat("Remember my preference: Likes concise answers\n")
        self.assertEqual(code, 0, err)
        self.assertIn("Likes concise answers", (self.installation / "outputs/.senai-memory/USER.md").read_text())

    def test_selected_registry_context_and_outcome_are_preserved(self):
        from senai.skills import Registry
        package = self.root / "package"
        package.mkdir()
        (package / "SKILL.md").write_text("---\nname: chat-check\ndescription: Verify chat artifacts\nversion: '1.0'\n---\nPreserve identifier strings.\n")
        registry = Registry(self.project / "outputs/skills")
        registry.import_local(package)
        cli.main(["skill", "use", "chat-check"], io.StringIO(), io.StringIO())
        with patch("senai.cli.run_codex", side_effect=self.executor):
            code, _, err = self.chat("Implement example\n")
        self.assertEqual(code, 0, err)
        self.assertIn("SKILL_CONTEXT_JSON", self.calls[0][0])
        self.assertEqual(registry.outcomes("chat-check")[0].status, "unverified")

    def test_unknown_turn_is_retained_and_not_automatically_repeated(self):
        def fail(prompt, workspace, *, session_callback, **kwargs):
            session_callback(FIRST)
            raise RuntimeError("Transport ended after launch")
        with patch("senai.cli.run_codex", side_effect=fail):
            self.assertEqual(self.chat("possibly executed\n")[0], 2)
        with patch("senai.cli.run_codex") as run:
            code, out, err = self.chat("do not silently repeat\n")
            self.assertFalse(run.called)
            self.assertEqual(code, 2)
        _, history, _ = self.chat(args=["--history"])
        self.assertIn("possibly executed", history)
        self.assertIn("unknown", history)

    def test_read_only_history_does_not_call_model_or_create_session(self):
        with patch("senai.cli.run_codex") as run:
            self.assertEqual(self.chat(args=["--history"])[0], 0)
            self.assertEqual(self.chat(args=["--sessions"])[0], 0)
            self.assertFalse(run.called)

    def test_installed_context_cannot_silently_change_existing_chat_owner(self):
        with patch("senai.cli.run_codex", side_effect=self.executor):
            self.chat("owner one\n")
            other = self.root / "other"
            other.mkdir()
            setup_profiles(other)
            self.chat("owner two\n", ["--installation", str(other)])
        self.assertIsNone(self.calls[-1][2].resume)
        _, out, _ = self.chat(args=["--history"])
        self.assertNotIn("owner two", out)

    def test_json_ephemeral_and_arbitrary_native_resume_are_rejected(self):
        with patch("senai.cli.run_codex") as run:
            for args in (["--json"], ["--ephemeral"], ["--last"], ["--resume", FIRST]):
                self.assertEqual(self.chat("hello\n", args)[0], 2)
            self.assertFalse(run.called)

    def test_history_directory_and_database_are_private(self):
        self.chat(args=["--history"])
        directory = self.project / "outputs/.senai-chat"
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((directory / "history.sqlite3").stat().st_mode & 0o777, 0o600)

    def test_unsafe_history_symlink_is_rejected(self):
        workspace = self.project / "outputs"
        workspace.mkdir()
        (workspace / ".senai-chat").symlink_to(self.root, target_is_directory=True)
        code, _, err = self.chat(args=["--history"])
        self.assertEqual(code, 2)
        self.assertIn("symlink", err.lower())

    def test_interrupted_pending_turn_recovers_as_unknown_not_retryable(self):
        from senai.chat_store import ChatStore
        workspace = self.project / "outputs"
        workspace.mkdir()
        store = ChatStore(workspace)
        owner = str(self.installation)
        session = store.select(owner)
        store.begin(session['id'], "unfinished request")
        with store.exclusive():
            self.assertEqual(store.history(owner)[0]['status'], "unknown")
            with self.assertRaisesRegex(ValueError, "unknown"):
                store.begin(session['id'], "unsafe repeat")

    def test_singleton_lock_does_not_recover_another_live_turn(self):
        from senai.chat_store import ChatStore
        workspace = self.project / "outputs"
        workspace.mkdir()
        first, second = ChatStore(workspace), ChatStore(workspace)
        owner = str(self.installation)
        with first.exclusive():
            session = first.select(owner)
            first.begin(session['id'], "live request")
            with self.assertRaisesRegex(ValueError, "Another Senai chat"):
                with second.exclusive():
                    self.fail("Second chat acquired lock")
            self.assertEqual(first.history(owner)[0]['status'], "pending")

    def test_native_id_mismatch_and_history_database_symlink_are_rejected(self):
        from senai.chat_store import ChatStore
        workspace = self.project / "outputs"
        workspace.mkdir()
        store = ChatStore(workspace)
        session = store.select(str(self.installation))
        store.bind(session['id'], str(self.installation), FIRST)
        with self.assertRaisesRegex(ValueError, "mapping preserved"):
            store.bind(session['id'], str(self.installation), SECOND)
        self.assertEqual(store.session(session['id'], str(self.installation))['native_id'], FIRST)
        store.path.unlink()
        store.path.symlink_to(self.root / "outside.sqlite3")
        with self.assertRaisesRegex(ValueError, "symlink"):
            ChatStore(workspace)
        self.assertFalse((self.root / "outside.sqlite3").exists())

    def test_resume_archived_local_chat_and_project_isolation(self):
        from senai.chat_store import ChatStore
        with patch("senai.cli.run_codex", side_effect=self.executor):
            self.chat("original\n")
            store = ChatStore(self.project / "outputs")
            old = store.sessions(str(self.installation))[0]['id']
            self.chat("fresh\n", ["--new"])
            self.chat("/resume " + old + "\ncontinue original\n")
            self.assertEqual(self.calls[-1][2].resume, FIRST)
        other = self.root / "project-b"
        other.mkdir()
        _, out, _ = self.chat(args=["--project", str(other), "--history"])
        self.assertNotIn("original", out)

    def test_real_offline_codex_child_persists_session_and_frozen_context(self):
        import json
        import sys
        binary = self.root / "bin"
        binary.mkdir()
        fake = binary / "codex"
        fake.write_text("#!" + sys.executable + "\n" + """
import json,sys
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.read()
with Path('chat-trace.jsonl').open('a') as stream:
    stream.write(json.dumps({'args':args,'prompt':prompt}) + chr(10))
sid = args[args.index('resume')+1] if 'resume' in args else '11111111-1111-4111-8111-111111111111'
Path(args[args.index('--output-last-message')+1]).write_text('Offline child reply')
print(json.dumps({'type':'thread.started','thread_id':sid}))
""")
        fake.chmod(0o700)
        cli.main(["user", "add", "Initial profile marker"], io.StringIO(), io.StringIO())
        with patch.dict(os.environ, {"PATH": str(binary) + os.pathsep + os.environ['PATH']}):
            code, out, err = self.chat("first actual child turn\n")
            self.assertEqual(code, 0, err)
            self.assertIn("Offline child reply", out)
            cli.main(["user", "add", "Later profile marker"], io.StringIO(), io.StringIO())
            code, _, err = self.chat("second actual child turn\n")
            self.assertEqual(code, 0, err)
        traces = [json.loads(line) for line in (self.project / "outputs/chat-trace.jsonl").read_text().splitlines()]
        self.assertEqual(len(traces), 2)
        self.assertIn("Initial profile marker", traces[0]['prompt'])
        self.assertIn("resume", traces[1]['args'])
        self.assertIn(FIRST, traces[1]['args'])
        self.assertNotIn("Later profile marker", traces[1]['prompt'])
        _, history, _ = self.chat(args=["--history"])
        self.assertIn("Offline child reply", history)
