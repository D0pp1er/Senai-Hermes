> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

# Memory changes

2026-11-09:
- 9c91d4d: scoped SQLite CRUD and fresh-process recall.
- 620249b: bounded advisory snapshots and injected executor.
- 596fb2f: reviewed outcome candidates and standalone CLI; 144 offline tests passed.
- fa0a3c5: multifile extension: scoped SOUL.md / USER.md / MEMORY.md,
  reviewed diffs, validation, cooperative locks, atomic replacement, conflict detection,
  explicit fresh-session snapshots and profile/session CLI commands.
- User confirmed private project-and-user USER.md and human-only SOUL.md.
- New TDD red states: missing profile module, absent CLI routes, and unverified
  outcome proposal accepted. Implementations now satisfy 31 memory behavior tests.

- Delivery verification: tested fa0a3c5; 167 full offline tests pass, including
  31 memory tests and 10 coordinator scope-guard tests. Logs retained under outputs/qa-project.

- 411d8b0: offline real-adapter transport tests. All curated sources plus relevant
  SQLite facts reach the child, exact resume ID and frozen shared snapshot survive,
  errors propagate, and no result is implicitly saved. 170 total / 34 memory pass.

2026-11-09 requirement revision: user confirmed one owner per senai repo/installation.
Added installation-wide USER/MEMORY/SOUL and SQLite adapter, cross-project recall,
request-or-verified-noteworthy app learning and --installation CLI. Old scoped APIs
remain compatible. TDD red: missing InstallationMemory export; green: 40 memory tests.

- d3fbff9: single-owner installation memory implemented. Full regression 176 PASS,
  including 40 memory tests; disposable installation CLI QA and scope/readiness PASS.

2026-11-09: added deterministic noteworthy proposals, confirmed-user-fact policy,
verified milestone policy, budgets/duplicates/content filtering and evaluate-events
dry-run CLI. TDD red: missing evaluator exports, then missing CLI command.
Thirteen new behavior tests pass, including integrated callback success/failure paths.

- bd37417: noteworthy extension. Exact-commit regression 248 PASS, including 53
  memory tests (13 new). Synthetic CLI QA and ownership/readiness checks pass.

2026-11-09 UX objective: authorized fast-forward to e4791e8; refreshed own .venv editable
install to obtain integrated cron dependencies, pip check PASS. Added human profile
shortcuts/setup/demo/README. TDD red: missing exports; additional red tests exposed
subparser stream leakage and multiline duplicate append, both fixed. 17 focused tests pass.
