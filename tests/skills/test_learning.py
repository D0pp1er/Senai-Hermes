import io
import json
from unittest.mock import patch
from senai.skills.cli import main
import tempfile
import unittest
from pathlib import Path

from senai.skills import Check, Registry, SkillError
from senai.skills.run import run_request
from senai.skills.learning import check_with_codex


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        source = self.project / "source"
        source.mkdir()
        (source / "SKILL.md").write_text("---\nname: author\ndescription: Author instruction packages\n---\nWrite focused instructions.\n")
        self.registry = Registry(self.project / "outputs/skills")
        self.author = self.registry.import_local(source)
        def executor(prompt, workspace, *, options):
            path = Path(workspace) / "new-skill"
            path.mkdir()
            (path / "SKILL.md").write_text("---\nname: new-skill\ndescription: Preserve CSV identifiers\nversion: 1\n---\nKeep identifiers as strings including leading zeros.\n")
            return "Created package"
        self.run = run_request(self.registry, "Create a reusable skill", ["author"], project=self.project, executor=executor, checker=lambda response, workspace: (Check("artifact", (workspace / "new-skill/SKILL.md").is_file(), "Observed package"),))

    def stage(self):
        return self.registry.stage_learning(self.run.id, path="new-skill", reason="Reuse the locally authored identifier workflow")

    def test_stage_preserves_source_run_and_remains_inactive(self):
        candidate = self.stage()
        self.assertEqual(candidate.name, "new-skill")
        self.assertEqual(candidate.source_run_id, self.run.id)
        self.assertEqual(candidate.source_outcome_ids, self.run.outcome_ids)
        self.assertEqual(candidate.status, "proposed")
        self.assertEqual([skill.name for skill in self.registry.list()], ["author"])
        self.assertEqual(Registry(self.registry.root).learning_candidates(), [candidate])

    def test_checked_acceptance_preserves_origin_and_history_after_restart(self):
        candidate = self.stage()
        validation = self.registry.check_learning(candidate.id, validator=lambda candidate: (Check("leading zeros", True, "Observed [001,002] preserved"),))
        learned = self.registry.accept_learning(candidate.id)
        restarted = Registry(self.registry.root)
        origin = restarted.origin("new-skill")
        self.assertEqual(origin.kind, "learned_here")
        self.assertEqual(origin.source_run_id, self.run.id)
        self.assertEqual(origin.validation_id, validation.id)
        self.assertEqual(origin.source_outcome_ids, self.run.outcome_ids)
        self.assertEqual(restarted.select(["new-skill"]), [learned])
        self.assertEqual(restarted.learning_candidates()[0].status, "accepted")
        self.assertEqual(restarted.learning_checks(candidate.id), [validation])
        self.assertIn(candidate.reason, restarted.history("new-skill")[0].reason)

    def test_no_checks_failed_checks_and_later_errors_cannot_activate(self):
        candidate = self.stage()
        with self.assertRaises(SkillError):
            self.registry.accept_learning(candidate.id)
        for checks in ((Check("case", False, "Observed failure"),), ()):
            self.registry.check_learning(candidate.id, validator=lambda candidate: checks)
            with self.assertRaises(SkillError):
                self.registry.accept_learning(candidate.id)
        self.registry.check_learning(candidate.id, validator=lambda candidate: (Check("case", True, "Observed pass"),))
        self.registry.check_learning(candidate.id, validator=lambda candidate: ())
        with self.assertRaises(SkillError):
            self.registry.accept_learning(candidate.id)
        self.assertEqual([skill.name for skill in self.registry.list()], ["author"])

    def test_candidate_tampering_after_pass_cannot_be_accepted(self):
        candidate = self.stage()
        self.registry.check_learning(candidate.id, validator=lambda candidate: (Check("case", True, "Observed pass"),))
        candidate.path.write_text("Tampered")
        with self.assertRaises(SkillError):
            self.registry.accept_learning(candidate.id)
        self.assertEqual([skill.name for skill in self.registry.list()], ["author"])

    def test_path_escape_unknown_run_and_unverified_source_are_rejected(self):
        for run_id, path in (("missing", "new-skill"), (self.run.id, "../new-skill"), (self.run.id, "/absolute")):
            with self.assertRaises(SkillError):
                self.registry.stage_learning(run_id, path=path, reason="Reuse")
        report = Path(self.run.report_path)
        data = json.loads(report.read_text())
        data["verification"] = "unverified"
        report.write_text(json.dumps(data))
        with self.assertRaises(SkillError):
            self.stage()
        self.assertEqual(self.registry.learning_candidates(), [])

    def test_conflicting_acceptance_keeps_existing_skill_and_candidate_inactive(self):
        candidate = self.stage()
        self.registry.check_learning(candidate.id, validator=lambda candidate: (Check("case", True, "Observed pass"),))
        existing = self.registry.import_local(Path(self.run.workspace) / "new-skill")
        with self.assertRaises(SkillError):
            self.registry.accept_learning(candidate.id)
        self.assertEqual(self.registry.select(["new-skill"]), [existing])
        self.assertEqual(self.registry.origin("new-skill").kind, "imported")
        self.assertEqual(self.registry.learning_candidates()[0].status, "proposed")

    def test_imported_revision_keeps_imported_origin(self):
        origin = self.registry.origin("author")
        self.assertEqual(origin.kind, "imported")
        self.assertFalse(origin.locally_revised)
        outcome = self.registry.record_outcome("author", digest=self.author.digest, request="Try", result="Wrong", checks=(Check("case", False, "Observed error"),))
        revision = self.registry.propose_revision("author", document=self.author.path.read_text().replace("description:", "version: 2\ndescription:").replace("Write focused instructions.", "Write focused checked instructions."), outcome_ids=(outcome.id,), reason="Fix error")
        self.registry.validate_revision(revision.id, validator=lambda *args: (Check("case", True, "Observed pass"),))
        self.registry.activate_revision(revision.id)
        self.assertEqual(self.registry.origin("author").kind, "imported")
        self.assertTrue(self.registry.origin("author").locally_revised)

    def test_codex_checks_compare_actual_json_not_model_claims(self):
        candidate = self.stage()
        calls = []
        def executor(prompt, workspace, *, options):
            self.assertEqual(options.sandbox, "read-only")
            calls.append(prompt)
            return '["001", "002"]'
        cases = [dict(name="leading zeros", request="Normalize 001,002; return only JSON array", expected_json=["001", "002"])]
        validation = check_with_codex(self.registry, candidate.id, cases=cases, project=self.project, executor=executor)
        self.assertEqual(validation.status, "passed")
        self.assertEqual(len(calls), 1)
        failed = check_with_codex(self.registry, candidate.id, cases=cases, project=self.project, executor=lambda *args, **kwargs: "Everything passed!")
        self.assertEqual(failed.status, "failed")

    def test_old_origin_backfill_does_not_invent_learned_status(self):
        with self.registry._connect() as db:
            db.execute("DROP TABLE origins")
        migrated = Registry(self.registry.root)
        self.assertEqual(migrated.origin("author").kind, "imported")
        self.assertEqual(len(migrated.list()), 1)

    def test_cli_stage_check_accept_and_origin_listing(self):
        def call(*args):
            out, err = io.StringIO(), io.StringIO()
            code = main(["--project", str(self.project), *args], stdout=out, stderr=err)
            self.assertEqual(code, 0, err.getvalue())
            return json.loads(out.getvalue())
        candidate = call("learn", "--run", self.run.id, "--path", "new-skill", "--reason", "Reuse the locally authored workflow")
        cases = self.project / "cases.json"
        cases.write_text(json.dumps([dict(name="leading zeros", request="Return identifiers as JSON", expected_json=["001", "002"])]))
        with patch("senai.codex.run_codex", return_value='["001", "002"]'):
            validation = call("check-learning", candidate["id"], "--cases", str(cases))
        self.assertEqual(validation["status"], "passed")
        accepted = call("accept-learning", candidate["id"])
        self.assertEqual(accepted["origin"]["kind"], "learned_here")
        self.assertEqual(call("origin", "new-skill")["source_run_id"], self.run.id)
        kinds = {skill["name"]: skill["origin"] for skill in call("list")}
        self.assertEqual(kinds, {"author": "imported", "new-skill": "learned_here"})

    def test_cli_failed_learning_check_returns_failure_without_activation(self):
        candidate = self.stage()
        cases = self.project / "cases.json"
        cases.write_text(json.dumps([dict(name="leading zeros", request="Return identifiers as JSON", expected_json=["001", "002"])]))
        out, err = io.StringIO(), io.StringIO()
        with patch("senai.codex.run_codex", return_value='[1, 2]'):
            code = main(["--project", str(self.project), "check-learning", candidate.id, "--cases", str(cases)], stdout=out, stderr=err)
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())["status"], "failed")
        with self.assertRaises(SkillError):
            self.registry.accept_learning(candidate.id)
