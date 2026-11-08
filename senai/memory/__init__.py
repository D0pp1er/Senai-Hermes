"""Explicit, project-scoped persistent facts; no automatic model calls."""
from .store import Entry, MemoryStore, Namespace

__all__ = ["Entry", "MemoryStore", "Namespace"]
