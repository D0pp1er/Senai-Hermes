# Current task

Strengthen modular delivery and merge-conflict prevention for four active workstreams.

Status: complete.

- Shared policy and ownership map are committed on main and synchronized identically
  into all four feature branches without rebase or feature source edits.
- Added tested scope/readiness guard; all four current feature diffs pass ownership.
- Per-feature changes.md, integration-notes.md, and draft delivery.json are seeded
  without overwriting existing feature records.
- Main suite: 136 tests pass. All four copied coordination-tool suites pass.
- Delivery manifests remain draft until feature owners fill actual API/test evidence.

Next: each active chat must reread AGENTS.md and parallel/MERGE_POLICY.md, maintain
its own contract/records, and run the guard before commits and final delivery.
Merge one module at a time with coordinator-owned shared integration changes.

## Integration merge completed

2e50418 includes 26d8da1 and reviewed pending-delivery fix 7487862. Scope/readiness passed; merged main passed 151 tests. Regression log: outputs/integrations-main-regression.log. Live QA remains optional and unperformed. Existing Telegram config/state/session were not accessed.

## Telegram media merge acceptance (2026-11-09)

Merged feature/integrations through 477c17a in a601b95, including cebfe57, c6b930a and a78aa29. Scope/readiness and diff checks passed; full regression passed 184 tests on both feature and merged main. Logs: outputs/qa-integrations/review-regression.log and outputs/integrations-media-main-regression.log.

Gracefully restarted the existing single bot with its original command/environment. Created a protected stopped-state backup under outputs/qa-integrations-live/. Existing jobs, paired users and exact shared session were compared and preserved. Telegram credential configuration was not modified.

Live BotAPI.send_photo uploaded a valid PNG to an existing authorized private chat; Telegram returned a photo message successfully (sanitized evidence: outputs/qa-integrations-live/acceptance.json). User visual confirmation and model-to-manifest photo flow remain pending. /voice QUESTION and bare /voice live audio acceptance remain pending: the existing process has neither SENAI_TTS_API_KEY nor OPENAI_API_KEY. Configure speech locally; never provide secrets in chat. Bot currently runs with text/photo support and unconfigured-voice fallback. No live audio success is claimed.

## Installation memory integration (2026-11-09)

Integrated feature/memory through 3146de5 in merge 0f0c979. Coordinator lifecycle wiring: 62cbf9f. Feature scope/readiness passed before merge, with 176 offline tests (40 memory tests). Combined regression: 235 passed, including existing Telegram media/auth tests, 40 memory tests and 11 coordinator memory lifecycle tests. TDD logs include failing missing-runtime and SOUL-write tests before implementations.

Real isolated Codex acceptance at 62cbf9f: project A saved a harmless USER.md fact; a distinct fresh session in project B recalled it from the same installation. Exact-ID resume also succeeded. No production bot state, jobs, pairing, sessions or credentials were copied or used; no push, deployment or production restart.

Evidence:
- outputs/memory-combined-regression.log
- outputs/memory-transport-tests.log
- outputs/qa-memory-installation/acceptance.json
- outputs/qa-memory-installation/first-session.jsonl
- outputs/qa-memory-installation/final-fresh-session.jsonl
- outputs/qa-memory-installation/final-resume.jsonl

Complete. Memory remains opt-in; production activation was not requested.

## Cron integration (2026-11-09)

Merged feature/cron through 46e739d (6a50762); wiring 7e6cf18. Consolidated pinned dependencies, shared senai cron management, opt-in /cron management, existing serialized native-session execution, and currently authorized durable text delivery. All 299 combined tests passed; installed CLI fixture QA and dependency checks passed. Production state/services untouched; live scheduling remains disabled and unverified. See projectprogress/cron.md for usage and limits.

## Supervised cron worker (2026-11-09)

Added explicit senai cron worker / worker-status commands in 58109c0. Execution and delivery loops are independent; scheduled native execution has a configurable process-group deadline. Unknown execution pauses the schedule and bypasses retries; ambiguous sends remain unknown. Singleton locking preserves Telegram's exact shared-session policy. Existing bot --enable-cron mode also drains delivery independently. All 312 tests passed, including disposable offline pipeline/authorized-delivery and restart acceptance. Live acceptance remains pending explicit instruction; production services/state were not used. Startup, shutdown and recovery: projectprogress/cron.md.

## Voice-only integration (2026-11-09)

Merged feature/integrations through fadeea4 (tested implementation c858952) in af84cc2. Feature scope/readiness and all 216 branch tests passed again. Resolved the Telegram CLI startup conflict by combining protected optional speech loading with existing cron deadlines and independent delivery callbacks. Added tests/coordination/test_voice_cron_composition.py for configured/unavailable speech alongside cron startup. All 345 combined tests passed. Logs: outputs/qa-integrations/coordinator-voice-review.log in the feature worktree, and outputs/voice-only-combined-regression.log plus outputs/voice-cron-composition.log on main.

Current /voice policy supersedes prior text-plus-audio documentation: audio only on successful upload, text fallback when unavailable/failing, no text acknowledgement, and persisted audio/fallback choice across delivery retries. Legacy partial text replies finish as text. Explicit /result still returns text. Optional local voice configuration commands are included; setup remains skippable. New voice_delivery storage is additive and media-local.

No Telegram credentials, production jobs/pairing/media/native authentication/session state were accessed or changed. No bot restart, live API test, push or deployment was performed. No further blocking code fixes found. Later operator-managed live QA should verify /voice QUESTION, bare /voice, explicit /result, unavailable-key fallback and restart/retry continuity. Network acceptance followed by local persistence failure remains an acknowledged ambiguity; no exactly-once claim.

Safely update the feature worktree using a fast-forward merge (do not rebase already-integrated history). The coordinator has NOT updated that worktree:
    cd /home/rk/SentiensHermes/senai-integrations
    git status --short
    git branch --show-current
Stop if the tree is not clean or the branch is not feature/integrations. Then:
    git merge --ff-only main
    source .venv/bin/activate
    python -m pip install -e .
    python -m pip check
    python -m unittest discover -s tests -v
    python scripts/check_workstream_scope.py --feature integrations --ready
Reinstalling in this worktree's .venv includes the cron dependencies now present on main; never use pip --user or reinstall globally. If fast-forward refuses because new feature commits were added, stop for coordinator review; do not reset or automatically rebase. These commands do not restart the bot or migrate live runtime state.
