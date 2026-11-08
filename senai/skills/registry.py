"""Strict local instruction package registry using only the standard library."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json

from .outcomes import Check, _decode
from .revisions import Revision
from hashlib import sha256
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import uuid


class SkillError(ValueError):
    """An import or selection failed validation."""


@dataclass(frozen=True)
class Skill:
    name: str
    version: str
    description: str
    source: str
    digest: str
    validation: str
    path: Path
    instructions: str


def _name(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) or len(value) > 64:
        raise SkillError("Invalid skill name")
    return value


def _parse(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SkillError("SKILL.md must be UTF-8") from exc
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise SkillError("Missing metadata header")
    metadata = {}
    for index, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if not sep or key not in {"name", "description", "version"} or key in metadata:
            raise SkillError("Unsupported or duplicate metadata")
        value = value.strip()
        if not value or value[0] in "[{>|&*!" or value in {"null", "~"}:
            raise SkillError("Metadata requires scalar text")
        if value[0] in "\"'":
            if len(value) < 2 or value[-1] != value[0]:
                raise SkillError("Unterminated metadata string")
            value = value[1:-1]
        metadata[key] = value
    else:
        raise SkillError("Unterminated metadata header")
    if not metadata.get("description") or not metadata.get("name"):
        raise SkillError("Name and description required")
    _name(metadata["name"])
    version = metadata.setdefault("version", "1")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise SkillError("Invalid version")
    instructions = "".join(lines[index + 1:])
    if not instructions.strip():
        raise SkillError("Instructions required")
    return metadata, instructions


def _snapshot(source):
    if source.is_symlink() or not source.is_dir():
        raise SkillError("Only real local directories supported; archives are not extracted")
    files = {}
    total = 0
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise SkillError("Package symlinks are unsupported")
        if path.is_dir():
            continue
        if not path.is_file():
            raise SkillError("Only regular package files supported")
        relative = path.relative_to(source).as_posix()
        if "\\" in relative or any(part in {".", ".."} for part in Path(relative).parts):
            raise SkillError("Unsafe package path")
        if path.stat().st_size > 1024 * 1024:
            raise SkillError("File exceeds 1 MiB")
        data = path.read_bytes()
        total += len(data)
        if total > 8 * 1024 * 1024 or len(files) >= 256:
            raise SkillError("Package exceeds size/file limit")
        files[relative] = data
    if "SKILL.md" not in files:
        raise SkillError("Package requires SKILL.md")
    return files, _digest(files)


def _digest(files):
    digest = sha256()
    for name, data in sorted(files.items()):
        digest.update(name.encode() + b"\0" + str(len(data)).encode() + b"\0" + data)
    return digest.hexdigest()


class Registry:
    """Caller supplies an isolated outputs/ registry; no global discovery occurs."""

    def __init__(self, root):
        root = Path(root)
        if root.is_symlink():
            raise SkillError("Registry root cannot be a symlink")
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS skills (name TEXT PRIMARY KEY, version TEXT NOT NULL, description TEXT NOT NULL, source TEXT NOT NULL, digest TEXT NOT NULL, directory TEXT NOT NULL)")

            db.execute("CREATE TABLE IF NOT EXISTS outcomes (id TEXT PRIMARY KEY, skill_name TEXT NOT NULL, skill_version TEXT NOT NULL, skill_digest TEXT NOT NULL, request TEXT NOT NULL, result TEXT NOT NULL, checks TEXT NOT NULL, correction TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'unverified')), created_at TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS outcomes_skill ON outcomes(skill_name)")
            db.execute("CREATE TABLE IF NOT EXISTS revisions (id TEXT PRIMARY KEY, skill_name TEXT NOT NULL, version TEXT NOT NULL, base_digest TEXT NOT NULL, digest TEXT NOT NULL, source TEXT NOT NULL, outcome_ids TEXT NOT NULL, reason TEXT NOT NULL, directory TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(skill_name, version))")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.root / "registry.sqlite3")
        try:
            with db:
                yield db
        finally:
            db.close()

    def import_local(self, source):
        source = Path(source).absolute()
        if self.root == source.resolve() or self.root.is_relative_to(source.resolve()):
            raise SkillError("Source cannot contain registry")
        files, digest = _snapshot(source)
        metadata, _ = _parse(files["SKILL.md"])
        directory = uuid.uuid4().hex
        target = self.root / directory
        stage = Path(tempfile.mkdtemp(prefix=".import-", dir=self.root))
        try:
            for name, data in files.items():
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT 1 FROM skills WHERE name=?", (metadata["name"],)).fetchone():
                    raise SkillError("Skill name already registered; explicit revisions required")
                stage.rename(target)
                db.execute("INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?)", (metadata["name"], metadata["version"], metadata["description"], str(source.resolve()), digest, directory))
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)
            raise
        return self.select([metadata["name"]])[0]

    def list(self):
        with self._connect() as db:
            names = [row[0] for row in db.execute("SELECT name FROM skills ORDER BY name")]
        return self.select(names)

    def select(self, names):
        selected = []
        with self._connect() as db:
            for name in names:
                _name(name)
                row = db.execute("SELECT name, version, description, source, digest, directory FROM skills WHERE name=?", (name,)).fetchone()
                if row is None:
                    raise SkillError("Skill is not registered: " + name)
                if not re.fullmatch(r"[0-9a-f]{32}", row[5]):
                    raise SkillError("Invalid stored package path")
                path = self.root / row[5]
                files, digest = _snapshot(path)
                if digest != row[4]:
                    raise SkillError("Registered package content changed")
                _, instructions = _parse(files["SKILL.md"])
                selected.append(Skill(*row[:5], "passed", path / "SKILL.md", instructions))
        return selected

    def execute(self, request, names, *, executor):
        if not isinstance(request, str) or not request.strip():
            raise SkillError("Request must be nonempty")
        return executor(request, tuple(self.select(names)))

    def record_outcome(self, name, *, digest, request, result, checks=(), correction=""):
        """Persist adapter-observed evidence; this never activates a revision.

        Callers must supply independently observed checks. Neither check labels nor
        stored evidence authenticate a caller or prove a model's claims true.
        """
        skill = self.select([name])[0]
        if digest != skill.digest:
            raise SkillError("Outcome must identify the exact selected skill digest")
        for label, value, limit, required in (("request", request, 32000, True), ("result", result, 64000, False), ("correction", correction, 16000, False)):
            if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
                raise SkillError("Invalid outcome " + label)
        try:
            checks = tuple(checks)
        except TypeError as exc:
            raise SkillError("Checks must be an iterable of Check records") from exc
        if len(checks) > 100:
            raise SkillError("At most 100 checks allowed")
        for check in checks:
            if not isinstance(check, Check) or type(check.passed) is not bool:
                raise SkillError("Checks require a Check record and boolean result")
            for value, limit in ((check.name, 200), (check.evidence, 16000)):
                if not isinstance(value, str) or not value.strip() or len(value) > limit:
                    raise SkillError("Each check requires a bounded name and observed evidence")
        status = "unverified" if not checks else "passed" if all(check.passed for check in checks) else "failed"
        row = (uuid.uuid4().hex, name, skill.version, digest, request, result, json.dumps([asdict(check) for check in checks]), correction, status, datetime.now(timezone.utc).isoformat())
        with self._connect() as db:
            db.execute("INSERT INTO outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
        return _decode(row)

    def outcomes(self, name):
        """Return append-only evidence in insertion order for one registered skill."""
        self.select([name])
        with self._connect() as db:
            return [_decode(row) for row in db.execute("SELECT id, skill_name, skill_version, skill_digest, request, result, checks, correction, status, created_at FROM outcomes WHERE skill_name=? ORDER BY rowid", (name,))]

    def propose_revision(self, name, *, document, outcome_ids, reason):
        """Stage an instruction-only revision; supporting files remain unchanged.

        Outcome links must identify observed passed/failed checks for the exact
        base package. Proposals are never loaded by select() or execute().
        """
        skill = self.select([name])[0]
        if not isinstance(document, str) or len(document.encode("utf-8")) > 1024 * 1024:
            raise SkillError("Candidate document must be UTF-8 text up to 1 MiB")
        metadata, instructions = _parse(document.encode("utf-8"))
        if metadata["name"] != name or metadata["version"] == skill.version:
            raise SkillError("Revision requires the same name and a distinct version")
        if instructions.strip() == skill.instructions.strip():
            raise SkillError("Revision must change reusable instructions")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 16000:
            raise SkillError("Revision requires a bounded nonempty reason")
        try:
            outcome_ids = tuple(outcome_ids)
        except TypeError as exc:
            raise SkillError("Outcome IDs must be iterable") from exc
        if not outcome_ids or len(outcome_ids) > 100 or any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value) for value in outcome_ids):
            raise SkillError("Revision requires 1-100 valid outcome IDs")
        if len(set(outcome_ids)) != len(outcome_ids):
            raise SkillError("Duplicate outcome links")
        files, base_digest = _snapshot(skill.path.parent)
        if base_digest != skill.digest:
            raise SkillError("Base package changed during proposal")
        files["SKILL.md"] = document.encode("utf-8")
        if sum(map(len, files.values())) > 8 * 1024 * 1024:
            raise SkillError("Revised package exceeds 8 MiB")
        digest = _digest(files)
        revision_id = uuid.uuid4().hex
        stage = Path(tempfile.mkdtemp(prefix=".revision-", dir=self.root))
        target = self.root / revision_id
        try:
            for relative, data in files.items():
                path = stage / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                active = db.execute("SELECT digest, version FROM skills WHERE name=?", (name,)).fetchone()
                if active != (skill.digest, skill.version):
                    raise SkillError("Active base changed; recreate proposal")
                if db.execute("SELECT 1 FROM revisions WHERE skill_name=? AND version=?", (name, metadata["version"])).fetchone():
                    raise SkillError("Revision version already exists")
                for outcome_id in outcome_ids:
                    row = db.execute("SELECT skill_name, skill_digest, status FROM outcomes WHERE id=?", (outcome_id,)).fetchone()
                    if row is None or row[:2] != (name, skill.digest) or row[2] not in {"passed", "failed"}:
                        raise SkillError("Outcome must be verified and belong to this exact base skill")
                stage.rename(target)
                db.execute("INSERT INTO revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (revision_id, name, metadata["version"], skill.digest, digest, skill.source, json.dumps(outcome_ids), reason, revision_id, datetime.now(timezone.utc).isoformat()))
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)
            raise
        return next(revision for revision in self.revisions(name) if revision.id == revision_id)

    def revisions(self, name):
        """List validated package snapshots for inactive proposals, oldest first."""
        self.select([name])
        with self._connect() as db:
            rows = db.execute("SELECT id, skill_name, version, base_digest, digest, source, outcome_ids, reason, directory, created_at FROM revisions WHERE skill_name=? ORDER BY rowid", (name,)).fetchall()
        revisions = []
        for row in rows:
            if not re.fullmatch(r"[0-9a-f]{32}", row[8]):
                raise SkillError("Invalid stored revision path")
            path = self.root / row[8]
            files, digest = _snapshot(path)
            if digest != row[4]:
                raise SkillError("Revision package content changed")
            metadata, instructions = _parse(files["SKILL.md"])
            if metadata["name"] != name or metadata["version"] != row[2]:
                raise SkillError("Revision metadata does not match recorded identity")
            revisions.append(Revision(*row[:6], tuple(json.loads(row[6])), row[7], "proposed", path / "SKILL.md", instructions, row[9]))
        return revisions
