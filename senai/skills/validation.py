"""Persisted regression evidence; trusted callers own the checker implementation."""
from dataclasses import dataclass
from .outcomes import Check


@dataclass(frozen=True)
class Validation:
    id: str
    revision_id: str
    base_digest: str
    candidate_digest: str
    checks: tuple[Check, ...]
    status: str
    error: str
    created_at: str
