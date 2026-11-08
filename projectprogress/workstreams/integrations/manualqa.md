# Integrations manual QA

2026-11-09, Ubuntu-22.04 WSL, assigned worktree only.

PASS (offline): branch feature/integrations; .venv/bin/python and senai.__file__
resolve inside /home/rk/SentiensHermes/senai-integrations.
PASS (offline): baseline 126 tests; RED missing adapter module recorded before
implementation; final full suite 134 tests passed; git diff --check passed.
New tests use temporary SQLite fixtures and fake API/executor only.

Reproduce from the assigned worktree:

```bash
.venv/bin/python -m unittest tests.integrations.test_telegram_adapter -v
.venv/bin/python -m unittest discover -s tests -q
git diff --check
```

Expected: 8 focused tests and 134 total tests pass. Existing argparse negative
tests print usage/error text even when the suite passes.
Coverage: identity/account/project scope, unauthorized and malformed events,
queue bounds, restart duplicate suppression, revocation before execution,
Unicode/redaction splitting and delivery retry without job re-execution.

NOT RUN: live Telegram/pairing/Codex acceptance. No production state or token
was accessed. Discord setup/live acceptance remains future work. Do not start
production pollers for this verification.
