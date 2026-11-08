import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from senai.memory import InstallationMemory, execute_session


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.memory = InstallationMemory(self.repo)

    def test_global_files_and_restart_across_projects(self):
        self.memory.remember("USER.md", "Prefers Python", user_requested=True)
        self.memory.remember("MEMORY.md", "Completed the first release", user_requested=True)
        self.assertEqual(self.memory.profiles.read("USER.md").path,
                         self.repo / "outputs/.senai-memory/USER.md")
        self.assertEqual(self.memory.profiles.read("MEMORY.md").path,
                         self.repo / "outputs/.senai-memory/MEMORY.md")
        self.memory.store.add(self.memory.namespace, "Release artifacts stay local", provenance="user")
        reopened = InstallationMemory(self.repo)
        for project in ("project-a", "project-b"):
            workspace = self.repo / project
            workspace.mkdir()
            snapshot = reopened.snapshot("release")
            prompts = []
            execute_session("Work here", workspace, snapshot=snapshot,
                            executor=lambda prompt, workspace: prompts.append(prompt))
            self.assertIn("Prefers Python", prompts[0])
            self.assertIn("Completed the first release", prompts[0])
            self.assertIn("Release artifacts stay local", prompts[0])
        other = self.repo / "other-installation"
        other.mkdir()
        self.assertEqual(InstallationMemory(other).snapshot("release").context, "")

    def test_requested_or_verified_noteworthy_learning_only(self):
        with self.assertRaises(ValueError):
            self.memory.remember("MEMORY.md", "Ordinary output")
        with self.assertRaises(ValueError):
            self.memory.remember("MEMORY.md", "Claimed event", noteworthy=True)
        for flag in ("user_requested", "noteworthy", "verified"):
            with self.assertRaises(ValueError):
                self.memory.remember("MEMORY.md", "Fact", **{flag: "yes"})
        self.memory.remember("MEMORY.md", "User chose a local-only design",
                             noteworthy=True, verified=True)
        self.assertIn("local-only", self.memory.snapshot("design").context)
        self.memory.remember("USER.md", "Dislikes noisy output", noteworthy=True, verified=True)
        self.assertIn("Dislikes noisy output", self.memory.snapshot("design").context)

    def test_learning_appends_deduplicates_and_cannot_edit_soul(self):
        self.memory.remember("MEMORY.md", "First event", user_requested=True)
        self.memory.remember("MEMORY.md", "Second event", noteworthy=True, verified=True)
        self.memory.remember("MEMORY.md", "First event", user_requested=True)
        text = self.memory.profiles.read("MEMORY.md").text
        self.assertEqual(text.count("First event"), 1)
        self.assertIn("Second event", text)
        with self.assertRaises(ValueError):
            self.memory.remember("SOUL.md", "Change identity", user_requested=True)
        self.assertEqual(self.memory.profiles.read("SOUL.md").text, "")

    def test_validation_capacity_and_snapshot_freezing(self):
        self.memory.remember("USER.md", "Prefers Python", user_requested=True)
        snapshot = self.memory.snapshot("hello")
        for text in ("api_key=example", "x" * 4000):
            with self.assertRaises(ValueError):
                self.memory.remember("USER.md", text, user_requested=True)
        self.memory.remember("USER.md", "Likes concise answers", user_requested=True)
        self.assertNotIn("Likes concise answers", snapshot.context)
        self.assertIn("Likes concise answers", self.memory.snapshot("hello").context)
        self.assertEqual(self.memory.store.list(self.memory.namespace), [])

    def test_global_cli_without_user_or_project_selection(self):
        base = [sys.executable, "-m", "senai.memory", "--installation", str(self.repo)]
        result = subprocess.run(base + ["remember", "USER.md", "Prefers Python",
                                       "--user-requested"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = subprocess.check_output(base + ["session-context", "hello"], text=True)
        self.assertIn("Prefers Python", text)
        proposal = subprocess.check_output(
            base + ["profile-propose", "SOUL.md", "Be clear"], text=True)
        file = self.repo / "proposal.json"
        file.write_text(proposal)
        subprocess.run(base + ["profile-apply", str(file), "--approve"],
                       check=True, capture_output=True)
        self.assertIn("Be clear", subprocess.check_output(
            base + ["session-context", "hello"], text=True))
        failure = subprocess.run(base + ["remember", "MEMORY.md", "Ordinary output"],
                                 text=True, capture_output=True)
        self.assertNotEqual(failure.returncode, 0)
        forbidden = subprocess.run(base + ["--scope", "private", "list"],
                                   text=True, capture_output=True)
        self.assertNotEqual(forbidden.returncode, 0)

    def test_legacy_project_data_not_silently_imported(self):
        legacy = self.repo / "outputs/.senai-memory/profiles"
        legacy.mkdir(parents=True)
        (legacy / "MEMORY.md").write_text("Unselected legacy content")
        self.assertNotIn("Unselected legacy content", self.memory.snapshot("legacy").context)
