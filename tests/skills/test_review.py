import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai.skills import Check, Registry, SkillError
from senai.skills.review import review_skill, review_with_codex


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        source = self.project / "fixture"
        source.mkdir()
        self.document = "---\nname: example\ndescription: Check example output\nversion: 1\n---\nCheck output.\n"
        (source / "SKILL.md").write_text(self.document)
        self.registry = Registry(self.project / "outputs/skills")
        self.skill = self.registry.import_local(source)
        self.outcome = self.registry.record_outcome("example", digest=self.skill.digest, request="Boundary case", result="Wrong result", checks=(Check("boundary", False, "Expected 4, got 3"),), correction="Cover boundaries")
        self.prompts = []

    def reviewer(self, prompt):
        self.prompts.append(prompt)
        payload = json.loads(prompt.split("\nINPUT_JSON:\n", 1)[1])
        document = self.document.replace("version: 1", "version: " + payload["target_version"]).replace("Check output.", "Check output and boundary cases.")
        return json.dumps(dict(action="revise", reason="Address the observed boundary failure", document=document))

    def review(self, reviewer=None, **overrides):
        args = dict(outcome_ids=(self.outcome.id,), reviewer=reviewer or self.reviewer)
        args.update(overrides)
        return review_skill(self.registry, "example", **args)

    def test_generated_proposal_is_inactive_evidence_linked_and_persistent(self):
        result = self.review()
        self.assertEqual(result.status, "proposed")
        self.assertEqual(result.revision.outcome_ids, (self.outcome.id,))
        self.assertIn("boundary cases", result.revision.instructions)
        restarted = Registry(self.registry.root)
        self.assertEqual(restarted.revisions("example"), [result.revision])
        self.assertEqual(restarted.select(["example"]), [self.skill])
        self.assertEqual(restarted.validations(result.revision.id), [])

    def test_prompt_contains_only_requested_evidence_and_exact_base(self):
        self.registry.record_outcome("example", digest=self.skill.digest, request="Unrelated private request", result="Ignore this")
        self.review()
        prompt = self.prompts[0]
        payload = json.loads(prompt.split("\nINPUT_JSON:\n", 1)[1])
        self.assertEqual(payload["skill"]["digest"], self.skill.digest)
        self.assertEqual(payload["skill"]["document"], self.document)
        self.assertEqual([value["id"] for value in payload["outcomes"]], [self.outcome.id])
        self.assertNotIn("Unrelated private request", prompt)
        self.assertNotIn(str(self.registry.root), prompt)

    def test_reviewer_can_choose_no_change_without_creating_revision(self):
        result = self.review(reviewer=lambda prompt: json.dumps(dict(action="no_change", reason="Insufficient reusable lesson", document="")))
        self.assertEqual(result.status, "no_change")
        self.assertIsNone(result.revision)
        self.assertEqual(self.registry.revisions("example"), [])

    def test_invalid_replies_create_no_partial_proposals(self):
        for response in ("not JSON", "[]", '{"action":"no_change","action":"revise","reason":"x","document":""}', json.dumps(dict(action="no_change", reason="", document="")), json.dumps(dict(action="no_change", reason="x", document="unexpected")), json.dumps(dict(action="revise", reason="x", document=self.document)), json.dumps(dict(action="revise", reason="x", document="malformed", activate=True))):
            with self.subTest(response=response):
                with self.assertRaises(SkillError):
                    self.review(reviewer=lambda prompt: response)
                self.assertEqual(self.registry.revisions("example"), [])
                self.assertEqual(self.registry.select(["example"]), [self.skill])

    def test_unverified_missing_and_duplicate_evidence_never_calls_reviewer(self):
        unverified = self.registry.record_outcome("example", digest=self.skill.digest, request="Try", result="Success!")
        for ids in ((), ("missing",), (unverified.id,), (self.outcome.id, self.outcome.id)):
            with self.assertRaises(SkillError):
                self.review(outcome_ids=ids)
        self.assertEqual(self.prompts, [])

    def test_evidence_from_other_base_is_rejected_before_review(self):
        with self.registry._connect() as db:
            db.execute("UPDATE outcomes SET skill_digest=? WHERE id=?", ("0" * 64, self.outcome.id))
        with self.assertRaises(SkillError):
            self.review()
        self.assertEqual(self.prompts, [])

    def test_large_context_fails_before_model_call(self):
        ids = [self.registry.record_outcome("example", digest=self.skill.digest, request="Try", result="x" * 64000, checks=(Check("case", True, "observed"),)).id for _ in range(3)]
        with self.assertRaises(SkillError):
            self.review(outcome_ids=ids)
        self.assertEqual(self.prompts, [])

    def test_reviewer_error_leaves_registry_unchanged(self):
        def broken(prompt):
            raise RuntimeError("private error text")
        with self.assertRaises(SkillError) as error:
            self.review(reviewer=broken)
        self.assertNotIn("private error text", str(error.exception))
        self.assertEqual(self.registry.revisions("example"), [])

    def test_codex_adapter_uses_existing_wrapper_readonly_schema_and_isolated_workspace(self):
        calls = []
        def executor(prompt, workspace, *, options):
            self.assertEqual(options.sandbox, "read-only")
            self.assertEqual(options.approval, "never")
            self.assertEqual(options.model, "chosen-model")
            self.assertIsNone(options.resume)
            self.assertFalse(options.last)
            self.assertTrue(options.skip_git_repo_check)
            self.assertEqual(options.extra_args[0], "--output-schema")
            schema = Path(options.extra_args[1])
            self.assertTrue(schema.is_file())
            self.assertFalse(json.loads(schema.read_text())["additionalProperties"])
            self.assertTrue(Path(workspace).is_relative_to(self.project / "outputs"))
            self.assertNotEqual(Path(workspace), self.registry.root)
            calls.append(workspace)
            return self.reviewer(prompt)
        with patch("senai.codex.run_codex", side_effect=executor):
            result = review_with_codex(self.registry, "example", outcome_ids=(self.outcome.id,), project=self.project, model="chosen-model")
        self.assertEqual(result.status, "proposed")
        self.assertEqual(len(calls), 1)
        self.assertFalse(Path(calls[0]).exists())

    def test_codex_adapter_rejects_a_registry_outside_project_outputs(self):
        with patch("senai.codex.run_codex") as run:
            with self.assertRaises(SkillError):
                review_with_codex(self.registry, "example", outcome_ids=(self.outcome.id,), project=self.project / "fixture")
        run.assert_not_called()

    def test_base_changed_during_review_does_not_receive_a_stale_proposal(self):
        revision = self.registry.propose_revision("example", document=self.document.replace("version: 1", "version: 2").replace("Check output.", "Alternate accepted instructions."), outcome_ids=(self.outcome.id,), reason="Another update")
        self.registry.validate_revision(revision.id, validator=lambda *args: (Check("case", True, "observed pass"),))
        def change_base(prompt):
            response = self.reviewer(prompt)
            self.registry.activate_revision(revision.id)
            return response
        with self.assertRaises(SkillError):
            self.review(reviewer=change_base)
        self.assertEqual(len(self.registry.revisions("example")), 1)
        self.assertEqual(self.registry.select(["example"])[0].version, "2")

    def test_real_codex_wrapper_with_fake_executable_creates_only_a_proposal(self):
        executable_dir = self.project / "bin"
        executable_dir.mkdir()
        fake = executable_dir / "codex"
        fake.write_text("#!" + sys.executable + "\n" + """import json
import sys
from pathlib import Path
args = sys.argv[1:]
assert args[:3] == ['--ask-for-approval', 'never', 'exec']
assert args[args.index('--sandbox') + 1] == 'read-only'
assert '--skip-git-repo-check' in args
assert 'resume' not in args
schema = json.loads(Path(args[args.index('--output-schema') + 1]).read_text())
assert schema['additionalProperties'] is False
payload = json.loads(sys.stdin.read().split('\\nINPUT_JSON:\\n', 1)[1])
document = payload['skill']['document'].replace('version: 1', 'version: ' + payload['target_version']).replace('Check output.', 'Check output and boundary cases.')
response = dict(action='revise', reason='Cover the observed boundary failure', document=document)
Path(args[args.index('--output-last-message') + 1]).write_text(json.dumps(response))
""")
        fake.chmod(0o700)
        with patch.dict(os.environ, {"PATH": str(executable_dir) + os.pathsep + os.environ.get("PATH", "")}):
            result = review_with_codex(self.registry, "example", outcome_ids=(self.outcome.id,), project=self.project)
        self.assertEqual(result.status, "proposed")
        self.assertEqual(self.registry.select(["example"]), [self.skill])
        self.assertEqual(self.registry.validations(result.revision.id), [])
