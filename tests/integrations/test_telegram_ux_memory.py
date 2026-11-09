import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai.defaults import save_defaults
from senai.memory import InstallationMemory
from senai.telegram.runner import CommandRunner
from senai.telegram.store import JobStore
from senai.telegram.router import Router
from senai.telegram.conversation import create_conversation_router
from senai.telegram.session_policy import SessionGate

SID = "11111111-1111-4111-8111-111111111111"
NEW = "22222222-2222-4222-8222-222222222222"


class TelegramMemoryContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        self.installation = self.root / "installation"
        self.other = self.root / "other-installation"
        for path in (self.project, self.installation, self.other):
            path.mkdir()
        self.config = self.root / "defaults.json"
        self.defaults = {"project": str(self.project), "installation": str(self.installation),
                         "timezone": "Asia/Dhaka", "skip_git_repo_check": True}
        save_defaults(self.defaults, environ={"SENAI_CONFIG": str(self.config)})
        binary = self.root / "bin"
        binary.mkdir()
        executable = binary / "codex"
        executable.write_text("""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
Path('ux-trace.json').write_text(json.dumps({'prompt': sys.stdin.read(), 'args': args}))
Path(args[args.index('--output-last-message') + 1]).write_text('Done.')
print(json.dumps({'type': 'thread.started', 'thread_id': os.environ['FIXTURE_SID']}))
""")
        executable.chmod(0o700)
        self.env = {"PATH": str(binary) + os.pathsep + os.environ["PATH"],
                    "SENAI_CONFIG": str(self.config), "FIXTURE_SID": SID}
        self.store = JobStore(self.project / "outputs/state/state.sqlite3")

    def trace(self):
        return json.loads((self.project / "outputs/ux-trace.json").read_text())

    def test_child_defaults_enable_same_installation_and_fresh_session_sees_updated_profile(self):
        memory = InstallationMemory(self.installation)
        memory.remember("USER.md", "Prefers cobalt", user_requested=True)
        runner = CommandRunner(self.project, self.store.path.parent, store=self.store, skip_git_repo_check=True)
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(runner({"id": 1, "prompt": "What is my preference?"}), ("succeeded", "Done."))
        self.assertIn("Prefers cobalt", self.trace()["prompt"])
        memory.remember("USER.md", "Likes chamomile", user_requested=True)
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(runner({"id": 2, "prompt": "Continue"}), ("succeeded", "Done."))
        self.assertNotIn("Likes chamomile", self.trace()["prompt"])
        self.assertIn(SID, self.trace()["args"])
        gate = SessionGate()
        router = create_conversation_router(Router(self.store, {7}, "test_bot"), project=self.project,
                 account="123", new_session_users={7}, session_guard=gate.idle)
        def update(identifier, text):
            return {"update_id": identifier, "message": {"from": {"id": 7}, "chat": {"id": 7, "type": "private"}, "text": text}}
        router.handle(update(10, "/new"))
        router.handle(update(11, "Confirm"))
        with patch.dict(os.environ, {**self.env, "FIXTURE_SID": NEW}, clear=True):
            self.assertEqual(runner({"id": 3, "prompt": "What are my preferences?"}), ("succeeded", "Done."))
        self.assertIn("Likes chamomile", self.trace()["prompt"])
        self.assertEqual(self.store.shared_session(), NEW)
        self.assertEqual(self.store.session_history()[0]["session_id"], SID)
        self.assertFalse((self.project / "outputs/.senai-memory").exists())

    def test_explicit_startup_installation_is_pinned_if_saved_defaults_later_change(self):
        InstallationMemory(self.installation).remember("USER.md", "Pinned owner profile", user_requested=True)
        InstallationMemory(self.other).remember("USER.md", "Wrong owner profile", user_requested=True)
        runner = CommandRunner(self.project, self.store.path.parent, store=self.store,
                               skip_git_repo_check=True, installation=self.installation)
        changed = {**self.defaults, "installation": str(self.other)}
        save_defaults(changed, environ={"SENAI_CONFIG": str(self.config)})
        with patch.dict(os.environ, {**self.env, "SENAI_INSTALLATION_ROOT": str(self.other)}, clear=True):
            self.assertEqual(runner({"id": 1, "prompt": "Who am I?"}), ("succeeded", "Done."))
        self.assertIn("Pinned owner profile", self.trace()["prompt"])
        self.assertNotIn("Wrong owner profile", self.trace()["prompt"])


    def test_explicit_absent_memory_context_does_not_pick_later_defaults(self):
        InstallationMemory(self.installation).remember("USER.md", "Must stay absent", user_requested=True)
        runner = CommandRunner(self.project, self.store.path.parent, store=self.store,
                               skip_git_repo_check=True, installation="")
        with patch.dict(os.environ, self.env, clear=True):
            self.assertEqual(runner({"id": 1, "prompt": "Hello"}), ("succeeded", "Done."))
        self.assertNotIn("Must stay absent", self.trace()["prompt"])
