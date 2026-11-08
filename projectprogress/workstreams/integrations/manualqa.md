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

## Combined image and voice verification

PASS offline: 183 full tests; 30 focused image/voice tests; ownership/diff checks.
From this worktree: .venv/bin/python -m unittest discover -s tests -v
Focused: .venv/bin/python -m unittest tests.integrations.test_telegram_media tests.integrations.test_telegram_voice -v
Evidence: outputs/qa-integrations/media-voice.log and regression.log.

After coordinator integration, operator configures speech locally if desired and
restarts the existing single bot with its original project/config/session state.
Do not rerun pairing or configure a duplicate poller.

1. Ask "Create an image of a red kite and send it here". Expect short text and
   an actual photo, or an honest generation-unavailable message.
2. Ask to send an existing PNG/JPEG from outputs/. Expect that photo alone, with
   no unrelated folder contents. Outside/private/invalid images must not upload.
3. Send "/voice What is Python?". With speech configured: expect text plus a
   playable voice note labeled AI-generated. Without config: short setup notice,
   no model/speech execution. No secrets belong in Telegram messages.
4. Send "/voice" after a successful text response. Expect that answer read aloud,
   without a new model turn. Ask a normal question next: expect text only.
5. Check existing /status, /result, pairing/revocation and shared-session continuation.
   /result remains text-only. No claim of media delivery before actual upload.

Live acceptance NOT RUN; API billing/voice quality and real imagegen availability
are not established by fake client tests. Voice configuration is documented in
integration-notes.md; never paste credentials in chat or tracked config.

Final rerun on a78aa29447c62fac8f60377eb1b3b74a9f8a67dd: PASS, 184 total tests,
31 media/voice tests. Scope/diff checks PASS. Final evidence supersedes earlier counts.
The remaining delivery-record commit changes no source/tests. Live acceptance NOT RUN.

Voice config storage TDD: .venv/bin/python -m unittest tests.integrations.test_voice_config -v (13 tests pass). All fixtures/keys are synthetic in temporary directories; no real configuration touched. Logs: outputs/qa-integrations/voice-config-{red,green}.log.

## Optional voice setup acceptance

Offline tests use only synthetic keys and temporary config/project/state directories.
Commands: .venv/bin/python -m unittest tests.integrations.test_voice_config tests.integrations.test_voice_setup_cli -v
Full regression: .venv/bin/python -m unittest discover -s tests -v
Readiness: .venv/bin/python scripts/check_workstream_scope.py --feature integrations --ready
Logs: outputs/qa-integrations/voice-config-red.log, voice-cli-red.log,
voice-compat-red.log, voice-cli-green.log and voice-setup-regression.log.

Verified offline: Configure/Skip during initial setup with/without --start; no prompt
for existing-user startup; later configuration/replacement/check/removal without Telegram
credentials/API/poller; Enter keeps saved key; atomic write failure preserves old file;
600/700 modes; reject insecure/symlink/Git/project storage; secret-free malformed config,
repr, prompt and parser diagnostics; environment precedence; invalid optional config
keeps text Telegram operational; no environment mutation; native auth regression retained.
Real temporary SQLite/credential fixture hashes remain identical for jobs, users, media,
pairing and exact native UUID through standalone configuration/update/check/removal.
Existing /voice tests still verify text and matching audio and durable retry behavior.

For an operator's later manual acceptance (NOT RUN here): choose Skip during first setup
and confirm Telegram works; configure voice later using only the hidden local prompt;
check local status and permissions without opening/catting the key file; replace/remove
and check status again. Confirm command output explains graceful restart and never
prints the key. Do not repeat setup/pairing or launch another bot. Only an explicitly
approved later restart applies changes to a running bot. Live API key validity/audio
playback is not claimed by these local checks and was not requested for this task.

Final voice setup evidence: exact source commit fa9c20963ec146339c1c409573255b667b571c33; 210 total tests PASS and 26 setup/config tests PASS. Scope/diff PASS. Final readiness command recorded in delivery.json; records-only commit follows. No live API/auth/audio acceptance or restart claimed.

## Current voice-only acceptance (supersedes earlier dual-output checks)

TDD: voice-only success, no acknowledgement, upload-failure/missing-file fallback,
restart-after-fallback, interrupted-finalization and no-key cases failed before changes.
Current expected checks after separately approved integration/restart:
1. /voice QUESTION -> one voice note; no text acknowledgement or answer transcript.
2. /voice after a successful answer -> one voice note; no repeated transcript.
3. Missing speech config/generation/upload failure -> answer in text.
4. A fallback-text retry never regenerates speech or later adds voice.
5. Normal questions, images and explicit /result still work; revoked users receive nothing.
Offline fixtures cover these plus legacy partially sent text completion without audio.
Logs: outputs/qa-integrations/voice-only-{red,green,regression}.log and voice-no-key-red.log.
Live API/audio checks NOT RUN; no production process/state was touched.
