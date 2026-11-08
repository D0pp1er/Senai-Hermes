# senai collaboration rules

- Work in WSL. Do not edit the Windows project mirror or synced reference files.
- Read projectprogress/parallel/README.md and the assigned handoff prompt before coding.
- Each feature chat owns exactly one worktree and branch. Never switch another checkout,
  reset its files, edit main, merge branches, or push unless the user explicitly requests it.
- Activate this checkout's .venv. Never use pip install --user or change the global editable
  senai install. Verify senai.__file__ resolves inside this worktree.
- Use failing behavior tests, small implementations, refactoring, and short commits.
- Keep feature changes inside the assigned module/tests/docs ownership boundaries.
  Shared CLI/execution/packaging/root documentation changes are coordinated separately.
- Record feature objectives, achievements, current task, architecture, and manual QA in
  projectprogress/workstreams/<feature>/; tests belong in tests/<feature>/.
- Generated artifacts and runtime state stay in this worktree's outputs/. Tests may use
  temporary directories. Never use production Telegram state or the live project for QA.
- Do not print/copy credentials, start a second poller for the production bot, modify global
  Codex skills/configuration, or activate real schedules during automated testing.
- Preserve current CLI, Telegram pairing/shared-session behavior, and old DB compatibility.
- Keep messages short. Distinguish offline tests, live checks, and unverified claims.
