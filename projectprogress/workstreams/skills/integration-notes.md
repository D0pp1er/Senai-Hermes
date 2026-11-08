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

## Terminal entrypoint

Implemented `python -m senai.skills`, separately callable within this checkout's .venv. cli.main(argv=None, stdout=None, stderr=None) -> int. Uses stable senai.workspace.prepare_workspace; no sibling import. Per-project registry is outputs/skills/. demo.run_demo(project) -> dict retains synthetic evidence under outputs/skills-demo/.

Coordinator may later dispatch `senai skills ...` to this feature-local main once merging. No dispatch or packaging patch applied here. The context command exports instructions and does not invoke Codex. Production execution/reviewer wiring still pending. No dependency/migration change in this step.

## Reviewer contract

Exports: ReviewResult(status, reason, revision); review_skill(registry, name, *, outcome_ids, reviewer) -> ReviewResult; review_with_codex(registry, name, *, outcome_ids, project, model=None, executor=None) -> ReviewResult. reviewer(prompt) returns strict JSON text; executor(prompt, workspace, *, options) returns native final-response text. No activation or validation occurs as a side effect. Caller selects trustworthy/redacted evidence. No-change decisions have no separate durable log yet.

CLI: python -m senai.skills --project PROJECT review NAME --outcome ID [--outcome ID ...] [--model MODEL]. Native installed Codex/auth required only for this explicit command. Output contains proposed Revision or no_change. Shared router/normal execution/session mappings unchanged. No new dependencies or DB migration.

Coordinator may call review after independently verified outcomes, but should not infer checks from model success prose or promote proposals without independent regression cases. Native Codex option/config semantics apply. Live reviewer output quality, actual behavioral improvement and production wiring remain unverified.

## Metadata/dependency integration

Install `.venv/bin/python -m pip install --only-binary=:all: -r requirements-skills.txt` in a feature environment. Runtime pin: PyYAML==6.0.3. Only this worktree venv was changed. Coordinator should consolidate the dependency into shared packaging; no root metadata/lock edits here.

Additive API: Registry.metadata(name) -> dict; CLI metadata NAME. select(names, *, compatibility_check=None) and execute(request, names, *, executor, compatibility_check=None) preserve old calls. Optional trusted compatibility_check(metadata) -> bool must return True to permit selection. It does not grant tools or install requirements; coordinator decides runtime compatibility policy.

No DB migration. Stricter frontmatter checks may reject previously accepted overlong descriptions or ambiguous YAML; do not alter historical bytes to bypass hashes. Full official-spec compliance is not claimed: legacy source-folder/name mismatch remains supported, aliases/tags disallowed, and nested Hermes metadata is treated as inert data. Public source acquisition remains next, not implemented by this compatibility change.

## Obsidian requirement (planned)

New user requirement: export project skill inventory with imported/learned origin and a brief history to Obsidian-readable Markdown. Default separate folder outputs/skills-vault/; no personal vault path needed initially. No runtime API/CLI exists for export yet. Registry remains authoritative. Additive provenance migration may be needed; imported+revised is distinct from new learned_here packages. This introduces no shared coordinator patch until an optional export-refresh hook is proposed. No personal vault/settings changed.

## Fast demonstration priority

User deferred Obsidian export until last. Added feature-owned run_live_demo(project, *, executor=None, model=None, emit=None) -> dict and CLI demo --live [--model MODEL]. Uses existing stable execution/reviewer/registry APIs; shared core untouched. emit(message) receives stage progress; optional executor has run_codex signature. No new dependency or schema migration. Native runs consume up to four model calls; offline tests inject responses.

Live isolated correction/reuse passed, with actual deterministic JSON checks. It is a deliberately lossy known CSV fixture, not normal production traffic. Existing ordinary CLI/Telegram routes still require coordinator integration. Keep production-readiness claims separate from this successful feature-local demo.

## Public source contract

Registry.import_github(repository, *, commit, path, fetch=None) -> Skill. repository is owner/repo, commit full lowercase 40-hex SHA, path POSIX relative directory or . . fetch(url, *, max_bytes) -> bytes is the injectable transport; no auth exposed. CLI import-github OWNER/REPO --commit SHA --path DIRECTORY. Existing local import source semantics preserved; common internal file-bundle activation centralizes integrity/atomicity checks.

No new runtime dependency or DB migration. Canonical source URL contains exact commit/path; package digest and import audit retained. Public import cannot overwrite native/global skills or an existing registry name. No provider beyond allowed installed Codex is introduced. Arbitrary/private sources, archive extraction, automatic updates and native skill installation remain unsupported. Default transport ignores environment proxy credentials and refuses redirects; deployments requiring a proxy need an explicit adapter/policy later.

Actual network QA imported official skill-creator into a separate outputs QA registry, with seven files/hash/provenance verified after restart; no script ran. This does not establish safety or compatibility of every public skill. Coordinator normal CLI/Telegram wiring remains unapplied. Obsidian export LAST.
