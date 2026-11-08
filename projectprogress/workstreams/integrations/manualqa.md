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

## Telegram chat improvement, 2026-11-09

PASS offline: .venv/bin/python -m unittest tests.integrations.test_telegram_chat -v
(5 tests), full unittest discovery (149 tests), scope guard, git diff --check.
Evidence logs: outputs/qa-integrations/chat-tests.log and regression.log.

After coordinator integration and an operator restart of the existing bot, send a
normal short question. Expect one of the five approved acknowledgement messages,
then a brief plain-text answer without a success-status header. Send another
question to check variation (random selection can repeat). Check /status and
/result; commands should respond directly, and /result should resend the answer.
Request code explicitly to confirm necessary detail is still allowed.
Live acceptance NOT RUN. This worktree's tests use only temporary state/fakes.

## Viewer context regression

PASS offline: 7 chat tests and 153 full-suite tests; scope guard and diff check pass.
Logs: outputs/qa-integrations/viewer-tests.log and regression.log.
After coordinator integration/restart, request a generated-file summary. Expect the
useful content in chat, without a misleading host-only download link. Ask for an
image/voice reply: while media is unavailable, expect an honest short explanation,
not a false claim of attachment. Actual model behavior/live delivery NOT RUN.

## Image delivery acceptance

PASS offline: .venv/bin/python -m unittest tests.integrations.test_telegram_media -v
(11 tests), full discovery (164 tests), scope guard and git diff --check.
Logs: outputs/qa-integrations/media-{red,green}.log, media-pipeline-red.log, regression.log.
After integration/restart, ask to create an image and send it here; expect text plus
an actual photo. Ask to send an existing image within configured outputs/. Check a
missing/outside/private path fails with an honest chat response. Live checks NOT RUN.
