"""SQLite storage with transactional namespace capacity and explicit provenance."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from uuid import uuid4


_SECRET = re.compile(
    r"(?:api[ _-]?key|password|passwd|secret|token)\s*[:=]\s*\S+"
    r"|\bbearer\s+\S+|-----BEGIN .*PRIVATE KEY-----"
    r"|\bsk-[a-zA-Z0-9_-]{12,}|\b\d{6,}:[a-zA-Z0-9_-]{20,}", re.I)


def validate_text(value, name="text", limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty and at most {limit} characters")
    if _SECRET.search(value) or any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise ValueError(f"{name} contains disallowed content")
    return value.strip()


@dataclass(frozen=True)
class Namespace:
    project: str
    scope: str

    def __post_init__(self):
        object.__setattr__(self, "project", str(Path(self.project).expanduser().resolve()))
        object.__setattr__(self, "scope", validate_text(self.scope, "scope", 200))


@dataclass(frozen=True)
class Entry:
    id: str
    project: str
    scope: str
    text: str
    provenance: str
    created_at: str
    updated_at: str


class MemoryStore:
    def __init__(self, path, *, max_entries=100, max_chars=20000):
        if type(max_entries) is not int or type(max_chars) is not int or min(max_entries, max_chars) < 1:
            raise ValueError("capacity must be positive integers")
        self.path = Path(path)
        self.max_entries = max_entries
        self.max_chars = max_chars
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported memory schema version")
            db.execute("""CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, scope TEXT NOT NULL,
                text TEXT NOT NULL, provenance TEXT NOT NULL,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                UNIQUE(project, scope, text))""")
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self, namespace):
        with self._db() as db:
            rows = db.execute(
                "SELECT * FROM memory_entries WHERE project=? AND scope=? ORDER BY created_at, id",
                (namespace.project, namespace.scope)).fetchall()
        return [Entry(**dict(row)) for row in rows]

    def _write(self, namespace, text, provenance, entry_id=None):
        text = validate_text(text)
        provenance = validate_text(provenance, "provenance", 500)
        now = datetime.now(timezone.utc).isoformat()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = None
            if entry_id is not None:
                existing = db.execute(
                    "SELECT * FROM memory_entries WHERE id=? AND project=? AND scope=?",
                    (entry_id, namespace.project, namespace.scope)).fetchone()
                if existing is None:
                    raise KeyError(entry_id)
            count, chars = db.execute(
                "SELECT count(*), coalesce(sum(length(text)),0) FROM memory_entries "
                "WHERE project=? AND scope=?", (namespace.project, namespace.scope)).fetchone()
            if count + (existing is None) > self.max_entries or chars - (
                    len(existing["text"]) if existing else 0) + len(text) > self.max_chars:
                raise ValueError("memory capacity exceeded; delete or shorten entries")
            item = Entry(entry_id or uuid4().hex, namespace.project, namespace.scope,
                         text, provenance, existing["created_at"] if existing else now, now)
            try:
                if existing:
                    db.execute("UPDATE memory_entries SET text=?, provenance=?, updated_at=? WHERE id=?",
                               (text, provenance, now, item.id))
                else:
                    db.execute("INSERT INTO memory_entries VALUES (?,?,?,?,?,?,?)",
                               tuple(item.__dict__.values()))
            except sqlite3.IntegrityError:
                raise ValueError("duplicate memory entry") from None
            return item

    def add(self, namespace, text, *, provenance):
        return self._write(namespace, text, provenance)

    def update(self, namespace, entry_id, text, *, provenance):
        return self._write(namespace, text, provenance, entry_id)

    def delete(self, namespace, entry_id):
        with self._db() as db:
            return bool(db.execute(
                "DELETE FROM memory_entries WHERE id=? AND project=? AND scope=?",
                (entry_id, namespace.project, namespace.scope)).rowcount)

    def retrieve(self, namespace, request, *, limit=10):
        if type(limit) is not int or limit < 0:
            raise ValueError("limit must be a nonnegative integer")
        terms = set(re.findall(r"\w+", request.casefold()))
        scored = [(len(terms & set(re.findall(r"\w+", e.text.casefold()))), e)
                  for e in self.list(namespace)]
        return [e for score, e in sorted(scored, key=lambda pair: (-pair[0], pair[1].id))
                if score > 0][:limit]
