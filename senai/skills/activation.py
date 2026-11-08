"""Audit records for explicit skill activation and rollback."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Activation:
    id: str
    skill_name: str
    action: str
    from_digest: str
    to_digest: str
    revision_id: str
    validation_id: str
    reason: str
    created_at: str
