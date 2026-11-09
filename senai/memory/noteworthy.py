"""Conservative, deterministic proposals from trusted structured evidence; no writes."""
from dataclasses import dataclass
from itertools import islice
import unicodedata

from .store import validate_text


@dataclass(frozen=True)
class MemoryEvent:
    """App evidence. confirmed means explicit user approval to retain this user fact."""
    event_id: str
    kind: str
    text: str
    source: str
    verified: bool = False
    confirmed: bool = False
    significant: bool = False


@dataclass(frozen=True)
class NoteworthyProposal:
    name: str
    text: str
    reason: str
    evidence_id: str
    noteworthy: bool = True
    verified: bool = True


def _normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split()).rstrip(".")


def evaluate_noteworthy(events, *, existing=None, max_candidates=5, max_chars=1200):
    """Propose confirmed user facts or validator-verified significant milestones.

    Evidence must come from authorized user input/app validators, never model assertions.
    At most 100 events, 240 characters per single-line fact, and 4000 chars per target.
    No observations, transcripts, counters or proposals are persisted by this function.
    """
    if type(max_candidates) is not int or not 0 <= max_candidates <= 100:
        raise ValueError("max_candidates must be an integer between 0 and 100")
    if type(max_chars) is not int or not 0 <= max_chars <= 24000:
        raise ValueError("max_chars must be an integer between 0 and 24000")
    batch = list(islice(events, 101))
    if len(batch) > 100:
        raise ValueError("event batch exceeds limit")
    existing = {} if existing is None else existing
    if not isinstance(existing, dict) or any(
            name not in ("USER.md", "MEMORY.md") or not isinstance(text, str)
            or len(text) > 4000 for name, text in existing.items()):
        raise ValueError("invalid existing memory")
    known = {name: {_normalized(line.strip().removeprefix("- ")) for line in
                    existing.get(name, "").splitlines() if line.strip()}
             for name in ("USER.md", "MEMORY.md")}
    sizes = {name: len(existing.get(name, "")) for name in known}
    proposals = []
    seen_ids = set()
    chars = 0
    for event in batch:
        if not isinstance(event, MemoryEvent):
            raise ValueError("events must be MemoryEvent values")
        if any(type(flag) is not bool for flag in
               (event.verified, event.confirmed, event.significant)):
            raise ValueError("evidence decisions must be boolean")
        event_id = validate_text(event.event_id, "event ID", 200)
        if event_id in seen_ids:
            continue
        seen_ids.add(event_id)
        if not event.verified:
            continue
        if event.kind in ("preference", "habit", "like", "dislike", "choice"):
            if event.source != "user" or not event.confirmed:
                continue
            if event.kind == "choice" and not event.significant:
                continue
            name, reason = "USER.md", "explicitly confirmed user " + event.kind
        elif event.kind == "milestone":
            if event.source != "validator" or not event.significant:
                continue
            name, reason = "MEMORY.md", "verified significant milestone"
        else:
            continue
        try:
            text = validate_text(event.text, "candidate", 240)
        except ValueError:
            continue
        if "\n" in text or "\r" in text or "\t" in text:
            continue
        key = _normalized(text)
        if key in known[name]:
            continue
        added = len(text) + 2 + (2 if sizes[name] else 0)
        if (len(proposals) >= max_candidates or chars + len(text) > max_chars
                or sizes[name] + added > 4000):
            continue
        proposals.append(NoteworthyProposal(name, text, reason, event_id))
        known[name].add(key)
        chars += len(text)
        sizes[name] += added
    return tuple(proposals)
