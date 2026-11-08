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
