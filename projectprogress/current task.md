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
