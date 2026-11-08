import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai.skills import Check, Registry, SkillError
from senai.skills.run import run_request
from senai.skills.cli import main


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        source = self.project / "fixture"
        source.mkdir()
        self.document = "---\nname: example\ndescription: Write a small example\nversion: 1\n---\nCreate a focused result and check it.\n"
        (source / "SKILL.md").write_text(self.document)
        (source / "reference.txt").write_text("Use this reference when needed")
        self.registry = Registry(self.project / "outputs/skills")
        self.skill = self.registry.import_local(source)
        self.calls = []

    def executor(self, prompt, workspace, *, options):
        self.calls.append((prompt, Path(workspace), options))
        (Path(workspace) / "hello.py").write_text("print('hello')\n")
        return "Created hello.py and everything passed!"

    def run_request(self, **overrides):
        args = dict(project=self.project, executor=self.executor)
        args.update(overrides)
        return run_request(self.registry, "Write hello.py", ["example"], **args)

    def test_request_uses_saved_instructions_and_retains_result_without_false_verification(self):
        result = self.run_request()
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.verification, "unverified")
        self.assertIn("Created hello.py", result.response)
        prompt, workspace, options = self.calls[0]
        self.assertEqual(json.loads(prompt.split("\nSKILL_CONTEXT_JSON:\n", 1)[1])[0]["instructions"], self.skill.instructions)
        self.assertTrue(workspace.is_relative_to(self.project / "outputs/skill-runs"))
        self.assertNotEqual(workspace, self.registry.root)
        self.assertEqual(options.sandbox, "workspace-write")
        self.assertIsNone(options.resume)
        self.assertFalse(options.last)
        self.assertEqual(Path(result.workspace), workspace)
        self.assertTrue((workspace / "hello.py").is_file())
        self.assertTrue(Path(result.report_path).is_file())
        self.assertTrue((Path(result.report_path).parent / "response.txt").is_file())
        outcome = self.registry.outcomes("example")[0]
        self.assertEqual(outcome.status, "unverified")
        self.assertEqual(outcome.skill_digest, self.skill.digest)

    def test_supporting_resources_are_copied_with_original_unchanged(self):
        result = self.run_request()
        context = Path(result.report_path).parent / "context/skills/example"
        self.assertEqual((context / "reference.txt").read_text(), "Use this reference when needed")
        self.assertEqual(self.skill.path.read_text(), self.document)
        self.assertIn(str(context), self.calls[0][0])

    def test_checker_supplies_observed_evidence_and_failed_checks_are_not_success(self):
        def checker(response, workspace):
            self.assertIn("Created", response)
            return (Check("hello artifact", (workspace / "hello.py").is_file(), "Observed hello.py"),)
        result = self.run_request(checker=checker)
        self.assertEqual(result.verification, "passed")
        self.assertEqual(self.registry.outcomes("example")[-1].status, "passed")
        failed = self.run_request(checker=lambda *args: (Check("expected content", False, "Wrong content"),))
        self.assertEqual(failed.status, "checks-failed")
        self.assertEqual(failed.verification, "failed")

    def test_checker_error_is_not_a_pass_and_preserves_response(self):
        def broken(*args):
            raise RuntimeError("private diagnostic")
        result = self.run_request(checker=broken)
        self.assertEqual(result.status, "check-error")
        self.assertEqual(result.verification, "error")
        self.assertTrue(result.response)
        self.assertNotIn("private diagnostic", result.error)
        self.assertEqual(self.registry.outcomes("example")[-1].status, "unverified")

    def test_bad_request_or_incompatible_skill_never_invokes_model(self):
        for request, names in ((" ", ["example"]), ("Try", []), ("Try", ["missing"]), ("Try", ["example", "example"])):
            with self.assertRaises(SkillError):
                run_request(self.registry, request, names, project=self.project, executor=self.executor)
        with self.assertRaises(SkillError):
            self.run_request(compatibility_check=lambda metadata: False)
        self.assertEqual(self.calls, [])
        self.assertFalse((self.project / "outputs/skill-runs").exists())

    def test_read_only_and_native_skill_options_preserve_existing_transport(self):
        with patch("senai.codex.run_codex", return_value="Read-only answer") as run:
            result = run_request(self.registry, "Explain the workflow", ["example"], project=self.project, read_only=True, native_skills=("native-helper",), model="chosen-model")
        self.assertEqual(result.status, "completed")
        self.assertIn("$native-helper", run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs["options"].sandbox, "read-only")
        self.assertEqual(run.call_args.kwargs["options"].model, "chosen-model")

    def test_executor_failure_is_reported_without_success_evidence(self):
        def broken(*args, **kwargs):
            raise RuntimeError("private native failure")
        result = self.run_request(executor=broken)
        self.assertEqual(result.status, "execution-error")
        self.assertEqual(result.verification, "unverified")
        self.assertEqual(self.registry.outcomes("example"), [])
        self.assertNotIn("private native failure", result.error)
        self.assertTrue(Path(result.report_path).exists())

    def test_inflight_outcome_stays_bound_to_selected_version_after_another_activation(self):
        evidence = self.registry.record_outcome("example", digest=self.skill.digest, request="Prior case", result="Wrong", checks=(Check("case", False, "Observed failure"),))
        revision = self.registry.propose_revision("example", document=self.document.replace("version: 1", "version: 2").replace("Create a focused result", "Create and verify a focused result"), outcome_ids=(evidence.id,), reason="Correct observed issue")
        self.registry.validate_revision(revision.id, validator=lambda *args: (Check("case", True, "Observed pass"),))
        def concurrent(prompt, workspace, *, options):
            self.registry.activate_revision(revision.id)
            return "Original version run completed"
        result = self.run_request(executor=concurrent)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.registry.outcomes("example")[-1].skill_digest, self.skill.digest)
        self.assertEqual(self.registry.select(["example"])[0].version, "2")

    def test_cli_run_executes_and_checks_explicit_expected_artifact(self):
        out, err = io.StringIO(), io.StringIO()
        with patch("senai.codex.run_codex", side_effect=self.executor):
            code = main(["--project", str(self.project), "run", "example", "Write hello.py", "--expect-file", "hello.py"], stdout=out, stderr=err)
        self.assertEqual(code, 0, err.getvalue())
        result = json.loads(out.getvalue())
        self.assertEqual(result["verification"], "passed")
        self.assertTrue((Path(result["workspace"]) / "hello.py").is_file())

    def test_cli_missing_expected_file_is_failure_and_escape_is_rejected_before_execution(self):
        for expected, code_expected in (("missing.py", 2), ("../escape", 2)):
            out, err = io.StringIO(), io.StringIO()
            self.calls.clear()
            with patch("senai.codex.run_codex", side_effect=self.executor):
                code = main(["--project", str(self.project), "run", "example", "Write hello.py", "--expect-file", expected], stdout=out, stderr=err)
            self.assertEqual(code, code_expected)
            if expected.startswith(".."):
                self.assertEqual(self.calls, [])
            else:
                self.assertEqual(json.loads(out.getvalue())["verification"], "failed")

    def test_multiple_saved_skills_get_exact_context_and_separate_outcome_links(self):
        other_source = self.project / "other-source"
        other_source.mkdir()
        (other_source / "SKILL.md").write_text(self.document.replace("name: example", "name: other"))
        other = self.registry.import_local(other_source)
        result = run_request(self.registry, "Write hello.py", ["example", "other"], project=self.project, executor=self.executor)
        self.assertEqual(len(result.outcome_ids), 2)
        self.assertEqual([skill.digest for skill in result.skills], [self.skill.digest, other.digest])
        self.assertEqual(self.registry.outcomes("other")[0].skill_digest, other.digest)

    def test_wrong_project_registry_is_rejected_before_execution(self):
        wrong_project = self.project / "other-project"
        wrong_project.mkdir()
        with self.assertRaises(SkillError):
            self.run_request(project=wrong_project)
        self.assertEqual(self.calls, [])

    def test_explicit_file_check_rejects_symlink_artifacts(self):
        from senai.skills.run import expected_files_checker
        workspace = self.project / "check-workspace"
        workspace.mkdir()
        outside = self.project / "outside.txt"
        outside.write_text("Not an artifact")
        (workspace / "linked.txt").symlink_to(outside)
        checks = expected_files_checker(["linked.txt"])("Claimed success", workspace)
        self.assertFalse(checks[0].passed)
