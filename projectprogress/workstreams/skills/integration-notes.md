# Skills integration notes

No shared changes applied. Coordinator should initialize Registry(project / "outputs" / "skills") within an authorized project. select(names) supplies immutable Skill records to the existing execution path, retaining native --skill behavior. Do not treat imported instructions as authority to expand permissions.

After execution, a trusted adapter may call record_outcome(name, digest=selected.digest, request=..., result=..., checks=tuple[Check, ...], correction=...). The digest must identify the actual selected package. Checks must come from independently observed validation, not model-generated success prose. The API cannot authenticate fabricated evidence. Do not record secrets; redact private details at the adapter boundary. No automatic core hook or Codex reviewer is implemented yet.

Storage migration is additive and idempotent: Registry initialization adds outcomes and an index to registry.sqlite3, preserving the prior skills table. No existing Telegram/core state is touched. SQLite and package data remain per-project. Dependencies: standard library only. No sibling feature imports.

Current blocking limitations for final delivery: no revision history/activation/rollback, no automatic review, no feature-local CLI, no public-source adapter or full Hermes metadata compatibility. delivery.json remains draft. Scope check alone is not merge readiness.

## Revision proposal API

`Registry.propose_revision(name, *, document, outcome_ids, reason) -> Revision` and `Registry.revisions(name) -> list[Revision]` are additive APIs. A future injected Codex reviewer may supply the candidate document and rationale; caller must link actual outcome IDs. No coordinator wiring is applied. `Revision(id, skill_name, version, base_digest, digest, source, outcome_ids, reason, status, path, instructions, created_at)` is frozen; current status is always proposed. No model call, skill execution or activation occurs.

Additive local migration: create revisions table on Registry initialization, preserving previous skills/outcomes and package snapshots. No new dependency. Version tokens are distinct identifiers, not semantically ordered releases. Existing draft blockers remain except inactive proposal persistence is now implemented.
