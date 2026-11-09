import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import io

from senai.skills import Registry
from senai.skills.live_demo import run_live_demo
from senai.skills.cli import main


class LiveDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.calls = []

    def executor(self, prompt, workspace, *, options):
        self.calls.append((prompt, Path(workspace), options))
        self.assertEqual(options.sandbox, "read-only")
        self.assertEqual(options.approval, "never")
        self.assertIsNone(options.resume)
        self.assertFalse(options.last)
        if "\nINPUT_JSON:\n" in prompt:
            payload = json.loads(prompt.split("\nINPUT_JSON:\n", 1)[1])
            document = payload["skill"]["document"].replace("version: 1", "version: " + payload["target_version"])
            document = document.replace("Convert each identifier to an integer, removing leading zeros.", "Preserve each identifier as a string, including all leading zeros.")
            return json.dumps(dict(action="revise", reason="Preserve identifiers after observed zero loss", document=document))
        payload = json.loads(prompt.split("\nTASK_JSON:\n", 1)[1])
        values = [[part.strip() for part in case.split(",")] for case in payload["cases"]]
        if "Convert each identifier to an integer" in payload["instructions"]:
            values = [[int(value) for value in row] for row in values]
        return json.dumps(dict(values=values))

    def test_demo_observes_failures_checks_revision_reuses_and_restores(self):
        stages = []
        report = run_live_demo(self.project, executor=self.executor, emit=stages.append)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["mode"], "live-codex-controlled-fixture")
        self.assertFalse(report["baseline_passed"])
        self.assertEqual(report["validation_status"], "passed")
        self.assertTrue(report["reuse_passed"])
        self.assertEqual(report["restored_version"], "1")
        self.assertEqual(len(self.calls), 4)
        registry = Registry(report["registry"])
        self.assertEqual([event.action for event in registry.history(report["skill"])], ["import", "activate", "rollback"])
        self.assertEqual([outcome.status for outcome in registry.outcomes(report["skill"])], ["failed", "passed"])
        self.assertEqual(registry.select([report["skill"]])[0].version, "1")
        self.assertGreaterEqual(len(stages), 5)
        self.assertTrue(Path(report["report_path"]).is_file())
        self.assertFalse((self.project / "outputs/skills").exists())

    def test_failed_candidate_never_activates_or_runs_heldout_case(self):
        def bad(prompt, workspace, *, options):
            response = self.executor(prompt, workspace, options=options)
            if "\nTASK_JSON:\n" in prompt:
                data = json.loads(response)
                return json.dumps(dict(values=[[int(value) for value in row] for row in data["values"]]))
            return response
        report = run_live_demo(self.project, executor=bad)
        self.assertEqual(report["status"], "validation-failed")
        self.assertEqual(report["validation_status"], "failed")
        registry = Registry(report["registry"])
        self.assertEqual([event.action for event in registry.history(report["skill"])], ["import"])
        self.assertEqual(len(self.calls), 3)

    def test_no_change_reply_stops_without_activation(self):
        def no_change(prompt, workspace, *, options):
            if "\nINPUT_JSON:\n" in prompt:
                return json.dumps(dict(action="no_change", reason="No reliable change", document=""))
            return self.executor(prompt, workspace, options=options)
        report = run_live_demo(self.project, executor=no_change)
        self.assertEqual(report["status"], "no-change")
        self.assertEqual(Registry(report["registry"]).select([report["skill"]])[0].version, "1")

    def test_model_error_is_reported_honestly_with_retained_failure_report(self):
        def broken(*args, **kwargs):
            raise RuntimeError("private error details")
        report = run_live_demo(self.project, executor=broken)
        self.assertEqual(report["status"], "error")
        self.assertNotIn("private error details", json.dumps(report))
        self.assertTrue(Path(report["report_path"]).is_file())

    def test_failed_heldout_reuse_is_recorded_and_rolled_back(self):
        def fail_reuse(prompt, workspace, *, options):
            response = self.executor(prompt, workspace, options=options)
            if "\nTASK_JSON:\n" in prompt and len(self.calls) == 4:
                return json.dumps(dict(values=[[7, 0, 42]]))
            return response
        report = run_live_demo(self.project, executor=fail_reuse)
        self.assertEqual(report["status"], "reuse-failed")
        self.assertFalse(report["reuse_passed"])
        registry = Registry(report["registry"])
        self.assertEqual(registry.select([report["skill"]])[0].version, "1")
        self.assertEqual(registry.outcomes(report["skill"])[-1].status, "failed")

    def test_cli_live_demo_is_explicit_and_streams_stages_to_stderr(self):
        out, err = io.StringIO(), io.StringIO()
        def run(project, *, model, emit):
            emit("Checking real output")
            return dict(status="completed", mode="live-codex-controlled-fixture")
        with patch("senai.skills.cli.run_live_demo", side_effect=run):
            code = main(["--project", str(self.project), "demo", "--live", "--model", "chosen-model"], stdout=out, stderr=err)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "completed")
        self.assertIn("Checking real output", err.getvalue())
