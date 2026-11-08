import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from senai.memory import MemoryStore, Namespace
from senai.memory.profiles import ProfileStore, ConflictError
from senai.memory.session import start_session, execute_session


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ns = Namespace(self.root / "project", "team")
        self.profiles = ProfileStore(self.root / "profiles", self.ns, user_id="alice")
        self.db = MemoryStore(self.root / "facts.db")

    def save(self, name, text, **kwargs):
        proposal = self.profiles.propose(name, text, **kwargs)
        return self.profiles.apply(proposal, approved=True)

    def test_missing_files_and_scoped_restart(self):
        self.assertEqual(self.profiles.read("MEMORY.md").text, "")
        self.save("MEMORY.md", "Invoices use PostgreSQL")
        reopened = ProfileStore(self.root / "profiles", self.ns, user_id="alice")
        self.assertEqual(reopened.read("MEMORY.md").text, "Invoices use PostgreSQL")
        other = ProfileStore(self.root / "profiles", Namespace(self.root / "other", "team"))
        self.assertEqual(other.read("MEMORY.md").text, "")
        private = ProfileStore(self.root / "profiles", Namespace(self.root / "project", "private"))
        self.assertEqual(private.read("MEMORY.md").text, "")

    def test_proposal_review_conflict_and_deletion(self):
        proposal = self.profiles.propose("MEMORY.md", "Uses tabs")
        self.assertEqual(self.profiles.read("MEMORY.md").text, "")
        self.assertIn("+Uses tabs", proposal.diff)
        with self.assertRaises(ValueError):
            self.profiles.apply(proposal, approved=False)
        self.profiles.apply(proposal, approved=True)
        with self.assertRaises(ConflictError):
            self.profiles.apply(proposal, approved=True)
        self.save("MEMORY.md", "")
        self.assertEqual(self.profiles.read("MEMORY.md").text, "")

    def test_user_files_require_explicit_identity_and_do_not_cross_users(self):
        self.save("USER.md", "Prefers concise responses")
        bob = ProfileStore(self.root / "profiles", self.ns, user_id="bob")
        self.assertEqual(bob.read("USER.md").text, "")
        self.assertEqual(bob.read("MEMORY.md").text, "")
        anonymous = ProfileStore(self.root / "profiles", self.ns)
        with self.assertRaises(ValueError):
            anonymous.read("USER.md")

    def test_soul_requires_human_authorship(self):
        with self.assertRaises(ValueError):
            self.profiles.propose("SOUL.md", "Be concise", origin="outcome")
        self.save("SOUL.md", "Be concise", origin="human")

    def test_invalid_names_secrets_and_oversized_files(self):
        for name in ("../USER.md", "nested/MEMORY.md", "other.md"):
            with self.assertRaises(ValueError):
                self.profiles.read(name)
        for text in ("api_key=example", "x" * 4001):
            with self.assertRaises(ValueError):
                self.profiles.propose("MEMORY.md", text)
        self.save("MEMORY.md", "Valid")
        path = self.profiles.read("MEMORY.md").path
        path.write_bytes(b"\xff")
        with self.assertRaises(ValueError):
            self.profiles.read("MEMORY.md")
        path.write_bytes(b"x" * 20000)
        with self.assertRaises(ValueError):
            self.profiles.read("MEMORY.md")

    def test_symlink_and_concurrent_updates(self):
        self.save("MEMORY.md", "Original")
        proposal = self.profiles.propose("MEMORY.md", "Updated")
        def apply(_):
            try:
                self.profiles.apply(proposal, approved=True)
                return True
            except ConflictError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(apply, range(2))), 1)
        path = self.profiles.read("MEMORY.md").path
        path.unlink()
        target = self.root / "outside"
        target.write_text("Outside")
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            self.profiles.read("MEMORY.md")
        with self.assertRaises(ValueError):
            self.profiles.apply(self.profiles.propose("SOUL.md", "Valid"),
                                approved="true")

    def test_multifile_order_freeze_refresh_and_budgets(self):
        self.save("SOUL.md", "Be concise")
        self.save("USER.md", "Prefers Python")
        self.save("MEMORY.md", "Invoices use PostgreSQL")
        self.db.add(self.ns, "Invoices deploy on Fridays", provenance="manual")
        session = start_session(self.profiles, self.db, "invoices", include_user=True)
        text = session.context
        self.assertLess(text.index("SOUL.md"), text.index("USER.md"))
        self.assertLess(text.index("USER.md"), text.index("MEMORY.md"))
        self.assertLess(text.index("MEMORY.md"), text.index("SQLite"))
        self.assertIn("untrusted", text)
        self.assertIn("subordinate", text)
        self.save("MEMORY.md", "Invoices use SQLite")
        self.assertIn("PostgreSQL", session.context)
        fresh = start_session(self.profiles, self.db, "invoices", include_user=True)
        self.assertIn("Invoices use SQLite", fresh.context)
        shared = start_session(self.profiles, self.db, "invoices")
        self.assertNotIn("Prefers Python", shared.context)
        with self.assertRaises(ValueError):
            start_session(self.profiles, self.db, "invoices", max_chars=50)
        bounded = start_session(self.profiles, self.db, "invoices", max_chars=len(shared.context))
        self.assertLessEqual(len(bounded.context), len(shared.context))

    def test_executor_uses_explicit_snapshot_without_reloading(self):
        self.save("MEMORY.md", "Invoices use PostgreSQL")
        session = start_session(self.profiles, self.db, "invoices")
        self.save("MEMORY.md", "Invoices use SQLite")
        calls = []
        def executor(prompt, workspace, **kwargs):
            calls.append((prompt, workspace, kwargs))
            return "done"
        result = execute_session("Build invoices", self.root, snapshot=session,
                                 executor=executor, options="fake-options")
        self.assertEqual(result, "done")
        self.assertIn("PostgreSQL", calls[0][0])
        self.assertNotIn("Invoices use SQLite", calls[0][0])
        self.assertEqual(calls[0][2]["options"], "fake-options")
        self.assertIn("<user_request>", calls[0][0])

    def test_outcome_file_updates_need_verification_and_review(self):
        with self.assertRaises(ValueError):
            self.profiles.propose("MEMORY.md", "Invoices migrated", origin="outcome")
        proposal = self.profiles.propose("MEMORY.md", "Invoices migrated",
                                        origin="outcome", verified=True)
        self.assertEqual(self.profiles.read("MEMORY.md").text, "")
        self.profiles.apply(proposal, approved=True)
        self.assertEqual(self.profiles.read("MEMORY.md").text, "Invoices migrated")

    def test_cross_owner_proposals_and_manual_edits_are_rejected(self):
        proposal = self.profiles.propose("MEMORY.md", "New summary")
        other = ProfileStore(self.root / "profiles", self.ns, user_id="bob")
        with self.assertRaises(ValueError):
            other.apply(proposal, approved=True)
        self.save("MEMORY.md", "Original")
        proposal = self.profiles.propose("MEMORY.md", "Replacement")
        self.profiles.read("MEMORY.md").path.write_text("Manual correction")
        with self.assertRaises(ConflictError):
            self.profiles.apply(proposal, approved=True)

    def test_profile_root_symlink_is_rejected(self):
        target = self.root / "external"
        target.mkdir()
        linked = self.root / "linked"
        linked.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            ProfileStore(linked, self.ns)
