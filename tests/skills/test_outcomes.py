import tempfile
import unittest
from pathlib import Path

from senai.skills import Check, Registry, SkillError


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        source = self.root / "source"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: sample\ndescription: Test workflow\n---\nCheck the result.\n")
        self.registry = Registry(self.root / "registry")
        self.skill = self.registry.import_local(source)

    def record(self, **overrides):
        args = dict(digest=self.skill.digest, request="Build example", result="Built", checks=(Check("unit tests", True, "3 tests passed"),))
        args.update(overrides)
        return self.registry.record_outcome("sample", **args)

    def test_verified_success_survives_restart_with_exact_skill_identity(self):
        outcome = self.record()
        restarted = Registry(self.root / "registry")
        self.assertEqual(restarted.outcomes("sample"), [outcome])
        self.assertEqual(outcome.skill_digest, self.skill.digest)
        self.assertEqual(outcome.skill_version, "1")
        self.assertEqual(outcome.status, "passed")
        self.assertEqual(outcome.checks, (Check("unit tests", True, "3 tests passed"),))
        self.assertTrue(outcome.created_at.endswith("+00:00"))

    def test_failed_checks_and_correction_are_retained(self):
        outcome = self.record(checks=(Check("unit tests", False, "wrong output"),), correction="Validate output before saving")
        self.assertEqual(outcome.status, "failed")
        self.assertEqual(self.registry.outcomes("sample")[0].correction, "Validate output before saving")
        self.assertEqual(self.registry.select(["sample"])[0], self.skill)

    def test_success_text_without_checks_remains_unverified(self):
        outcome = self.record(result="Everything passed!", checks=())
        self.assertEqual(outcome.status, "unverified")

    def test_invalid_records_do_not_persist(self):
        for overrides in (dict(digest="0" * 64), dict(request=" "), dict(result=3), dict(checks=(Check("test", "yes", "log"),)), dict(checks=(Check("", True, "log"),)), dict(checks=(Check("test", True, ""),)), dict(correction=3)):
            with self.subTest(overrides=overrides):
                with self.assertRaises(SkillError):
                    self.record(**overrides)
                self.assertEqual(self.registry.outcomes("sample"), [])

    def test_registry_namespaces_do_not_share_evidence(self):
        self.record()
        other = Registry(self.root / "other")
        with self.assertRaises(SkillError):
            other.outcomes("sample")

    def test_multiple_records_have_distinct_ids_and_preserve_order(self):
        first = self.record()
        second = self.record(result="Second attempt")
        self.assertNotEqual(first.id, second.id)
        self.assertEqual(self.registry.outcomes("sample"), [first, second])
