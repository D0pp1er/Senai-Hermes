"""Explicit scoped facts, curated files and frozen session context."""
from .store import Entry, MemoryStore, Namespace
from .context import build_snapshot, execute_with_memory
from .candidates import Candidate, extract_candidates, accept_candidate
from .profiles import ConflictError, ProfileDocument, ProfileProposal, ProfileStore
from .session import SessionSnapshot, start_session, execute_session
from .installation import InstallationMemory
from .noteworthy import MemoryEvent, NoteworthyProposal, evaluate_noteworthy
from .profile_commands import profile_main, setup_profiles

__all__ = [
    "Entry", "MemoryStore", "Namespace", "build_snapshot", "execute_with_memory",
    "Candidate", "extract_candidates", "accept_candidate", "ConflictError",
    "ProfileDocument", "ProfileProposal", "ProfileStore", "SessionSnapshot",
    "start_session", "execute_session", "InstallationMemory",
    "MemoryEvent", "NoteworthyProposal", "evaluate_noteworthy", "profile_main", "setup_profiles",
]
