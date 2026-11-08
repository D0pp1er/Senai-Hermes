# Memory architecture

## Implemented modules

- store.py: Namespace canonicalizes project paths and requires an explicit scope.
  Entry carries UUID ID, text, provenance and UTC creation/update timestamps.
  SQLite connections are short-lived. BEGIN IMMEDIATE serializes writes and capacity
  checks; concurrent writers cannot bypass namespace limits. CRUD predicates include
  project/scope. Exact duplicate text fails. Delete is permanent at the application
  level and immediately excludes the entry from subsequent retrieval.
- context.py: lexical word-overlap retrieval, deterministic tie order, up to ten
  relevant entries. Snapshots contain provenance/namespace/time metadata as JSON,
  explicitly labeled untrusted reference facts. Angle brackets are escaped. Default
  2200-character budget includes framing and JSON; oversized entries are omitted whole.
  No match yields empty context. A returned string is frozen for that invocation.
  execute_with_memory calls existing build_prompt and a caller-supplied executor
  with the existing run_codex signature. No model calls happen on import.
- candidates.py: bounded, opt-in parser for Memory: fact lines in caller-verified
  outcomes. No model/provider dependency. Candidates are volatile immutable values;
  extraction never writes storage. accept_candidate requires boolean approval,
  namespace match and store validation. Rejection discards the value; acceptance
  uses ordinary capacity/duplicate rules. Accepted facts can be updated/deleted by ID.
- __main__.py: feature-local add/list/update/delete/context commands. Requires explicit
  project/scope. Uses prepare_workspace and outputs/.senai-memory/memory.db; rejects
  symlinked state roots/DB. Private directory/file modes; diagnostics omit fact content.

## Limits and failure behavior

Store defaults: 100 entries and 20000 text characters per namespace; individual text
4000 characters, provenance 500, scope 200. No automatic eviction or compaction.
Writes reject empty/oversized/control-character and recognizable credential patterns.
Pattern rejection cannot identify every secret: candidates require review. Caller
owns authorization and namespace selection; scope names alone are not access control.
Direct MemoryStore callers own path/mode validation; CLI applies isolated path checks.

SQLite schema version 1 is independent of all existing native/Telegram state. Corrupt
DBs and unsupported versions fail without replacement. There is no backup/repair tool.
Deletion is logical SQL deletion, not secure erasure of SQLite pages/backups, and cannot
remove a snapshot already supplied to an executor. Storage is local and unencrypted.
Lexical retrieval has no stemming, semantic embeddings, priority or recency learning.
Candidate extraction is explicit marked-line parsing, not autonomous fact mining.
Existing facts are not silently updated/deduplicated semantically.

## Hermes subset and integration

Official reference consulted 2026-11-09:
https://hermes-agent.nousresearch.com/docs/user-guide/features/memory

Hermes documents bounded curated memory, persisted edits/removals, frozen session
snapshots and capacity rejection. This branch adopts those ideas for explicit scoped
facts using SQLite. It does not implement Hermes MEMORY.md/USER.md compatibility,
automatic writes, session search, external memory providers or profile tooling.
Our snapshots are per wrapper invocation, rather than a native session lifecycle hook.
See current task.md for the minimal proposed coordinator hook; it is not wired here.

## Curated files and fresh-session extension

profiles.py adds optional SOUL.md, USER.md and MEMORY.md under hashed project/scope
paths, with USER additionally hashed by explicit identity. Missing files are empty.
Each read checks fixed filename, symlink paths, regular-file type, bounded bytes,
strict UTF-8, character limits and credential patterns. No import-time state changes.
ProfileProposal carries owner, origin, verification flag, prior content hash and diff.
Writes require caller approval, reject stale revisions, and use flock plus same-directory
fsync/atomic replacement. Empty text deletes. Only human-origin SOUL changes are accepted.

session.py loads SOUL, optional authorized USER, MEMORY in that order under the profile
lock, then retrieves SQLite facts into the remaining budget. Snapshot contains immutable
context, namespace, optional user ID and file revisions. Curated overflow raises rather
than truncates. The new execute_session bridge consumes a supplied snapshot without
reloading; fresh/refresh decisions belong to the coordinator. Detailed limits, trust
boundaries and lifecycle requirements are in integration-notes.md.
