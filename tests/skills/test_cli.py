import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from senai.skills import Registry
from senai.skills.review import ReviewResult

from senai.skills.cli import main


class SkillsCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.fixture = self.project / "fixture"
        self.fixture.mkdir()
        (self.fixture / "SKILL.md").write_text("---\nname: example\ndescription: Example workflow\nversion: 1\n---\nCheck output before reporting success.\n")

    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        code = main(["--project", str(self.project), *args], stdout=out, stderr=err)
        return code, out.getvalue(), err.getvalue()

    def test_list_missing_registry_is_empty_and_creates_no_state(self):
        code, out, err = self.call("list")
        self.assertEqual((code, json.loads(out), err), (0, [], ""))
        self.assertFalse((self.project / "outputs").exists())

    def test_import_list_and_show_persist_across_cli_calls(self):
        code, out, err = self.call("import", str(self.fixture))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["name"], "example")
        self.assertTrue((self.project / "outputs/skills/registry.sqlite3").is_file())
        code, out, err = self.call("list")
        skills = json.loads(out)
        self.assertEqual(skills[0]["version"], "1")
        self.assertNotIn("instructions", skills[0])
        code, out, err = self.call("show", "example")
        self.assertIn("Check output", json.loads(out)["instructions"])

    def test_context_returns_request_and_selected_instructions_without_execution(self):
        self.call("import", str(self.fixture))
        code, out, err = self.call("context", "example", "Check my project")
        context = json.loads(out)
        self.assertEqual(code, 0, err)
        self.assertEqual(context["request"], "Check my project")
        self.assertEqual(context["skills"][0]["name"], "example")
        self.assertIn("Check output", context["skills"][0]["instructions"])

    def test_duplicate_invalid_and_missing_inputs_fail_without_tracebacks(self):
        self.call("import", str(self.fixture))
        for args in (("import", str(self.fixture)), ("show", "missing"), ("show", "../escape"), ("activate", "missing"), ("context", "example", " ")):
            with self.subTest(args=args):
                code, out, err = self.call(*args)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertTrue(err.startswith("skills: "))
                self.assertNotIn("Traceback", err)

    def test_inspection_commands_report_saved_history(self):
        self.call("import", str(self.fixture))
        for command in ("versions", "history", "revisions", "outcomes"):
            code, out, err = self.call(command, "example")
            self.assertEqual(code, 0, err)
            self.assertIsInstance(json.loads(out), list)
        code, out, err = self.call("history", "example")
        self.assertEqual(json.loads(out)[0]["action"], "import")

    def test_demo_retains_isolated_registry_and_leaves_main_registry_absent(self):
        code, out, err = self.call("demo")
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["mode"], "offline-simulated")
        self.assertEqual(report["activated_version"], "2")
        self.assertEqual(report["restored_version"], "1")
        self.assertEqual(report["actions"], ["import", "activate", "rollback"])
        self.assertFalse((self.project / "outputs/skills").exists())
        self.assertTrue(Path(report["registry"]).is_relative_to(self.project / "outputs"))
        out, err = io.StringIO(), io.StringIO()
        code = main(["--project", report["project"], "list"], stdout=out, stderr=err)
        self.assertEqual(code, 0, err.getvalue())
        self.assertEqual(json.loads(out.getvalue())[0]["name"], "demo-workflow")

    def test_real_module_entrypoint_help_requires_no_registry(self):
        result = subprocess.run([sys.executable, "-m", "senai.skills", "--help"], cwd=self.project, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("import", result.stdout)
        self.assertIn("context", result.stdout)
        self.assertFalse((self.project / "outputs").exists())

    def test_symlinked_outputs_is_rejected(self):
        outside = self.project / "outside"
        outside.mkdir()
        (self.project / "outputs").symlink_to(outside, target_is_directory=True)
        code, out, err = self.call("import", str(self.fixture))
        self.assertEqual(code, 2)
        self.assertIn("symlink", err)
        self.assertEqual(list(outside.iterdir()), [])

    def test_review_cli_delegates_explicit_model_and_outcomes(self):
        self.call("import", str(self.fixture))
        with patch("senai.skills.cli.review_with_codex", return_value=ReviewResult("no_change", "No reusable lesson", None)) as review:
            code, out, err = self.call("review", "example", "--outcome", "id-one", "--outcome", "id-two", "--model", "chosen-model")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["status"], "no_change")
        self.assertEqual(review.call_args.kwargs["outcome_ids"], ["id-one", "id-two"])
        self.assertEqual(review.call_args.kwargs["model"], "chosen-model")
        self.assertEqual(review.call_args.kwargs["project"], self.project)

    def test_review_cli_missing_evidence_fails_without_model_call(self):
        self.call("import", str(self.fixture))
        with patch("senai.codex.run_codex") as run:
            code, out, err = self.call("review", "example", "--outcome", "missing")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotIn("Traceback", err)
        run.assert_not_called()
