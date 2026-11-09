import tempfile
import unittest
from pathlib import Path

from senai.skills import Check, Registry, SkillError


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "fixture"
        self.source.mkdir()
        self.registry = Registry(self.root / "registry")
        self.document = """---
name: example
description: >-
  Check output
  and boundary cases.
license: MIT
compatibility: Requires Python 3.10
allowed-tools: Read Bash(python:*)
metadata:
  version: "1.2"
  author: Example author
  hermes:
    tags: [checks, testing]
    category: development
---
Check the result against expected output.
"""

    def write(self, document=None):
        (self.source / "SKILL.md").write_text(document or self.document)

    def test_standard_and_hermes_metadata_survive_import_and_restart(self):
        self.write()
        skill = self.registry.import_local(self.source)
        restarted = Registry(self.registry.root)
        metadata = restarted.metadata("example")
        self.assertEqual(skill.version, "1.2")
        self.assertEqual(skill.description, "Check output and boundary cases.")
        self.assertEqual(metadata["license"], "MIT")
        self.assertEqual(metadata["compatibility"], "Requires Python 3.10")
        self.assertEqual(metadata["allowed-tools"], "Read Bash(python:*)")
        self.assertEqual(metadata["metadata"]["hermes"]["tags"], ["checks", "testing"])
        self.assertEqual(skill.path.read_text(), self.document)

    def test_compatibility_predicate_blocks_execution_without_granting_tools(self):
        self.write()
        self.registry.import_local(self.source)
        calls = []
        def checker(metadata):
            calls.append(metadata)
            return False
        with self.assertRaises(SkillError):
            self.registry.execute("Check", ["example"], executor=lambda *args: self.fail("Must not execute"), compatibility_check=checker)
        self.assertEqual(calls[0]["compatibility"], "Requires Python 3.10")
        selected = self.registry.select(["example"], compatibility_check=lambda metadata: True)
        self.assertEqual(selected[0].name, "example")

    def test_optional_metadata_cannot_be_silently_removed_by_revision(self):
        self.write()
        skill = self.registry.import_local(self.source)
        outcome = self.registry.record_outcome("example", digest=skill.digest, request="Try", result="Failure", checks=(Check("case", False, "Wrong value"),))
        changed = self.document.replace('version: "1.2"', 'version: "2"').replace("Check the result", "Check boundary cases and the result")
        for document in (changed.replace("license: MIT\n", ""), changed.replace("compatibility: Requires Python 3.10", "compatibility: Requires network access")):
            with self.assertRaises(SkillError):
                self.registry.propose_revision("example", document=document, outcome_ids=(outcome.id,), reason="Fix failure")
        revision = self.registry.propose_revision("example", document=changed, outcome_ids=(outcome.id,), reason="Fix failure")
        self.assertEqual(revision.version, "2")

    def test_duplicate_keys_tags_anchors_and_aliases_are_rejected(self):
        headers = ["name: example\nname: other\ndescription: Test", "name: example\ndescription: Test\nmetadata:\n  author: a\n  author: b", "name: example\ndescription: !!python/object/apply:os.system ['echo forbidden']", "name: example\ndescription: &text Test\nlicense: *text", "name: example\ndescription: Test\nmetadata: {<<: {author: a}}"]
        for header in headers:
            with self.subTest(header=header):
                self.write("---\n" + header + "\n---\nInstructions\n")
                with self.assertRaises(SkillError):
                    self.registry.import_local(self.source)
                self.assertEqual(self.registry.list(), [])

    def test_invalid_types_lengths_and_unknown_fields_are_rejected(self):
        headers = ["name: example\ndescription: [not, text]", "name: example\ndescription: Test\nmetadata: text", "name: example\ndescription: Test\nlicense: [MIT]", "name: example\ndescription: Test\ncompatibility: " + "x" * 501, "name: example\ndescription: " + "x" * 1025, "name: example\ndescription: Test\nunknown: data", "name: example\ndescription: Test\nversion: 2\nmetadata: {version: 3}"]
        for header in headers:
            with self.subTest(header=header[:100]):
                self.write("---\n" + header + "\n---\nInstructions\n")
                with self.assertRaises(SkillError):
                    self.registry.import_local(self.source)
                self.assertEqual(self.registry.list(), [])

    def test_quoted_scalars_and_comments_preserve_literal_meaning(self):
        self.write('---\nname: example # comment\ndescription: "Check: output # literal"\nmetadata: {version: "1.0", switch: on}\n---\nInstructions\n')
        skill = self.registry.import_local(self.source)
        self.assertEqual(skill.description, "Check: output # literal")
        self.assertEqual(self.registry.metadata("example")["metadata"]["switch"], "on")

    def test_oversized_or_deep_metadata_is_rejected_without_activation(self):
        for header in ("name: example\ndescription: Test\nmetadata: {value: '" + "x" * 17000 + "'}", "name: example\ndescription: Test\nmetadata: " + "[" * 20 + "value" + "]" * 20):
            self.write("---\n" + header + "\n---\nInstructions\n")
            with self.assertRaises(SkillError):
                self.registry.import_local(self.source)
            self.assertEqual(self.registry.list(), [])

    def test_model_review_preserves_optional_metadata_in_generated_proposal(self):
        import json
        from senai.skills import review_skill
        self.write()
        skill = self.registry.import_local(self.source)
        outcome = self.registry.record_outcome("example", digest=skill.digest, request="Try", result="Boundary failure", checks=(Check("case", False, "Wrong result"),))
        def reviewer(prompt):
            payload = json.loads(prompt.split("\nINPUT_JSON:\n", 1)[1])
            document = self.document.replace('version: "1.2"', 'version: "' + payload["target_version"] + '"').replace("Check the result", "Check boundary cases and the result")
            return json.dumps(dict(action="revise", reason="Fix observed boundary", document=document))
        result = review_skill(self.registry, "example", outcome_ids=(outcome.id,), reviewer=reviewer)
        self.assertEqual(result.status, "proposed")
        self.assertIn("license: MIT", result.revision.path.read_text())
        self.registry.validate_revision(result.revision.id, validator=lambda *args: (Check("regression", True, "Observed pass"),))
        self.registry.activate_revision(result.revision.id)
        self.assertEqual(self.registry.metadata("example")["metadata"]["hermes"]["category"], "development")
        self.assertEqual(self.registry.metadata("example")["version"], result.revision.version)
