"""Controlled live Codex demo with deterministic checks, retained artifacts and rollback."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import uuid

from senai.options import CodexOptions
from senai.workspace import prepare_workspace
from .errors import SkillError
from .outcomes import Check
from .registry import Registry
from .review import review_with_codex


_BASE_DOCUMENT = """---
name: csv-identifiers
description: Normalize CSV identifier batches in a controlled demonstration
version: 1
---
Split each CSV batch on commas and strip surrounding whitespace.
Convert each identifier to an integer, removing leading zeros.
Return the batches as the values array in the requested JSON object.
"""

_SCHEMA = {
    "type": "object",
    "properties": {"values": {"type": "array", "items": {"type": "array", "items": {"anyOf": [{"type": "string"}, {"type": "number"}]}}}},
    "required": ["values"],
    "additionalProperties": False,
}


def _evaluate(package, cases, project, *, executor, model):
    workspace = prepare_workspace(project) / "evaluations" / uuid.uuid4().hex
    workspace.mkdir(parents=True)
    schema = workspace / "response-schema.json"
    schema.write_text(json.dumps(_SCHEMA), encoding="utf-8")
    payload = {"instructions": package.instructions, "cases": cases}
    prompt = "Normalize these CSV identifier batches using the selected skill procedure. Return only a JSON object with a values array of arrays, preserving batch order. Do not use tools or modify files.\nTASK_JSON:\n" + json.dumps(payload)
    (workspace / "prompt.txt").write_text(prompt, encoding="utf-8")
    options = CodexOptions(model=model, sandbox="read-only", approval="never", skip_git_repo_check=True, extra_args=("--output-schema", str(schema)))
    response = executor(prompt, workspace, options=options)
    if not isinstance(response, str) or len(response) > 64000:
        raise SkillError("Task returned an invalid or excessive response")
    (workspace / "response.json").write_text(response, encoding="utf-8")
    try:
        data = json.loads(response)
    except ValueError as exc:
        raise SkillError("Task response was not JSON") from exc
    if not isinstance(data, dict) or set(data) != {"values"} or not isinstance(data["values"], list):
        raise SkillError("Task response requires a values array")
    actual = data["values"]
    expected = [[part.strip() for part in case.split(",")] for case in cases]
    checks = tuple(Check("case-" + str(index + 1), index < len(actual) and actual[index] == value, json.dumps({"input": cases[index], "expected": value, "actual": actual[index] if index < len(actual) else None})) for index, value in enumerate(expected))
    checks += (Check("batch-count", len(actual) == len(expected), "Expected %d batches; got %d" % (len(expected), len(actual))),)
    (workspace / "checks.json").write_text(json.dumps([asdict(check) for check in checks], indent=2), encoding="utf-8")
    return response, checks, str(workspace)


def run_live_demo(project, *, executor=None, model=None, emit=None):
    """Four explicit Codex calls at most; injected executor is supported for offline QA.

    The baseline is deliberately lossy and checks encode a known fixture contract.
    This demonstrates one actual correction/reuse, not general learning quality.
    """
    from senai.codex import run_codex

    runner = run_codex if executor is None else executor
    workspace = prepare_workspace(project)
    parent = workspace / "skills-live-demo"
    if parent.is_symlink():
        raise SkillError("Live demo directory cannot be a symlink")
    parent.mkdir(exist_ok=True)
    demo_project = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    source = demo_project / "fixture" / "csv-identifiers"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text(_BASE_DOCUMENT, encoding="utf-8")
    registry = Registry(prepare_workspace(demo_project) / "skills")
    original = registry.import_local(source)
    report_path = demo_project / "outputs" / "report.json"
    report = {"mode": "live-codex-controlled-fixture", "executor_kind": "native-codex" if executor is None else "injected", "status": "running", "project": str(demo_project), "registry": str(registry.root), "skill": original.name, "report_path": str(report_path), "stages": [], "artifacts": [], "limitation": "Deliberately lossy imported fixture and known checks; demonstrates a controlled correction, not general autonomous improvement. Injected executors may be used in offline tests."}

    def stage(message):
        report["stages"].append(message)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        if emit:
            emit(message)

    try:
        stage("1/6 Imported CSV identifier skill; running baseline with Codex")
        response, checks, artifact = _evaluate(original, ["001,002", "10,20"], demo_project, executor=runner, model=model)
        report["artifacts"].append(artifact)
        report["baseline_passed"] = all(check.passed for check in checks)
        outcome = registry.record_outcome(original.name, digest=original.digest, request="Normalize CSV identifiers without losing their original text", result=response, checks=checks, correction="Preserve identifiers as strings, including leading zeros")
        report["baseline_outcome_id"] = outcome.id
        if report["baseline_passed"]:
            report["status"] = "baseline-already-passed"
            stage("Baseline already passed; no improvement is claimed")
        else:
            stage("2/6 Independent checks detected identifier loss; asking Codex for a proposal")
            review = review_with_codex(registry, original.name, outcome_ids=(outcome.id,), project=demo_project, model=model, executor=runner)
            report["review_status"] = review.status
            if review.revision is None:
                report["status"] = "no-change"
                stage("Codex proposed no change; active skill remains version 1")
            else:
                candidate = review.revision
                report["revision_id"] = candidate.id
                stage("3/6 Proposal is inactive; checking Codex output on regression batches")
                def validator(base, revision, outcomes):
                    _, checks, artifact = _evaluate(revision, ["001,002", "10,20", " 003 , 9 "], demo_project, executor=runner, model=model)
                    report["artifacts"].append(artifact)
                    return checks
                validation = registry.validate_revision(candidate.id, validator=validator)
                report["validation_status"] = validation.status
                report["validation_id"] = validation.id
                if validation.status != "passed":
                    report["status"] = "validation-failed"
                    stage("Regression checks did not pass; proposal was not activated")
                else:
                    stage("4/6 Regression checks passed; activating the checked revision")
                    active = registry.activate_revision(candidate.id)
                    report["activated_version"] = active.version
                    try:
                        stage("5/6 Reopened registry; reusing active instructions on a held-out batch")
                        restarted = Registry(registry.root)
                        selected = restarted.select([original.name])[0]
                        response, checks, artifact = _evaluate(selected, ["007,000,42"], demo_project, executor=runner, model=model)
                        report["artifacts"].append(artifact)
                        report["reuse_passed"] = all(check.passed for check in checks)
                        reuse = restarted.record_outcome(selected.name, digest=selected.digest, request="Normalize a held-out CSV identifier batch", result=response, checks=checks)
                        report["reuse_outcome_id"] = reuse.id
                        report["status"] = "completed" if report["reuse_passed"] else "reuse-failed"
                    finally:
                        restored = registry.rollback(original.name, digest=original.digest, reason="Restore controlled demo baseline after reuse check")
                        report["restored_version"] = restored.version
                        stage("6/6 Restored original version; retained check results and update history")
    except Exception:
        report["status"] = "error"
        report["error"] = "Demo execution failed; no success is claimed. Inspect retained stage/check artifacts."
    report["actions"] = [event.action for event in registry.history(original.name)]
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
