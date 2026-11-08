"""Outcome evidence supplied by a trusted execution/check adapter, not model prose."""
from dataclasses import dataclass
import json


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class Outcome:
    id: str
    skill_name: str
    skill_version: str
    skill_digest: str
    request: str
    result: str
    checks: tuple[Check, ...]
    correction: str
    status: str
    created_at: str


def _decode(row):
    values = list(row)
    values[6] = tuple(Check(**check) for check in json.loads(values[6]))
    return Outcome(*values)
