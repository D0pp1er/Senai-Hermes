import sqlite3
import tempfile
import unittest
from pathlib import Path

from senai.skills import Check, Registry, SkillError


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / "source"
        source.mkdir()
        self.document = "---\nname: sample\ndescription: Example\nversion: 1\n---\nCheck output.\n"
        (source / "SKILL.md").write_text(self.document)
        self.registry = Registry(self.root / "registry")
        self.base = self.registry.import_local(source)
        outcome = self.registry.record_outcome("sample", digest=self.base.digest, request="Check", result="Wrong", checks=(Check("expected", False, "Expected 4, got 3"),))
        self.outcome_id = outcome.id
        self.candidate = self.propose("2")

    def propose(self, version):
        return self.registry.propose_revision("sample", document=self.document.replace("version: 1", "version: " + version).replace("Check output.", "Check output and boundaries for version " + version + "."), outcome_ids=(self.outcome_id,), reason="Fix boundary case")

    def validate(self, candidate=None, passed=True):
        return self.registry.validate_revision((candidate or self.candidate).id, validator=lambda *args: (Check("regression", passed, "Observed case result"),))

    def test_activation_persists_and_execution_receives_new_instructions(self):
        validation = self.validate()
        active = self.registry.activate_revision(self.candidate.id)
        restarted = Registry(self.root / "registry")
        self.assertEqual(restarted.select(["sample"]), [active])
        self.assertEqual(active.version, "2")
        self.assertEqual(active.digest, self.candidate.digest)
        self.assertEqual(active.source, self.base.source)
        result = restarted.execute("Check again", ["sample"], executor=lambda request, skills: skills[0].instructions)
        self.assertEqual(result, self.candidate.instructions)
        self.assertEqual(restarted.versions("sample"), [self.base, active])
        event = restarted.history("sample")[-1]
        self.assertEqual(event.action, "activate")
        self.assertEqual(event.from_digest, self.base.digest)
        self.assertEqual(event.to_digest, active.digest)
        self.assertEqual(event.validation_id, validation.id)
        self.assertEqual(event.revision_id, self.candidate.id)

    def test_without_passing_validation_activation_is_rejected(self):
        for validation in (None, False, "error"):
            if validation is False:
                self.validate(passed=False)
            elif validation == "error":
                self.registry.validate_revision(self.candidate.id, validator=lambda *args: ())
            with self.assertRaises(SkillError):
                self.registry.activate_revision(self.candidate.id)
            self.assertEqual(self.registry.select(["sample"]), [self.base])
            self.assertEqual(self.registry.versions("sample"), [self.base])
            self.assertEqual([event.action for event in self.registry.history("sample")], ["import"])

    def test_latest_failed_attempt_blocks_an_earlier_pass(self):
        self.validate()
        self.validate(passed=False)
        with self.assertRaises(SkillError):
            self.registry.activate_revision(self.candidate.id)
        self.assertEqual(self.registry.select(["sample"]), [self.base])

    def test_stale_sibling_proposal_cannot_activate_or_validate(self):
        sibling = self.propose("3")
        self.validate()
        self.validate(sibling)
        active = self.registry.activate_revision(self.candidate.id)
        with self.assertRaises(SkillError):
            self.registry.activate_revision(sibling.id)
        with self.assertRaises(SkillError):
            self.validate(sibling)
        self.assertEqual(self.registry.select(["sample"]), [active])

    def test_candidate_changed_after_validation_cannot_activate(self):
        self.validate()
        self.candidate.path.write_text("Changed candidate")
        with self.assertRaises(SkillError):
            self.registry.activate_revision(self.candidate.id)
        self.assertEqual(self.registry.select(["sample"]), [self.base])

    def test_rollback_restores_accepted_bytes_and_keeps_history(self):
        self.validate()
        active = self.registry.activate_revision(self.candidate.id)
        restored = self.registry.rollback("sample", digest=self.base.digest, reason="Restore prior behavior")
        restarted = Registry(self.root / "registry")
        self.assertEqual(restored, self.base)
        self.assertEqual(restarted.select(["sample"]), [self.base])
        self.assertEqual(restarted.versions("sample"), [self.base, active])
        events = restarted.history("sample")
        self.assertEqual([event.action for event in events], ["import", "activate", "rollback"])
        self.assertEqual(events[-1].reason, "Restore prior behavior")
        self.assertEqual(events[-1].from_digest, active.digest)
        self.assertEqual(events[-1].to_digest, self.base.digest)
        self.assertEqual(len(restarted.validations(self.candidate.id)), 1)
        self.assertEqual(restarted.revisions("sample")[0].status, "accepted")

    def test_rollback_cannot_select_a_never_accepted_candidate_or_empty_reason(self):
        for digest, reason in ((self.candidate.digest, "Not accepted"), (self.base.digest, " "), ("../escape", "Invalid digest")):
            with self.subTest(digest=digest):
                with self.assertRaises(SkillError):
                    self.registry.rollback("sample", digest=digest, reason=reason)
        self.assertEqual(self.registry.select(["sample"]), [self.base])

    def test_rollback_can_recover_a_corrupted_active_package(self):
        self.validate()
        active = self.registry.activate_revision(self.candidate.id)
        active.path.write_text("Corrupted active instructions")
        restored = self.registry.rollback("sample", digest=self.base.digest, reason="Recover intact original")
        self.assertEqual(restored, self.base)
        self.assertEqual(self.registry.select(["sample"]), [self.base])

    def test_rollback_rejects_corrupted_destination(self):
        self.validate()
        active = self.registry.activate_revision(self.candidate.id)
        self.base.path.write_text("Corrupted original")
        with self.assertRaises(SkillError):
            self.registry.rollback("sample", digest=self.base.digest, reason="Try corrupted destination")
        self.assertEqual(self.registry.select(["sample"]), [active])

    def test_previous_version_names_cannot_be_reused(self):
        self.validate()
        self.registry.activate_revision(self.candidate.id)
        outcome = self.registry.record_outcome("sample", digest=self.candidate.digest, request="Try", result="ok", checks=(Check("case", True, "passed"),))
        with self.assertRaises(SkillError):
            self.registry.propose_revision("sample", document=self.document.replace("Check output.", "Different instructions."), outcome_ids=(outcome.id,), reason="Reuse original version")

    def test_old_registry_migrates_without_losing_active_skill_or_outcomes(self):
        with sqlite3.connect(self.registry.root / "registry.sqlite3") as db:
            db.execute("DROP TABLE IF EXISTS accepted_versions")
            db.execute("DROP TABLE IF EXISTS activation_history")
        migrated = Registry(self.registry.root)
        self.assertEqual(migrated.select(["sample"]), [self.base])
        self.assertEqual(migrated.versions("sample"), [self.base])
        self.assertEqual(migrated.outcomes("sample")[0].id, self.outcome_id)
        again = Registry(self.registry.root)
        self.assertEqual(len(again.history("sample")), 1)
