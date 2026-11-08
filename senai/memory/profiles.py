"""Scoped curated files with reviewed, atomic updates (WSL/POSIX)."""
from contextlib import contextmanager
from dataclasses import dataclass
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from .store import validate_text


_NAMES = ("SOUL.md", "USER.md", "MEMORY.md")
_MISSING = "missing"


class ConflictError(ValueError):
    """The reviewed file revision no longer matches disk."""


@dataclass(frozen=True)
class ProfileDocument:
    name: str
    path: Path
    text: str
    revision: str


@dataclass(frozen=True)
class ProfileProposal:
    name: str
    text: str
    origin: str
    verified: bool
    owner: str
    before_revision: str
    diff: str


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _safe_path(path):
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("profile paths must not contain symlinks")


def _text(text):
    if not isinstance(text, str):
        raise ValueError("profile text must be a string")
    if text == "":
        return text
    return validate_text(text, "profile text", 4000)


class ProfileStore:
    """Caller supplies authorized project/scope/user; no identity inference."""

    def __init__(self, root, namespace, *, user_id=None):
        self.root = Path(root).absolute()
        _safe_path(self.root)
        self.namespace = namespace
        self.user_id = None if user_id is None else validate_text(user_id, "user_id", 200)
        key = json.dumps([namespace.project, namespace.scope], ensure_ascii=True).encode()
        self.directory = self.root / _digest(key)
        self.owner = _digest(json.dumps(
            [str(self.root), namespace.project, namespace.scope, self.user_id]).encode())

    def _path(self, name):
        if name not in _NAMES:
            raise ValueError("unknown profile filename")
        if name == "USER.md":
            if self.user_id is None:
                raise ValueError("USER.md requires an authorized user identity")
            path = self.directory / "users" / _digest(self.user_id.encode()) / name
        else:
            path = self.directory / name
        _safe_path(path)
        return path

    def read(self, name):
        path = self._path(name)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return ProfileDocument(name, path, "", _MISSING)
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("profile must be a regular file")
            data = stream.read(16001)
        if len(data) > 16000:
            raise ValueError("profile exceeds byte limit")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("profile must use UTF-8") from None
        if text:
            _text(text)
        return ProfileDocument(name, path, text, _digest(data))

    def propose(self, name, text, *, origin="human", verified=False):
        if type(verified) is not bool or (origin == "outcome" and not verified):
            raise ValueError("outcome proposals require verified=True")
        if origin not in ("human", "outcome") or (name == "SOUL.md" and origin != "human"):
            raise ValueError("SOUL.md requires explicit human authorship")
        text = _text(text)
        before = self.read(name)
        diff = "".join(difflib.unified_diff(
            before.text.splitlines(keepends=True), text.splitlines(keepends=True),
            fromfile=name + ":before", tofile=name + ":after"))
        return ProfileProposal(name, text, origin, verified, self.owner, before.revision, diff)

    @contextmanager
    def _lock(self):
        _safe_path(self.root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.root / ".profiles.lock"
        _safe_path(path)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("profile lock must be a regular file")
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def apply(self, proposal, *, approved):
        if approved is not True:
            raise ValueError("explicit boolean approval required")
        if type(proposal.verified) is not bool or (
                proposal.origin == "outcome" and not proposal.verified):
            raise ValueError("outcome proposals require verified=True")
        if proposal.owner != self.owner:
            raise ValueError("proposal belongs to a different profile owner")
        if proposal.origin not in ("human", "outcome") or (
                proposal.name == "SOUL.md" and proposal.origin != "human"):
            raise ValueError("SOUL.md requires explicit human authorship")
        text = _text(proposal.text)
        with self._lock():
            current = self.read(proposal.name)
            if current.revision != proposal.before_revision:
                raise ConflictError("profile changed; review a new proposal")
            path = current.path
            if text == "":
                path.unlink(missing_ok=True)
            else:
                _safe_path(path)
                path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=".profile-", dir=path.parent)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(text.encode("utf-8"))
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.replace(temporary, path)
                finally:
                    Path(temporary).unlink(missing_ok=True)
            return self.read(proposal.name)
