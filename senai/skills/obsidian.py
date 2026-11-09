"""One-way Markdown projection; registry data and personal Obsidian notes stay intact."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

from senai.workspace import prepare_workspace
from .errors import SkillError


@dataclass(frozen=True)
class VaultExport:
    vault_path: str
    index_path: str
    skill_count: int
    generated_files: int
    windows_path: str = ""


_LABELS = {"imported": "Imported", "learned_here": "Learned here", "unknown": "Unknown", "demo": "Demo"}
_MANIFEST = ".senai-manifest.json"


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _line(value, maximum=300):
    value = " ".join(str(value).split())[:maximum]
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("[", "\\[").replace("]", "\\]").replace("|", "\\|").replace("`", "\\`")


def _properties(values):
    return "---\n" + "".join(key + ": " + json.dumps(value, ensure_ascii=False) + "\n" for key, value in values.items()) + "---\n\n"


def _literal(text):
    longest = max((len(value) for value in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return fence + "text\n" + text.rstrip() + "\n" + fence + "\n"


def _state(registry):
    with registry._connect() as db:
        state = [db.execute("SELECT name,version,digest FROM skills ORDER BY name").fetchall(), db.execute("SELECT id,accepted FROM learning_candidates ORDER BY rowid").fetchall()]
        for table in ("origins", "outcomes", "activation_history", "accepted_versions", "revisions", "validations", "learning_validations"):
            state.append(db.execute("SELECT COUNT(*), MAX(rowid) FROM " + table).fetchone())
    return json.dumps(state)


def _history(registry, skill, origin):
    label = _LABELS.get(origin.kind, "Unknown")
    text = _properties(dict(type="skill-history", skill=skill.name, origin=origin.kind))
    text += "# " + skill.name + " — history\n\n[[Generated/Skills/" + skill.name + "|Skill]] · [[Generated/Index|All skills]]\n\n"
    text += "## Origin\n\n- " + label + ": " + _line(origin.reason) + "\n"
    if origin.created_at:
        text += "- Recorded: " + _line(origin.created_at) + "\n"
    if origin.source_run_id:
        text += "- Source run: `" + origin.source_run_id + "`\n- Linked source outcomes: " + str(len(origin.source_outcome_ids)) + "\n"
    if origin.validation_id:
        with registry._connect() as db:
            row = db.execute("SELECT checks,status FROM learning_validations WHERE id=?", (origin.validation_id,)).fetchone()
        if row:
            checks = json.loads(row[0])
            text += "- Acceptance checks: " + str(sum(item["passed"] is True for item in checks)) + "/" + str(len(checks)) + " " + _line(row[1]) + " (declared cases only).\n"
            text += "- Checked: " + ", ".join(_line(item["name"], 100) for item in checks[:5]) + "\n"
    text += "\n## Recent changes\n\n"
    for event in registry.history(skill.name)[-10:]:
        action = "accepted locally authored skill" if event.action == "import" and origin.kind == "learned_here" else event.action
        text += "- " + _line(event.created_at) + " — **" + action + "**: " + _line(event.reason) + "\n"
    proposals = registry.revisions(skill.name)[-6:]
    if proposals:
        text += "\n## Recent instruction revisions\n\n"
        for revision in proposals:
            validations = registry.validations(revision.id)
            verdict = validations[-1].status if validations else "not checked"
            text += "- Version " + _line(revision.version) + " — " + revision.status + ", checks " + verdict + ": " + _line(revision.reason) + "\n"
    text += "\n## Accepted versions\n\n"
    for version in registry.versions(skill.name)[-10:]:
        text += "- " + _line(version.version) + " (`" + version.digest[:12] + "`)" + (" — current" if version.digest == skill.digest else "") + "\n"
    outcomes = registry.outcomes(skill.name)
    counts = {status: sum(outcome.status == status for outcome in outcomes) for status in ("passed", "failed", "unverified")}
    text += "\n## Recorded use\n\n" + str(len(outcomes)) + " outcomes: " + ", ".join(str(counts[key]) + " " + key for key in counts) + ".\n\nPassing checks cover only their recorded cases. Raw requests, model responses and logs are omitted from this view.\n"
    return text


def _pages(registry):
    skills = registry.list()
    index = _properties(dict(type="skill-index", tags=["senai-skills"]))
    index += "# Skills library\n\nSaved procedures from this project's registry. **Learned here** means locally authored and accepted against recorded checks. Imported skills keep their origin after local revision.\n\n"
    index += "| Skill | Origin | Version | Locally revised |\n| --- | --- | --- | --- |\n" if skills else "No saved skills in this registry yet.\n"
    pages = {}
    for skill in skills:
        origin = registry.origin(skill.name)
        label = _LABELS.get(origin.kind, "Unknown")
        index += "| [[Generated/Skills/" + skill.name + "|" + skill.name + "]] | " + label + " | " + _line(skill.version) + " | " + ("Yes" if origin.locally_revised else "No") + " |\n"
        note = _properties(dict(type="skill", origin=origin.kind, source_kind=origin.source_kind, version=skill.version, locally_revised=origin.locally_revised, source=origin.source, digest=skill.digest, tags=["senai-skills", origin.kind.replace("_", "-")]))
        note += "# " + skill.name + "\n\n" + _line(skill.description, 1024) + "\n\n[[Generated/Index|All skills]] · [[Generated/History/" + skill.name + "|History]]\n\n"
        note += "**Origin:** " + label + "\n\n**Source:** " + _line(origin.source, 2048) + "\n\n"
        metadata = registry.metadata(skill.name)
        if "compatibility" in metadata:
            note += "**Declared environment:** " + _line(metadata["compatibility"], 500) + "\n\n"
        note += "## Saved instructions\n\nInstructions are displayed literally; this note does not activate or modify the skill.\n\n" + _literal(skill.instructions)
        pages["Skills/" + skill.name + ".md"] = note
        pages["History/" + skill.name + ".md"] = _history(registry, skill, origin)
    index += "\n---\nRefresh this one-way view with the export-obsidian command. Keep personal notes outside Generated, or in separate unowned files. Registry data remains authoritative.\n"
    pages["Index.md"] = index
    return skills, pages


def _previous(target, registry, seed=None):
    if not target.exists():
        return {}
    for item in (target, *target.rglob("*")):
        if item.is_symlink() or not (item.is_file() or item.is_dir()):
            raise SkillError("Generated vault content must contain only real files/directories")
    manifest_path = target / _MANIFEST
    if not manifest_path.exists() and seed is not None:
        # Adopt only notes that exactly match a prior verified project export.
        manifest = dict(schema_version=1, registry=str(registry.root), files=seed)
    else:
        if not manifest_path.is_file() or manifest_path.stat().st_size > 1024 * 1024:
            raise SkillError("Existing Generated folder is not owned by this exporter")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise SkillError("Invalid export ownership manifest") from exc
    if not isinstance(manifest, dict) or manifest.get("registry") != str(registry.root) or manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
        raise SkillError("Export ownership/source does not match this registry")
    for name, digest in manifest["files"].items():
        if not re.fullmatch(r"Index\.md|(?:Skills|History)/[a-z0-9]+(?:-[a-z0-9]+)*\.md", name) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise SkillError("Unsafe export manifest entry")
        path = target / name
        if not path.is_file() or _hash(path.read_bytes()) != digest:
            raise SkillError("Generated note was edited or removed; preserve/move edits before refreshing: " + name)
    return manifest["files"]


def _swap(stage, target):
    backup = target.parent / (".senai-backup-" + uuid.uuid4().hex)
    moved = False
    try:
        if target.exists():
            os.replace(target, backup)
            moved = True
        os.replace(stage, target)
    except BaseException:
        if moved and not target.exists():
            os.replace(backup, target)
        raise
    if moved:
        shutil.rmtree(backup, ignore_errors=True)


def _destination(value):
    text = str(value)
    windows_path = ""
    if re.match(r"^[A-Za-z]:[\\/]", text):
        windows_path = text
        if os.name != "nt":
            try:
                translated = subprocess.run(["wslpath", "-u", text], capture_output=True, text=True, check=True, timeout=10)
            except (OSError, subprocess.SubprocessError) as exc:
                raise SkillError("Cannot translate Windows destination; use its mounted /mnt/ path") from exc
            text = translated.stdout.strip()
            if not text.startswith("/"):
                raise SkillError("Windows destination did not translate to an absolute WSL path")
    path = Path(text).expanduser().absolute()
    if not windows_path:
        match = re.match(r"^/mnt/([A-Za-z])/(.+)$", str(path))
        if match:
            windows_path = match[1].upper() + ":\\" + match[2].replace("/", "\\")
    return path, windows_path


def export_vault(registry, *, project, destination=None):
    """Refresh only owned notes; return paths for Open folder as vault in Obsidian."""
    project = Path(project).expanduser().resolve()
    outputs = project / "outputs"
    if outputs.is_symlink() or not registry.root.is_relative_to(outputs.resolve()) or registry.root == outputs.resolve():
        raise SkillError("Export source must belong to this project's real outputs directory")
    outputs = prepare_workspace(project)
    default_vault = outputs / "skills-vault"
    vault, windows_path = (default_vault, "") if destination is None else _destination(destination)
    if vault.resolve() == Path(vault.anchor) or vault.resolve().is_relative_to(registry.root) or registry.root.is_relative_to(vault.resolve()):
        raise SkillError("Vault destination cannot overlap the registry or filesystem root")
    target = vault / "Generated"
    if vault.is_symlink() or target.is_symlink() or (vault / "Index.md").is_symlink():
        raise SkillError("Vault/export paths cannot be symlinks")
    vault.mkdir(parents=True, exist_ok=True)
    backups = list(vault.glob(".senai-backup-*"))
    if not target.exists() and backups:
        if len(backups) != 1 or not backups[0].is_dir() or backups[0].is_symlink():
            raise SkillError("Ambiguous interrupted export backup; inspect before refresh")
        _previous(backups[0], registry)
        os.replace(backups[0], target)
    seed = None
    if destination is not None and target.exists() and not (target / _MANIFEST).exists() and default_vault.resolve() != vault.resolve():
        source = default_vault / "Generated"
        if source.exists() and not default_vault.is_symlink():
            seed = _previous(source, registry)
    previous = _previous(target, registry, seed=seed)
    initial = _state(registry)
    skills, pages = _pages(registry)
    if _state(registry) != initial:
        raise SkillError("Registry changed during export; retry with a consistent state")
    stage = Path(tempfile.mkdtemp(prefix=".senai-stage-", dir=vault))
    try:
        if target.exists():
            shutil.copytree(target, stage, dirs_exist_ok=True)
        for name in previous:
            (stage / name).unlink()
        for name, text in pages.items():
            output = stage / name
            if output.exists():
                raise SkillError("New generated note would overwrite an unowned note: " + name)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
        manifest = dict(schema_version=1, registry=str(registry.root), exported_at=datetime.now(timezone.utc).isoformat(), files={name: _hash(text.encode("utf-8")) for name, text in pages.items()})
        (stage / _MANIFEST).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        _swap(stage, target)
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    index = vault / "Index.md"
    if not index.exists():
        index.write_text("# Skills\n\nOpen [[Generated/Index|Skills library]] to view imported and learned procedures, sources and histories.\n\nPersonal notes can be kept beside this note; generated instruction/history pages are refreshed separately.\n", encoding="utf-8")
    return VaultExport(str(vault), str(target / "Index.md"), len(skills), len(pages), windows_path)
