"""Opt-in extraction of explicitly marked facts, followed by caller approval."""
from dataclasses import dataclass

from .store import Namespace, validate_text


@dataclass(frozen=True)
class Candidate:
    namespace: Namespace
    text: str
    provenance: str


def extract_candidates(outcome, *, namespace, outcome_id, verified,
                       max_candidates=10):
    """Parse 'Memory: fact' lines only; never store raw output or invoke a model.

    verified must be supplied by a trusted outcome validator, not model self-report.
    Rejected/secret-looking lines are skipped, without echoing them.
    """
    if type(verified) is not bool:
        raise ValueError("verified must be boolean")
    if type(max_candidates) is not int or not 0 <= max_candidates <= 100:
        raise ValueError("max_candidates must be between 0 and 100")
    if not isinstance(outcome, str) or len(outcome) > 100000:
        raise ValueError("outcome exceeds input limit")
    provenance = validate_text("outcome:" + validate_text(outcome_id, "outcome_id", 200),
                               "provenance", 500)
    if not verified or max_candidates == 0:
        return ()
    candidates = []
    seen = set()
    for line in outcome.splitlines():
        if not line.startswith("Memory: "):
            continue
        try:
            text = validate_text(line[len("Memory: "):])
        except ValueError:
            continue
        if text in seen:
            continue
        seen.add(text)
        candidates.append(Candidate(namespace, text, provenance))
        if len(candidates) == max_candidates:
            break
    return tuple(candidates)


def accept_candidate(store, namespace, candidate, *, approved):
    """Approval must come from the authorized caller. Candidates are volatile until saved."""
    if approved is not True:
        raise ValueError("explicit boolean approval required")
    if candidate.namespace != namespace:
        raise ValueError("candidate namespace mismatch")
    return store.add(namespace, candidate.text, provenance=candidate.provenance)
