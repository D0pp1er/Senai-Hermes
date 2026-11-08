"""Offline synthetic lifecycle demonstration; never invokes Codex or imported code."""
from pathlib import Path
import tempfile

from senai.workspace import prepare_workspace
from .registry import Registry
from .outcomes import Check


def run_demo(project):
    workspace = prepare_workspace(project)
    parent = workspace / "skills-demo"
    if parent.is_symlink():
        raise ValueError("Demo directory cannot be a symlink")
    parent.mkdir(exist_ok=True)
    demo_project = Path(tempfile.mkdtemp(prefix="run-", dir=parent))
    source = demo_project / "fixture"
    source.mkdir()
    document = "---\nname: demo-workflow\ndescription: Synthetic offline lifecycle fixture\nversion: 1\n---\nCheck the example result.\n"
    (source / "SKILL.md").write_text(document, encoding="utf-8")
    registry = Registry(prepare_workspace(demo_project) / "skills")
    original = registry.import_local(source, demo=True)
    outcome = registry.record_outcome("demo-workflow", digest=original.digest, request="Synthetic boundary example", result="Simulated failure", checks=(Check("synthetic boundary", False, "Fixture deliberately reports a boundary failure"),), correction="Add boundary checks")
    revision = registry.propose_revision("demo-workflow", document=document.replace("version: 1", "version: 2").replace("Check the example result.", "Check the example result and boundary cases."), outcome_ids=(outcome.id,), reason="Demonstrate an evidence-linked proposal")
    validation = registry.validate_revision(revision.id, validator=lambda *args: (Check("synthetic regression", True, "Injected fixture result; no real task/model evaluated"),))
    activated = registry.activate_revision(revision.id)
    restored = registry.rollback("demo-workflow", digest=original.digest, reason="Demonstrate restoration")
    restarted = Registry(registry.root)
    return {
        "mode": "offline-simulated",
        "project": str(demo_project),
        "registry": str(registry.root),
        "skill": original.name,
        "revision_id": revision.id,
        "validation_id": validation.id,
        "activated_version": activated.version,
        "restored_version": restarted.select([restored.name])[0].version,
        "actions": [event.action for event in restarted.history(original.name)],
        "limitation": "Synthetic checks demonstrate storage/control flow, not real skill improvement or Codex integration.",
    }
