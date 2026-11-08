# Memory architecture

senai.memory.store uses standard-library SQLite, independent of Telegram state.
Namespace canonicalizes project paths and requires an explicit scope. Entries carry
UUID IDs, provenance and UTC creation/update timestamps. Every write opens a short
transaction; BEGIN IMMEDIATE serializes capacity checks. Limits apply per namespace.
Duplicate text fails; capacity errors never evict facts. Delete is namespace-qualified.
Schema v1 creates only memory_entries; unknown versions fail. Corrupt DBs raise without
replacement. Lexical retrieval requires overlapping words; no vector service.

Reference consulted 2026-11-09: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
Implemented subset: durable curated facts, explicit edits/removal and bounded capacity.
This is not Hermes file format compatibility, session search, or automatic retention.
Credential pattern rejection is defense in depth, not a complete secret detector.

context.py builds bounded JSON snapshots (including metadata and escaping), labels
them untrusted, escapes angle brackets and omits whole entries that do not fit.
execute_with_memory composes existing build_prompt and an injected run_codex-shaped
callback. It forwards workspace/options unchanged, does not save results or alter sessions.
Coordinator proposal: call this wrapper after authorization/workspace preparation with
an explicit Namespace, isolated MemoryStore, existing run_codex and CodexOptions.
No shared files need changing until coordinator integration.
