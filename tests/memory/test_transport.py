"""Memory-to-real-adapter transport; fake executable, no live model or credentials."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from senai.codex import run_codex
from senai.options import CodexOptions
from senai.workspace import prepare_workspace
from senai.memory import MemoryStore, Namespace, ProfileStore, start_session, execute_session


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.workspace = prepare_workspace(self.project)
        self.namespace = Namespace(self.project, "team")
        self.store = MemoryStore(self.workspace / "memory.db")
        self.profiles = ProfileStore(self.workspace / "profiles", self.namespace, user_id="alice")
        binaries = self.project / "bin"
        binaries.mkdir()
        fake = binaries / "codex"
        fake.write_text("#!" + sys.executable + "\n" + """
import json
import os
from pathlib import Path
import sys
args = sys.argv[1:]
prompt = sys.stdin.read()
Path("transport.json").write_text(json.dumps({
    "prompt": prompt, "args": args, "cwd": str(Path.cwd())}))
if os.environ.get("SENAI_MEMORY_TEST_FAIL") == "1":
    print("offline fixture failure", file=sys.stderr)
    raise SystemExit(23)
Path(args[args.index("--output-last-message") + 1]).write_text(
    "Memory: Invoices deploy on Fridays")
""")
        fake.chmod(0o700)
        self.patch = patch.dict(os.environ, {
            "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
            "SENAI_MEMORY_TEST_FAIL": "0"})
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def save(self, name, text):
        self.profiles.apply(self.profiles.propose(name, text), approved=True)

    def trace(self):
        return json.loads((self.workspace / "transport.json").read_text())

    def test_curated_and_sqlite_facts_reach_real_child_without_resume(self):
        self.save("SOUL.md", "Be clear")
        self.save("USER.md", "Prefers Python")
        self.save("MEMORY.md", "Invoices use PostgreSQL")
        self.store.add(self.namespace, "Invoices use UTC", provenance="user")
        # Reopen both sources, independent of native chat history.
        profiles = ProfileStore(self.workspace / "profiles", self.namespace, user_id="alice")
        store = MemoryStore(self.workspace / "memory.db")
        snapshot = start_session(profiles, store, "Build invoices", include_user=True)
        response = execute_session(
            "Build invoices; $literal", self.workspace, snapshot=snapshot,
            executor=run_codex, options=CodexOptions(model="offline-model",
                skip_git_repo_check=True, output_last_message="saved.txt"))
        trace = self.trace()
        for value in ("Be clear", "Prefers Python", "Invoices use PostgreSQL",
                      "Invoices use UTC", "Build invoices; $literal"):
            self.assertIn(value, trace["prompt"])
        self.assertEqual(trace["cwd"], str(self.workspace))
        self.assertNotIn("resume", trace["args"])
        self.assertIn("offline-model", trace["args"])
        self.assertEqual((self.workspace / "saved.txt").read_text(), response)
        # Even a marked result is not implicitly retained.
        self.assertEqual(len(store.list(self.namespace)), 1)
        self.assertEqual(profiles.read("MEMORY.md").text, "Invoices use PostgreSQL")

    def test_shared_resumed_transport_preserves_snapshot_and_exact_id(self):
        self.save("USER.md", "Private preference")
        self.save("MEMORY.md", "Invoices use PostgreSQL")
        snapshot = start_session(self.profiles, self.store, "invoices")
        self.save("MEMORY.md", "Invoices use SQLite")
        session_id = "6e327d14-c721-491c-9fa2-f04fc1f8cf22"
        execute_session("Build invoices", self.workspace, snapshot=snapshot,
                        executor=run_codex, options=CodexOptions(resume=session_id))
        trace = self.trace()
        self.assertIn("PostgreSQL", trace["prompt"])
        self.assertNotIn("Invoices use SQLite", trace["prompt"])
        self.assertNotIn("Private preference", trace["prompt"])
        self.assertEqual(trace["args"][-3:], ["resume", session_id, "-"])
        self.assertNotIn("--last", trace["args"])

    def test_child_failure_propagates_without_retention(self):
        self.save("MEMORY.md", "Invoices use PostgreSQL")
        snapshot = start_session(self.profiles, self.store, "invoices")
        with patch.dict(os.environ, {"SENAI_MEMORY_TEST_FAIL": "1"}):
            with self.assertRaisesRegex(RuntimeError, "code 23"):
                execute_session("Build invoices", self.workspace, snapshot=snapshot,
                                executor=run_codex)
        self.assertEqual(self.store.list(self.namespace), [])
        self.assertEqual(self.profiles.read("MEMORY.md").text, "Invoices use PostgreSQL")
        self.assertFalse(list(self.workspace.glob(".senai-*")))
