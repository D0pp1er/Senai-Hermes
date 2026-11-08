# Memory achievements

2026-11-09, feature/memory:
- 9c91d4d: scoped SQLite persistence, CRUD, provenance/timestamps, capacity and isolation.
  TDD red: missing module; green: seven tests including real process restart.
- 620249b: bounded escaped untrusted snapshots and injectable existing executor bridge.
  TDD red: missing context module; green: twelve feature tests.
- Reviewed candidate extraction and feature-local CRUD/context CLI implemented.
  TDD red: absent candidate module and CLI entry; green: eighteen feature tests.
- Full offline regression: 144 tests pass (126 baseline + 18 feature tests).
- Disposable subprocess QA confirms recall, scope isolation and deletion.
- Own .venv binding verified from /tmp; no extra dependencies, shared-file changes,
  production state, merges or pushes. Coordinator integration remains proposed.

Multifile extension, code commit fa0a3c5:
- Scoped optional SOUL.md / USER.md / MEMORY.md, private user identity selection.
- Human-only SOUL changes; outcome proposals require trusted verification plus approval.
- Diff review, content-hash conflicts, cooperative file locking and atomic replacement.
- Ordered bounded fresh-session context; frozen snapshot reused without reloading.
- Existing SQLite APIs preserved; new APIs and CLI are additive, no dependencies.
- 167 full offline tests pass: 126 original + 10 coordinator policy + 31 memory.
- Disposable subprocess checks confirm multifile restart loading and user exclusion.

Offline transport verification (411d8b0): real run_codex invokes a fake executable
inside a temporary output workspace. Verified final response persistence, literal
request transport, all memory sources, USER exclusion, frozen resumed context,
exact native session ID and failure/no-retention behavior.
170 total tests pass, including 34 memory tests. No live model claim.

Single-owner installation extension: flat global files, inclusion of USER across
projects, selective app retention, no SOUL learning, exact duplicate suppression
and separate-installation isolation. Existing scoped behavior preserved.
Forty memory tests pass; full current-revision evidence is being finalized.

Final installation verification: d3fbff9, 176 full offline tests PASS (40 memory).
CLI subprocesses confirm flat global files, fresh-session reload and other-installation
isolation. Evidence retained in outputs/qa-project/memory-installation-*.

Noteworthy extension: user selected explicit confirmation rather than repeated-statement
retention. Pure structured-evidence evaluator and dry-run CLI implemented. Thirteen new
offline tests pass; no SOUL proposal path and no arbitrary model-output validation.
