"""Durable source classification, independent of later local revision history."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Origin:
    name: str
    kind: str
    source_kind: str
    source: str
    source_run_id: str
    source_outcome_ids: tuple[str, ...]
    reason: str
    original_digest: str
    validation_id: str
    created_at: str
    locally_revised: bool
