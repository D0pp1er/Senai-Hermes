> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

# Cron achievements
- Baseline: 126 offline tests passed in this worktree .venv.
- TDD red: tests failed importing missing senai.cron.
- Green: eight fake-clock/offline behavior tests pass, including four competing connections.
- No live Codex execution, messages, scheduler daemon or OS schedules enabled.
- CLI TDD red: missing senai.cron.__main__; green: dry-run preserves due task and creates no runs.
- Final full offline suite: 135 tests passed (126 baseline + 9 cron).
- Feature-local CLI supports create/list/runs/pause/resume/delete/interrupt/dry-run.
- No additional dependencies, shared-file patches, or existing-state migrations required.

- 8335f7c: transactional outbox and recovery; full offline suite 154 tests passed on exact commit 8335f7c97916363b41808b8de4e378f879507b10. Log: outputs/cron-qa/offline-tests.log. Live checks not run.

- Calendar/misfire TDD milestone: 171 full offline tests passed, including 35 cron tests.
- Coverage includes spring gap, earlier fall fold only, wall-clock hour stability, restart,
  competing skip claims, failed-history rollback, bounded backlog counts and old DB defaults.
- pip check passes; dependencies installed only in this worktree .venv. No live checks.

- 67b8776: safe show/edit management, 184 full offline tests passed on exact commit.
- Edit-versus-claim race, stale editor, paused/consumed task, active retry and delivery snapshot
  behavior verified. Feature-only schema revision upgrade; no new dependencies or live checks.
