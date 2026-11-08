# Merge policy v1: modular delivery and shared-file ownership

This policy adds guardrails to the active workstreams; it does not redesign or discard
their already implemented APIs. Read it before each new implementation step.
Canonical ownership is [ownership.json](ownership.json) on main, not a branch-edited copy.

## 1. One writer for every path

| Workstream | Source owned | Tests owned | Records owned |
| --- | --- | --- | --- |
| integrations | senai/integrations/, senai/telegram/ | tests/integrations/ | projectprogress/workstreams/integrations/ |
| memory | senai/memory/ | tests/memory/ | projectprogress/workstreams/memory/ |
| cron | senai/cron/ | tests/cron/ | projectprogress/workstreams/cron/ |
| skills | senai/skills/ | tests/skills/ | projectprogress/workstreams/skills/ |

Each also owns requirements-<feature>.txt. All other paths are coordinator-owned unless
ownership.json is deliberately revised on main. Read access is allowed across modules;
write access belongs to the assigned owner. Do not edit a sibling to make your tests pass.

Coordinator-only files include cli.py, codex.py, prompts.py, options.py, workspace.py,
pyproject.toml, aggregate README/CHANGELOG/architecture/manualqa/progress files, root agent
instructions, and this policy/tooling. Feature chats propose minimal shared changes in
integration-notes.md; the coordinator applies them once during integration.

Identical coordinator policy updates are distributed to each branch. Preserve them.
They are allowed by the guard only when their bytes match main. Do not reset them as
unexpected agent changes, rewrite them, or include feature logic in those files.

## 2. Deliver one self-contained module

- Keep public exports explicit in the module package. Internal helpers stay internal.
- Import stable core seams or standard/declaratively listed dependencies; no imports
  from unmerged sibling features. Use dependency injection for execution/delivery/clock.
- No network calls, DB creation, threads, skill activation, or schedules at import time.
- A module must have a feature-local CLI/demo and deterministic offline tests without
  requiring another unmerged branch, personal credentials, or a live model.
- Preserve existing public behavior. Public breaking changes require a versioned adapter
  and migration notes, not silent signature changes.
- Keep feature DBs/config namespaces separate; migrations live under the owning package.
  Do not share a global numbered migration directory or independently extend Telegram's DB.
- Preserve explicit project/scope boundaries and the configured shared-session policy.

## 3. Shared records use per-feature files, not concurrent edits to one list

Every workstream maintains these files in its own progress directory:
objectives.md, acheivements.md, current task.md, architecture.md, manualqa.md,
changes.md, integration-notes.md, and delivery.json.

- changes.md: dated feature-local change notes and commit IDs; do not append root CHANGELOG.
- integration-notes.md: proposed shared hooks/patches, sibling requirements, schema migration,
  dependencies, compatibility assumptions, and any integration blockers.
- delivery.json: machine-readable module/API/CLI/executor/dependency/storage/test contract.
  Use [delivery-template.json](delivery-template.json), schema_version 1. Keep status draft
  until evidence is recorded. Include exact signatures, not vague capability labels.

Runtime dependencies go in requirements-<feature>.txt and delivery.json. The coordinator
consolidates pyproject.toml, CLI dispatch, aggregate documentation, and combined migrations.
No global install, shared registry edit, root lock-file rewrite, or production state changes.

## 4. Required checks

From your own worktree/environment, before each feature commit:

```bash
.venv/bin/python scripts/check_workstream_scope.py --feature FEATURE
.venv/bin/python -m unittest discover -s tests -v
```

Replace FEATURE with integrations, memory, cron, or skills. The scope guard checks committed,
staged, unstaged, and untracked nonignored paths, including the deleted side of renames.
It loads policy from main. It is a workflow guard, not a security sandbox or proof of correctness.

Before declaring delivery complete:

```bash
.venv/bin/python scripts/check_workstream_scope.py --feature FEATURE --ready
```

--ready checks a complete, declared delivery contract and evidence, not that tests were
actually run by the guard. Record actual commands/count/tested commit and retain logs.
Do not label unavailable live tests as passed. Keep shared-file proposals unapplied.

## 5. Coordinator merge sequence

1. Review ownership diff, manifest/API compatibility, dependency and migration needs.
2. Confirm feature tests and the inherited baseline; obtain needed live evidence separately.
3. Merge one feature at a time. Do not have four chats merge/rebase/switch the main checkout.
4. Apply shared adapters/router/hooks centrally; add cross-feature contract/integration tests.
5. Follow request flow: authorization -> scope -> memory/skills context -> execution ->
   persisted outcome -> delivery -> validated learning proposals. Scheduler submits via
   the same execution boundary rather than creating a second hidden agent pipeline.
6. Update aggregate docs/packaging once, validate the combined suite, then commit.

This reduces textual conflicts; it cannot guarantee zero behavioral conflicts. The final
combined execution, namespace, dependency, and migration checks remain necessary.
