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

## Ordinary request adapter

Exports run_request(registry, request, names, *, project, model=None, read_only=False, native_skills=(), executor=None, checker=None, compatibility_check=None) -> RunResult, RunResult(id, status, verification, response, workspace, report_path, skills, outcome_ids, error), RunSkill(name, version, digest, source). Executor uses stable run_codex(prompt, workspace, *, options) signature; checker(response, workspace) -> Iterable[Check] supplies observed results. Compatibility predicate follows the existing select contract.

CLI run NAME REQUEST [--skill NAME] [--native-skill NAME] [--model MODEL] [--read-only] [--expect-file PATH] is feature-local and available now. It snapshots context and writes only a unique project outputs run. Shared CLI/Telegram routing remains untouched and should use coordinator adapters with explicit session policy, not replace bot execution with standalone runs.

No dependency/schema migration. Additive outcome behavior allows exact previously accepted digests for in-flight runs after a concurrent activation; no never-accepted proposal outcomes allowed. Independent checks required for passed/failed evidence. Default unverified outcomes do not qualify for reviewer proposals. Partial outcome recording errors retain existing IDs and failure status.

Real ordinary imported-skill run passed artifact existence and independent metadata parsing. This verifies routing/use on that example; no automatic learned-origin registration, global installation or generalized improvement established. Obsidian still LAST.

## Learned package/origin APIs

Registry.stage_learning(run_id, *, path, reason) -> LearningCandidate; Registry.learning_candidates() -> list[LearningCandidate]; Registry.check_learning(candidate_id, *, validator) -> LearningValidation; Registry.learning_checks(candidate_id) -> list[LearningValidation]; Registry.accept_learning(candidate_id) -> Skill; Registry.origin(name) -> Origin. Optional check_with_codex(registry, candidate_id, *, cases, project, model=None, executor=None) -> LearningValidation supports deterministic JSON expected-result checking. Trusted validator(candidate) supplies observed Check records.

CLI: learn --run ID --path RELATIVE_PACKAGE --reason TEXT; learning; check-learning ID --cases JSON_FILE [--model MODEL]; learning-checks ID; accept-learning ID; origin NAME. list now adds origin/source_kind/locally_revised fields. import_local(source, *, demo=False) adds a backward-compatible explicit synthetic fixture label. Native/global skill invocation unaffected.

Additive DB tables origins/learning_candidates/learning_validations; no destructive data migration/dependency change. Existing origin inferred only from recognized import audit evidence; other legacy data unknown. Imported plus locally revised stays imported. Source run reports are trusted project state; not cryptographically authenticated author evidence. JSON checks establish only the selected cases.

Actual user-generated artifact was accepted only after two independent real-output checks. Source run ID, observed outcome IDs and validation ID persist in learned origin. Production shared routing still coordinator-owned/unapplied; no automatic background reviews or imports introduced. Obsidian export LAST.

## Obsidian/local copy delivery

export_vault(registry, *, project, destination=None) -> VaultExport and CLI export-obsidian [--destination PATH]. Windows C:\ paths or /mnt/c paths accepted from WSL. No background sync/app launch/install is part of the API. Dedicated generated section preserves personal notes/settings and refuses modified managed notes; exact prior manual projection can be adopted conservatively.

Twenty export tests plus actual Windows-local double refresh passed. User confirmed Obsidian viewing. No new dependency/schema migration. User explicitly authorized only a canonical README sync from main to resolve a historical scope mismatch; this byte-identical shared documentation exception contains no feature logic. Source/tests/other records stay owned. Coordinator handoff and minimal shared hook proposals now in handoff.md. Normal production wiring remains unapplied.

## Final module readiness

Exact tested source commit: 4dbe998788e1601a464f4a7d26077848c19d7f32, 272 offline tests passed; PyYAML dependency healthy. delivery.json public_api is now typed with exact names/signatures/purposes and records source commit/commands. handoff.md is the concise coordinator entrypoint. Normal production integration/merge remain unapplied. Approved canonical README is the only shared-file exception.

## Coordinator skills integration (2026-11-09)

Skills integrated through 82230b2 (tested feature source 4dbe998788e1601a464f4a7d26077848c19d7f32), merge 0667ad5, shared wiring 57d6c2e. Added singular basic skill list/use/import/show/export obsidian and plural advanced CLI. Consolidated PyYAML==6.0.3. Saved project selection feeds immutable exact-version/digest instructions/resources into the EXISTING executor, preserving native --skill, JSON options, memory, pairing and exact Telegram shared-session resume. Ordinary outcomes remain unverified without independently supplied Checks. No automatic proposal activation or model-prose verification. Obsidian path is prompted/saved on explicit export and shown on list/show; refresh stays explicit.

Verification: feature ownership/readiness passed; feature 272 tests passed when its own installed command and isolated config were used. Combined main 622 tests passed, including 9 new skills-composition tests and actual offline Telegram wrapper-child context/resume coverage. Dependency check passed. Initial non-isolated runs loaded operator defaults and failed; scripts/test.py now provides repeatable isolated tests, and the explicitly unconfigured test mocks configuration instead of assuming the user's home is empty. Logs: outputs/skills-combined-regression.log, skills-composition-green.log and skills-install.log. Historical feature handoff reports actual public import/model authoring/checked acceptance/reuse/rollback and user-confirmed Windows Obsidian viewing; those LIVE checks were not rerun by the coordinator.

Remaining explicit/separate paths: advanced skills run is a standalone authoring/evidence pipeline, not the Telegram session executor. Normal requests capture context/outcomes but do not create authoring run reports or auto-stage generated packages. Revision validation is a trusted Python callback/demo; no high-level validation wizard. No Telegram skill-management commands, vault watcher, automatic activation or weight training. Imported content is not security-scanned; origin/check records rely on trusted local state. No production state, live provider calls, push or deployment used.
