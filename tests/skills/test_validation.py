import tempfile
import unittest
from pathlib import Path

from senai.skills import Check, Registry, SkillError


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / "source"
        source.mkdir()
        document = "---\nname: sample\ndescription: Example\nversion: 1\n---\nCheck output.\n"
        (source / "SKILL.md").write_text(document)
        self.registry = Registry(self.root / "registry")
        self.base = self.registry.import_local(source)
        self.outcome = self.registry.record_outcome("sample", digest=self.base.digest, request="Check", result="Wrong", checks=(Check("expected", False, "Expected 4, got 3"),))
        self.revision = self.registry.propose_revision("sample", document=document.replace("version: 1", "version: 2").replace("Check output.", "Check boundary cases too."), outcome_ids=(self.outcome.id,), reason="Fix boundary failure")

    def test_passing_validation_passes_exact_context_and_survives_restart(self):
        calls = []
        def validator(base, candidate, outcomes):
            calls.append((base, candidate, outcomes))
            return (Check("old behavior", True, "3 cases passed"), Check("boundary regression", True, "boundary case passed"))
        validation = self.registry.validate_revision(self.revision.id, validator=validator)
        self.assertEqual(calls, [(self.base, self.revision, (self.outcome,))])
        self.assertEqual(validation.status, "passed")
        self.assertEqual(validation.base_digest, self.base.digest)
        self.assertEqual(validation.candidate_digest, self.revision.digest)
        self.assertEqual(len(validation.checks), 2)
        restarted = Registry(self.root / "registry")
        self.assertEqual(restarted.validations(self.revision.id), [validation])
        self.assertEqual(restarted.select(["sample"]), [self.base])

    def test_failed_regression_is_recorded_without_activation(self):
        validation = self.registry.validate_revision(self.revision.id, validator=lambda *args: (Check("regression", False, "old case failed"),))
        self.assertEqual(validation.status, "failed")
        self.assertEqual(self.registry.validations(self.revision.id), [validation])
        self.assertEqual(self.registry.select(["sample"]), [self.base])

    def test_empty_or_malformed_checks_are_not_a_pass(self):
        for checks in ((), (Check("test", "yes", "log"),), (Check("test", True, ""),), "passed", None):
            with self.subTest(checks=checks):
                validation = self.registry.validate_revision(self.revision.id, validator=lambda *args: checks)
                self.assertEqual(validation.status, "error")
                self.assertTrue(validation.error)
                self.assertEqual(validation.checks, ())

    def test_validator_exception_is_recorded_without_leaking_exception_text(self):
        def broken(*args):
            raise RuntimeError("private fixture text")
        validation = self.registry.validate_revision(self.revision.id, validator=broken)
        self.assertEqual(validation.status, "error")
        self.assertNotIn("private fixture text", validation.error)
        self.assertEqual(self.registry.validations(self.revision.id), [validation])

    def test_tampered_candidate_is_rejected_before_validator_runs(self):
        self.revision.path.write_text("tampered")
        calls = []
        with self.assertRaises(SkillError):
            self.registry.validate_revision(self.revision.id, validator=lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_validator_cannot_get_a_pass_after_modifying_candidate(self):
        def mutate(*args):
            self.revision.path.write_text("changed")
            return (Check("fake", True, "claimed pass"),)
        with self.assertRaises(SkillError):
            self.registry.validate_revision(self.revision.id, validator=mutate)
        with self.registry._connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM validations").fetchone()[0], 0)
        self.assertEqual(self.registry.select(["sample"]), [self.base])

    def test_unknown_revision_is_rejected_before_validator_runs(self):
        calls = []
        with self.assertRaises(SkillError):
            self.registry.validate_revision("missing", validator=lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_revalidation_retains_failed_attempt_after_a_pass(self):
        first = self.registry.validate_revision(self.revision.id, validator=lambda *args: (Check("case", True, "passed"),))
        second = self.registry.validate_revision(self.revision.id, validator=lambda *args: (Check("case", False, "failed"),))
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(self.registry.validations(self.revision.id), [first, second])
        self.assertEqual(self.registry.validations(self.revision.id)[-1].status, "failed")
