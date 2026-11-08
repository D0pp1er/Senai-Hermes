# Skills integration notes

No shared changes applied. Coordinator should initialize Registry(project / "outputs" / "skills") within an authorized project. select(names) supplies immutable Skill records to the existing execution path, retaining native --skill behavior. Do not treat imported instructions as authority to expand permissions.

After execution, a trusted adapter may call record_outcome(name, digest=selected.digest, request=..., result=..., checks=tuple[Check, ...], correction=...). The digest must identify the actual selected package. Checks must come from independently observed validation, not model-generated success prose. The API cannot authenticate fabricated evidence. Do not record secrets; redact private details at the adapter boundary. No automatic core hook or Codex reviewer is implemented yet.

Storage migration is additive and idempotent: Registry initialization adds outcomes and an index to registry.sqlite3, preserving the prior skills table. No existing Telegram/core state is touched. SQLite and package data remain per-project. Dependencies: standard library only. No sibling feature imports.

Current blocking limitations for final delivery: no revision history/activation/rollback, no automatic review, no feature-local CLI, no public-source adapter or full Hermes metadata compatibility. delivery.json remains draft. Scope check alone is not merge readiness.

## Revision proposal API

`Registry.propose_revision(name, *, document, outcome_ids, reason) -> Revision` and `Registry.revisions(name) -> list[Revision]` are additive APIs. A future injected Codex reviewer may supply the candidate document and rationale; caller must link actual outcome IDs. No coordinator wiring is applied. `Revision(id, skill_name, version, base_digest, digest, source, outcome_ids, reason, status, path, instructions, created_at)` is frozen; current status is always proposed. No model call, skill execution or activation occurs.

Additive local migration: create revisions table on Registry initialization, preserving previous skills/outcomes and package snapshots. No new dependency. Version tokens are distinct identifiers, not semantically ordered releases. Existing draft blockers remain except inactive proposal persistence is now implemented.

## Regression validation API

Registry.validate_revision(revision_id, *, validator) -> Validation. Callback validator(base: Skill, candidate: Revision, outcomes: tuple[Outcome, ...]) -> Iterable[Check]. Registry.validations(revision_id) -> list[Validation] (oldest first). No execution or activation hook applied to shared code. Checker isolation, trusted observed results and selection of regression cases belong to the injecting adapter.

Additive validations table/index; no dependency change or shared-state migration. Latest attempt must gate future activation; candidates have no activation API yet. Raw checker exception text is not persisted. Passing tests can establish acceptance only for the supplied cases.

## Activation and rollback APIs

Registry.activate_revision(revision_id) -> Skill; Registry.rollback(name, *, digest, reason) -> Skill; Registry.versions(name) -> list[Skill]; Registry.history(name) -> list[Activation]. Activation record fields: id, skill_name, action, from_digest, to_digest, revision_id, validation_id, reason, created_at. Revision.status expands to proposed/active/accepted; signatures remain compatible.

Migration: additive accepted_versions and activation_history tables; idempotent backfill of prior active rows as import baselines. Initial imports record acceptance/audit in the same transaction. No existing outcome/revision/validation records modified. All state stays in the explicit per-project registry. Standard library only. No sibling dependencies.

Remaining production gates: feature-local CLI/demo, injected reviewer, broader import compatibility/public adapters, coordinator wiring and isolated end-to-end/live checks. Normal senai --skill continues its native installed-skill behavior. Do not interpret this module-only feature as production integration.
