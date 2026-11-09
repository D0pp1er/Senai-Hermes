import tempfile
import unittest
from pathlib import Path

from senai.skills import Check, Registry, SkillError


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.document = "---\nname: sample\ndescription: Example\nversion: 1\n---\nCheck output.\n"
        (self.source / "SKILL.md").write_text(self.document)
        (self.source / "reference.txt").write_text("Keep this reference")
        self.registry = Registry(self.root / "registry")
        self.skill = self.registry.import_local(self.source)
        self.outcome = self.registry.record_outcome("sample", digest=self.skill.digest, request="Check example", result="Wrong output", checks=(Check("expected output", False, "Expected 4, got 3"),), correction="Check boundary cases")
        self.candidate = self.document.replace("version: 1", "version: 2").replace("Check output.", "Check output and boundary cases.")

    def propose(self, **overrides):
        args = dict(document=self.candidate, outcome_ids=(self.outcome.id,), reason="Address verified boundary failure")
        args.update(overrides)
        return self.registry.propose_revision("sample", **args)

    def test_proposal_survives_restart_without_changing_active_skill(self):
        revision = self.propose()
        restarted = Registry(self.root / "registry")
        self.assertEqual(restarted.revisions("sample"), [revision])
        self.assertEqual(restarted.select(["sample"]), [self.skill])
        self.assertEqual(revision.status, "proposed")
        self.assertEqual(revision.base_digest, self.skill.digest)
        self.assertEqual(revision.version, "2")
        self.assertEqual(revision.outcome_ids, (self.outcome.id,))
        self.assertNotEqual(revision.digest, self.skill.digest)
        self.assertEqual(revision.source, self.skill.source)
        self.assertIn("boundary cases", revision.instructions)

    def test_proposal_preserves_supporting_files_and_original_package(self):
        revision = self.propose()
        self.assertEqual((revision.path.parent / "reference.txt").read_text(), "Keep this reference")
        self.assertEqual(self.skill.path.read_text(), self.document)
        self.assertEqual(revision.path.read_text(), self.candidate)

    def test_rejects_missing_duplicate_unknown_and_unverified_evidence(self):
        unverified = self.registry.record_outcome("sample", digest=self.skill.digest, request="Try", result="Success!")
        for ids in ((), ("unknown",), (self.outcome.id, self.outcome.id), (unverified.id,)):
            with self.subTest(ids=ids):
                with self.assertRaises(SkillError):
                    self.propose(outcome_ids=ids)
                self.assertEqual(self.registry.revisions("sample"), [])

    def test_rejects_evidence_from_another_skill(self):
        other = self.root / "other"
        other.mkdir()
        (other / "SKILL.md").write_text(self.document.replace("name: sample", "name: other"))
        skill = self.registry.import_local(other)
        outcome = self.registry.record_outcome("other", digest=skill.digest, request="Try", result="ok", checks=(Check("test", True, "passed"),))
        with self.assertRaises(SkillError):
            self.propose(outcome_ids=(outcome.id,))
        self.assertEqual(self.registry.revisions("sample"), [])

    def test_invalid_candidates_leave_no_partial_activation_or_package(self):
        before = set(self.registry.root.iterdir())
        for document in ("bad", self.candidate.replace("name: sample", "name: changed"), self.candidate.replace("version: 2", "version: 1"), self.document.replace("version: 1", "version: 2"), self.candidate.replace("version: 2", "tools: shell")):
            with self.subTest(document=document):
                with self.assertRaises(SkillError):
                    self.propose(document=document)
                self.assertEqual(self.registry.revisions("sample"), [])
                self.assertEqual(self.registry.select(["sample"]), [self.skill])
                self.assertEqual(set(self.registry.root.iterdir()), before)

    def test_duplicate_revision_versions_are_rejected(self):
        revision = self.propose()
        with self.assertRaises(SkillError):
            self.propose()
        self.assertEqual(self.registry.revisions("sample"), [revision])

    def test_candidate_tampering_is_detected(self):
        revision = self.propose()
        revision.path.write_text("Tampered")
        with self.assertRaises(SkillError):
            self.registry.revisions("sample")
        self.assertEqual(self.registry.select(["sample"]), [self.skill])

    def test_passed_evidence_can_support_a_revision_but_empty_reason_cannot(self):
        outcome = self.registry.record_outcome("sample", digest=self.skill.digest, request="Try", result="ok", checks=(Check("test", True, "passed"),))
        with self.assertRaises(SkillError):
            self.propose(reason=" ")
        self.assertEqual(self.registry.revisions("sample"), [])
        revision = self.propose(outcome_ids=(outcome.id,))
        self.assertEqual(revision.outcome_ids, (outcome.id,))
