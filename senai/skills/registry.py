"""Strict local instruction package registry using only the standard library."""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json

from .outcomes import Check, _decode
from .revisions import Revision
from .validation import Validation
from .activation import Activation
from .errors import SkillError
from .metadata import parse_document as _parse, policy_metadata
from hashlib import sha256
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import uuid


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



def _checked_checks(checks):
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
    return checks


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

            db.execute("CREATE TABLE IF NOT EXISTS validations (id TEXT PRIMARY KEY, revision_id TEXT NOT NULL, base_digest TEXT NOT NULL, candidate_digest TEXT NOT NULL, checks TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('passed', 'failed', 'error')), error TEXT NOT NULL, created_at TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS validations_revision ON validations(revision_id)")
            db.execute("CREATE TABLE IF NOT EXISTS accepted_versions (name TEXT NOT NULL, version TEXT NOT NULL, description TEXT NOT NULL, source TEXT NOT NULL, digest TEXT NOT NULL, directory TEXT NOT NULL, accepted_at TEXT NOT NULL, PRIMARY KEY(name, digest), UNIQUE(name, version))")
            db.execute("CREATE TABLE IF NOT EXISTS activation_history (id TEXT PRIMARY KEY, skill_name TEXT NOT NULL, action TEXT NOT NULL CHECK(action IN ('import', 'activate', 'rollback')), from_digest TEXT NOT NULL, to_digest TEXT NOT NULL, revision_id TEXT NOT NULL, validation_id TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL)")
            # Backfill pre-activation registries without rewriting active packages.
            for row in db.execute("SELECT name, version, description, source, digest, directory FROM skills").fetchall():
                if not db.execute("SELECT 1 FROM accepted_versions WHERE name=? AND digest=?", (row[0], row[4])).fetchone():
                    self._accept(db, row)
                    self._audit(db, row[0], "import", "", row[4], reason="Preserved existing registry skill")

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
                row = (metadata["name"], metadata["version"], metadata["description"], str(source.resolve()), digest, directory)
                db.execute("INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?)", row)
                self._accept(db, row)
                self._audit(db, row[0], "import", "", digest, reason="Validated local import")
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            shutil.rmtree(target, ignore_errors=True)
            raise
        return self.select([metadata["name"]])[0]

    def list(self):
        with self._connect() as db:
            names = [row[0] for row in db.execute("SELECT name FROM skills ORDER BY name")]
        return self.select(names)

    def select(self, names, *, compatibility_check=None):
        selected = []
        with self._connect() as db:
            for name in names:
                _name(name)
                row = db.execute("SELECT name, version, description, source, digest, directory FROM skills WHERE name=?", (name,)).fetchone()
                if row is None:
                    raise SkillError("Skill is not registered: " + name)
                skill = self._skill(row)
                if compatibility_check is not None:
                    metadata, _ = _parse(skill.path.read_bytes())
                    if compatibility_check(metadata) is not True:
                        raise SkillError("Skill is incompatible with the selected execution context: " + name)
                selected.append(skill)
        return selected

    def execute(self, request, names, *, executor, compatibility_check=None):
        if not isinstance(request, str) or not request.strip():
            raise SkillError("Request must be nonempty")
        return executor(request, tuple(self.select(names, compatibility_check=compatibility_check)))

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
        checks = _checked_checks(checks)
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
        original_metadata, _ = _parse(skill.path.read_bytes())
        if policy_metadata(metadata) != policy_metadata(original_metadata):
            raise SkillError("Instruction revision must preserve optional metadata declarations")
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
                if db.execute("SELECT 1 FROM revisions WHERE skill_name=? AND version=?", (name, metadata["version"])).fetchone() or db.execute("SELECT 1 FROM accepted_versions WHERE name=? AND version=?", (name, metadata["version"])).fetchone():
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
        return self._revision(revision_id)

    def _revision_record(self, row):
        if not re.fullmatch(r"[0-9a-f]{32}", row[8]):
            raise SkillError("Invalid stored revision path")
        path = self.root / row[8]
        files, digest = _snapshot(path)
        if digest != row[4]:
            raise SkillError("Revision package content changed")
        metadata, instructions = _parse(files["SKILL.md"])
        if metadata["name"] != row[1] or metadata["version"] != row[2]:
            raise SkillError("Revision metadata does not match recorded identity")
        with self._connect() as db:
            active = db.execute("SELECT digest FROM skills WHERE name=?", (row[1],)).fetchone()
            accepted = db.execute("SELECT 1 FROM accepted_versions WHERE name=? AND digest=?", (row[1], row[4])).fetchone()
        status = "active" if active == (digest,) else "accepted" if accepted else "proposed"
        return Revision(*row[:6], tuple(json.loads(row[6])), row[7], status, path / "SKILL.md", instructions, row[9])

    def revisions(self, name):
        """List proposal snapshots and their proposed/active/accepted status."""
        self.select([name])
        with self._connect() as db:
            rows = db.execute("SELECT id, skill_name, version, base_digest, digest, source, outcome_ids, reason, directory, created_at FROM revisions WHERE skill_name=? ORDER BY rowid", (name,)).fetchall()
        return [self._revision_record(row) for row in rows]

    def _revision(self, revision_id):
        if not isinstance(revision_id, str) or not re.fullmatch(r"[0-9a-f]{32}", revision_id):
            raise SkillError("Invalid revision ID")
        with self._connect() as db:
            row = db.execute("SELECT id, skill_name, version, base_digest, digest, source, outcome_ids, reason, directory, created_at FROM revisions WHERE id=?", (revision_id,)).fetchone()
        if row is None:
            raise SkillError("Revision is not registered")
        return self._revision_record(row)

    def validate_revision(self, revision_id, *, validator):
        """Run an injected checker and retain its result without activating anything.

        Checker receives (base Skill, candidate Revision, tuple[Outcome, ...]).
        Exceptions/empty/malformed checks are persisted as error, never as passed.
        Caller owns checker isolation and must not execute untrusted scripts by default.
        """
        candidate = self._revision(revision_id)
        base = self.select([candidate.skill_name])[0]
        if base.digest != candidate.base_digest:
            raise SkillError("Proposal base is stale")
        recorded = {outcome.id: outcome for outcome in self.outcomes(candidate.skill_name)}
        outcomes = tuple(recorded[value] for value in candidate.outcome_ids)
        checks = ()
        error = ""
        try:
            checks = _checked_checks(validator(base, candidate, outcomes))
            if not checks:
                raise SkillError("Regression checks required")
            status = "passed" if all(check.passed for check in checks) else "failed"
        except Exception:
            checks = ()
            status = "error"
            error = "Validator raised an exception or returned invalid/empty checks"
        # Never attach a pass to different bytes than those presented to the checker.
        current = self._revision(revision_id)
        active = self.select([candidate.skill_name])[0]
        if current.digest != candidate.digest or active.digest != base.digest:
            raise SkillError("Candidate or base changed during validation")
        row = (uuid.uuid4().hex, revision_id, base.digest, candidate.digest, json.dumps([asdict(check) for check in checks]), status, error, datetime.now(timezone.utc).isoformat())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            digest = db.execute("SELECT digest FROM skills WHERE name=?", (candidate.skill_name,)).fetchone()
            if digest != (base.digest,):
                raise SkillError("Proposal base changed before validation was saved")
            db.execute("INSERT INTO validations VALUES (?, ?, ?, ?, ?, ?, ?, ?)", row)
        return self._validation(row)

    @staticmethod
    def _validation(row):
        return Validation(*row[:4], tuple(Check(**value) for value in json.loads(row[4])), *row[5:])

    def validations(self, revision_id):
        """Return all persisted attempts oldest first, including failures/errors."""
        self._revision(revision_id)
        with self._connect() as db:
            rows = db.execute("SELECT id, revision_id, base_digest, candidate_digest, checks, status, error, created_at FROM validations WHERE revision_id=? ORDER BY rowid", (revision_id,)).fetchall()
        return [self._validation(row) for row in rows]

    def _skill(self, row):
        if not re.fullmatch(r"[0-9a-f]{32}", row[5]):
            raise SkillError("Invalid stored package path")
        path = self.root / row[5]
        files, digest = _snapshot(path)
        if digest != row[4]:
            raise SkillError("Registered package content changed")
        metadata, instructions = _parse(files["SKILL.md"])
        if (metadata["name"], metadata["version"], metadata["description"]) != row[:3]:
            raise SkillError("Stored metadata does not match package identity")
        return Skill(*row[:5], "passed", path / "SKILL.md", instructions)

    @staticmethod
    def _accept(db, row):
        db.execute("INSERT OR IGNORE INTO accepted_versions VALUES (?, ?, ?, ?, ?, ?, ?)", (*row, datetime.now(timezone.utc).isoformat()))

    @staticmethod
    def _audit(db, name, action, from_digest, to_digest, *, revision_id="", validation_id="", reason):
        db.execute("INSERT INTO activation_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (uuid.uuid4().hex, name, action, from_digest, to_digest, revision_id, validation_id, reason, datetime.now(timezone.utc).isoformat()))

    def activate_revision(self, revision_id):
        """Explicitly activate only the latest passing, exact-base validation."""
        candidate = self._revision(revision_id)
        base = self.select([candidate.skill_name])[0]
        metadata, _ = _parse(candidate.path.read_bytes())
        row = (candidate.skill_name, candidate.version, metadata["description"], candidate.source, candidate.digest, candidate.path.parent.name)
        skill = self._skill(row)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            active = db.execute("SELECT digest FROM skills WHERE name=?", (candidate.skill_name,)).fetchone()
            if active != (candidate.base_digest,) or base.digest != candidate.base_digest:
                raise SkillError("Proposal base is stale")
            latest = db.execute("SELECT id, base_digest, candidate_digest, status FROM validations WHERE revision_id=? ORDER BY rowid DESC LIMIT 1", (revision_id,)).fetchone()
            if latest is None or latest[1:] != (base.digest, candidate.digest, "passed"):
                raise SkillError("Latest validation must pass for this exact base and candidate")
            self._accept(db, row)
            db.execute("UPDATE skills SET version=?, description=?, source=?, digest=?, directory=? WHERE name=?", (*row[1:], row[0]))
            self._audit(db, row[0], "activate", base.digest, candidate.digest, revision_id=revision_id, validation_id=latest[0], reason=candidate.reason)
        return skill

    def rollback(self, name, *, digest, reason):
        """Restore only a previously accepted, intact package; preserve all evidence."""
        _name(name)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise SkillError("Invalid rollback digest")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 16000:
            raise SkillError("Rollback requires a bounded nonempty reason")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT name, version, description, source, digest, directory FROM accepted_versions WHERE name=? AND digest=?", (name, digest)).fetchone()
            active = db.execute("SELECT digest FROM skills WHERE name=?", (name,)).fetchone()
            if row is None or active is None:
                raise SkillError("Rollback target was never accepted for this skill")
            if active == (digest,):
                raise SkillError("Requested version is already active")
            skill = self._skill(row)
            db.execute("UPDATE skills SET version=?, description=?, source=?, digest=?, directory=? WHERE name=?", (*row[1:], name))
            self._audit(db, name, "rollback", active[0], digest, reason=reason)
        return skill

    def versions(self, name):
        """List accepted versions in first-acceptance order, excluding proposals."""
        _name(name)
        with self._connect() as db:
            rows = db.execute("SELECT name, version, description, source, digest, directory FROM accepted_versions WHERE name=? ORDER BY rowid", (name,)).fetchall()
        if not rows:
            raise SkillError("Skill is not registered: " + name)
        return [self._skill(row) for row in rows]

    def history(self, name):
        """Return import/activation/rollback audit events without loading packages."""
        _name(name)
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM skills WHERE name=?", (name,)).fetchone():
                raise SkillError("Skill is not registered: " + name)
            rows = db.execute("SELECT id, skill_name, action, from_digest, to_digest, revision_id, validation_id, reason, created_at FROM activation_history WHERE skill_name=? ORDER BY rowid", (name,)).fetchall()
        return [Activation(*row) for row in rows]

    def metadata(self, name):
        """Return validated inert declarations; allowed-tools grants no permissions."""
        skill = self.select([name])[0]
        metadata, _ = _parse(skill.path.read_bytes())
        return metadata
