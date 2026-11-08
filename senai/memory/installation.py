"""Single-owner memory shared across projects in one explicitly selected installation."""
from pathlib import Path

from senai.workspace import prepare_workspace
from .profiles import ProfileStore, _safe_path
from .session import start_session
from .store import MemoryStore, Namespace, validate_text


class _InstallationProfiles(ProfileStore):
    """Reuse reviewed writes with a flat, installation-local three-file layout."""

    def _path(self, name):
        if name not in ("SOUL.md", "USER.md", "MEMORY.md"):
            raise ValueError("unknown profile filename")
        path = self.root / name
        _safe_path(path)
        return path


class InstallationMemory:
    """One owner per repo/installation. Caller explicitly selects the installation."""

    def __init__(self, installation):
        self.installation = Path(installation).expanduser().resolve()
        workspace = prepare_workspace(self.installation)
        self.directory = workspace / ".senai-memory"
        _safe_path(self.directory)
        self.directory.mkdir(mode=0o700, exist_ok=True)
        self.namespace = Namespace(self.installation, "installation")
        path = self.directory / "memory.db"
        _safe_path(path)
        self.store = MemoryStore(path)
        path.chmod(0o600)
        self.profiles = _InstallationProfiles(self.directory, self.namespace, user_id="owner")

    def snapshot(self, request, *, max_chars=8000):
        """Fresh installation snapshot always includes the single owner's USER.md."""
        return start_session(self.profiles, self.store, request,
                             include_user=True, max_chars=max_chars)

    def remember(self, name, text, *, user_requested=False, noteworthy=False, verified=False):
        """Append a validated fact on user request or trusted noteworthy-event judgment.

        Flags come from the authorized application, never directly from untrusted output.
        USER.md holds preferences/habits/likes/dislikes/significant choices; MEMORY.md
        holds core events. No automatic classifier or model is invoked here.
        """
        for flag in (user_requested, noteworthy, verified):
            if type(flag) is not bool:
                raise ValueError("learning decisions must be boolean")
        if name not in ("USER.md", "MEMORY.md"):
            raise ValueError("learning may update USER.md or MEMORY.md only")
        if not user_requested and not (noteworthy and verified):
            raise ValueError("a user request or verified noteworthy event is required")
        block = "- " + validate_text(text, "remembered fact", 4000)
        before = self.profiles.read(name)
        if block in before.text.split("\n\n"):
            return before
        combined = before.text + "\n\n" + block if before.text else block
        proposal = self.profiles.propose(
            name, combined, origin="human" if user_requested else "outcome", verified=verified)
        # Tie approval to the same content used to build the append, including racing writers.
        if proposal.before_revision != before.revision:
            from .profiles import ConflictError
            raise ConflictError("profile changed; retry the learning decision")
        return self.profiles.apply(proposal, approved=True)
