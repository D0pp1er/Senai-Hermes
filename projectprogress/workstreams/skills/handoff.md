# Skills coordinator handoff

## Implemented behavior

- Isolated local and pinned public GitHub package imports; syntax/path/blob/hash validation and atomic activation.
- Exact selected skill context/resources for feature-local requests, native skill mentions preserved, retained task artifacts and observed outcomes.
- Evidence-guided Codex proposals, independent regression checks, latest-pass activation, immutable accepted history and rollback.
- Checked new-package acceptance with imported/learned_here/unknown/demo origins and short provenance history.
- Obsidian Markdown projection, including Windows-local destination refresh without registry mutation or replacing personal notes/settings.

## Minimal shared integration proposals (not applied)

1. Add a `senai skills ...` dispatch that delegates to senai.skills.cli.main(argv, stdout=..., stderr=...). Preserve normal --skill literal native mentions.
2. Consolidate requirements-skills.txt's PyYAML==6.0.3 into packaging. Feature .venv already contains it; never change a global editable senai install.
3. If normal requests need registry context, add an explicit separate option such as --registry-skill NAME and select from Registry(project / "outputs" / "skills"). Do not overload native --skill or silently scan global registries. Select only inside the already authorized project/scope.
4. Inject selected instructions/resource context into the existing prompt/execution path while keeping existing CodexOptions/session handling. Standalone run_request deliberately does not resume the shared session and must not replace the Telegram runner.
5. Record independently observed results against the exact selected digest with record_outcome. Without checks use unverified. review/learning is explicit; do not auto-activate model suggestions. Optional background hooks require their own configured policy and integration tests.
6. Keep export refresh explicit; do not install Obsidian, alter personal settings, publish or sync user notes automatically. Windows viewing can use a dedicated local vault destination, leaving runtime state in WSL.

## Data/dependency migration

Registry SQLite separate from Telegram/core data. Additive CREATE IF NOT EXISTS/backfill for skills, outcomes, revisions, validations, accepted_versions, activation_history, origins, learning_candidates and learning_validations. Logical storage version 6. Existing import audits allow imported classification; insufficient evidence stays unknown. Never infer learned origin from filenames/wording. Immutable package snapshots retain source/version/digest across restart. No destructive production migration.

## Verification evidence

Full offline suite: 272 tests (136 skills tests), plus ownership guard. Actual installed-Codex controlled correction/regression/reuse/rollback passed. Real public official-package acquisition/restart passed. Ordinary imported skill-creator authored a local package. User-generated CSV package passed two native JSON cases and was accepted as learned_here; user independently demonstrated subsequent reuse preserving 007/000/42.

User confirmed Windows-local Obsidian vault visibility. Generated artifacts: two origins/five Markdown pages/ten links independently checked; new Windows-local command adopted/refreshed the open vault twice, preserving settings. Logs under outputs/skills-qa/. Exact tested code commit and final readiness are recorded in delivery.json after commit verification.

## Known limits

Explicit selection/review/acceptance, not automatic universal learning or weight training. Supplied check cases do not prove general improvement. Public GitHub full SHA-1 only, no private/arbitrary URL/archive sources; no content-security scanner/permission grant. YAML is bounded with tags/aliases rejected. Native config/tool behavior still applies. Output views are one-way snapshots; changed generated notes are protected rather than overwritten; personal notes belong outside managed pages. No shared production router changes/merge/push performed.

User-approved coordinator exception: README synced exactly from main, no feature logic in it. All implementation/tests/other documentation remain skills-owned.
