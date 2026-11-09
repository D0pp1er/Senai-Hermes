"""Coordinator: explicit installation memory and frozen native-session snapshots."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sqlite3
import uuid

from .memory import InstallationMemory, SessionSnapshot, execute_session
from .options import CodexOptions
from .memory.store import validate_text


@dataclass(frozen=True)
class LearningDecision:
    """Assertions supplied by trusted app validation, never parsed from model output."""
    name: str
    text: str
    user_requested: bool = False
    noteworthy: bool = False
    verified: bool = False
    confirmed: bool = False
    kind: str | None = None
    source: str | None = None
    significant: bool = False


class InstallationRuntime:
    def __init__(self, installation):
        self.memory = InstallationMemory(installation)
        self.path = self.memory.directory / "native-snapshots.sqlite3"
        if self.path.is_symlink():
            raise ValueError("Native snapshot database cannot be symlinked.")
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS snapshots (session TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        self.path.chmod(0o600)

    def _load(self, session):
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT payload FROM snapshots WHERE session=?", (session,)).fetchone()
        if row is None:
            raise ValueError("No frozen memory snapshot for this session. Start a fresh session with this installation; the existing session was not changed.")
        data = json.loads(row[0])
        data["revisions"] = tuple(tuple(item) for item in data["revisions"])
        snapshot = SessionSnapshot(**data)
        if snapshot.project != self.memory.namespace.project or snapshot.scope != "installation":
            raise ValueError("Snapshot belongs to a different installation.")
        return snapshot

    def _bind(self, session, snapshot):
        if not isinstance(session, str):
            raise ValueError("Codex did not return a valid native session ID.")
        session = str(uuid.UUID(session))
        payload = json.dumps(asdict(snapshot), sort_keys=True)
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT OR IGNORE INTO snapshots(session,payload) VALUES (?,?)", (session, payload))
            existing = db.execute("SELECT payload FROM snapshots WHERE session=?", (session,)).fetchone()[0]
            if existing != payload:
                raise ValueError("Native session already has a different frozen snapshot.")

    @staticmethod
    def requested_learning(request):
        # Telegram's trusted presentation wrapper keeps the original user message here.
        request = request.rsplit("\n\nUser message:\n", 1)[-1].strip()
        if re.match(r"remember my (preference|habit|like|dislike|choice):", request, re.IGNORECASE):
            return None
        if re.match(r"remember in SOUL\.md:", request, re.IGNORECASE):
            raise ValueError("SOUL.md is human-controlled; automatic learning cannot update it.")
        match = re.fullmatch(r"remember in (USER\.md|MEMORY\.md):\s*(.+)", request,
                             flags=re.IGNORECASE | re.DOTALL)
        if match:
            name = "USER.md" if match[1].upper() == "USER.MD" else "MEMORY.md"
            return LearningDecision(name, match[2].strip(), user_requested=True)
        match = re.fullmatch(r"remember (?:that )?(.+)", request,
                             flags=re.IGNORECASE | re.DOTALL)
        if match:
            return LearningDecision("MEMORY.md", match[1].strip(), user_requested=True)
        return None

    def execute(self, request, workspace, *, executor, options=None, skills=(),
                learning=None, confirmation=None, **streams):
        requested = self.requested_learning(request)
        if requested is not None:
            validate_text(requested.text, "remembered fact", 4000)
        options = options or CodexOptions()
        if options.last:
            raise ValueError("Installation memory requires an exact --resume session ID, not --last.")
        if "--ephemeral" in options.extra_args:
            raise ValueError("Installation memory requires a persistent native session.")
        snapshot = self._load(options.resume) if options.resume else self.memory.snapshot(request)
        observed = []
        def bind(session):
            if options.resume and session != options.resume:
                raise ValueError("Codex returned a different session; memory mapping was preserved.")
            self._bind(session, snapshot)
            observed.append(session)
        def managed_executor(prompt, workspace, **kwargs):
            prompt = ("Installation profiles are managed by the application. Do not directly edit "
                      "SOUL.md, USER.md, MEMORY.md or memory databases. SOUL.md changes require "
                      "explicit human editing; return your answer and let the app save approved facts.\n\n"
                      + prompt)
            return executor(prompt, workspace, **kwargs)
        response = execute_session(request, workspace, snapshot=snapshot, executor=managed_executor,
                                   skills=skills, options=options, session_callback=bind, **streams)
        if not observed:
            raise RuntimeError("Codex did not report a native session; no learning was saved.")
        decisions = []
        if requested is not None:
            decisions.append(requested)
        if learning is None:
            from .outcome_learning import OutcomeLearning
            learning = OutcomeLearning(self.memory, confirm=confirmation)
        decisions.extend(learning(request, response, Path(workspace)))
        # Validate the whole batch before applying any personal fact.
        for decision in decisions:
            if not isinstance(decision, LearningDecision):
                raise ValueError("Learning requires a trusted app decision.")
            if decision.name not in ("USER.md", "MEMORY.md"):
                raise ValueError("SOUL.md remains human-controlled.")
            if any(type(flag) is not bool for flag in (decision.user_requested, decision.noteworthy,
                    decision.verified, decision.confirmed, decision.significant)):
                raise ValueError("Learning decisions must be boolean.")
            if not decision.user_requested:
                if decision.name == "USER.md":
                    if not (decision.confirmed and decision.source == "user"
                            and decision.kind in ("preference","habit","like","dislike","choice")
                            and (decision.kind != "choice" or decision.significant)):
                        raise ValueError("Personal facts require explicit user confirmation.")
                elif not (decision.kind == "milestone" and decision.source == "validator"
                          and decision.significant and decision.verified):
                    raise ValueError("Automatic memory requires a verified significant milestone.")
        for decision in decisions:
            if not isinstance(decision, LearningDecision):
                raise ValueError("Learning requires a trusted app decision.")
            self.memory.remember(decision.name, decision.text,
                                 user_requested=decision.user_requested,
                                 noteworthy=decision.noteworthy, verified=decision.verified)
        return response
