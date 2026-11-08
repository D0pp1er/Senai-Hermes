"""Immutable descriptions of inactive instruction revision proposals."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Revision:
    id: str
    skill_name: str
    version: str
    base_digest: str
    digest: str
    source: str
    outcome_ids: tuple[str, ...]
    reason: str
    status: str
    path: Path
    instructions: str
    created_at: str
