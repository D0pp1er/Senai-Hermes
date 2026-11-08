# Memory changes

2026-11-09:
- 9c91d4d: scoped SQLite CRUD and fresh-process recall.
- 620249b: bounded advisory snapshots and injected executor.
- 596fb2f: reviewed outcome candidates and standalone CLI; 144 offline tests passed.
- Multifile extension (pending commit): scoped SOUL.md / USER.md / MEMORY.md,
  reviewed diffs, validation, cooperative locks, atomic replacement, conflict detection,
  explicit fresh-session snapshots and profile/session CLI commands.
- User confirmed private project-and-user USER.md and human-only SOUL.md.
- New TDD red states: missing profile module, absent CLI routes, and unverified
  outcome proposal accepted. Implementations now satisfy 31 memory behavior tests.
