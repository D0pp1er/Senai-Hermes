> Development history and progress, not onboarding instructions. Current setup and supported capabilities are documented in README.md and docs/.

# Achievements

- Created the local Git repository and documented development steps.
- Built and installed the senai package in WSL.
- Verified real Codex file creation and editing.
- Routed generated files into outputs/ and rejected a symlinked output root.
- Split the implementation into senai/ modules and tests into tests/.
- Eleven regression tests cover input, context, execution, and failure handling.

See CHANGELOG.md for chronological details and verification evidence.

- Added explicit model, profile, and repeated configuration overrides; 14 tests pass.
- Added repeatable image attachments with file validation; 17 tests pass.
- Added opt-in live web search; 19 tests pass.
- Added explicit installed-skill mentions; 22 tests pass.
- Added native session resume by id/name or latest session; 27 tests pass.
- Added interactive terminal handoff through senai chat; 30 tests pass.
- Added native command forwarding preserving arguments, streams, and exit codes; 35 tests pass.
- Added read-only code review for uncommitted/base/commit scopes; 38 tests pass.

## Compatibility verification

- All 40 offline tests pass without skips; installed process tests preserve argument values and exit status.
- Verified against installed WSL Codex CLI 0.167.0.
- A live search-enabled request created outputs/compatibility_demo.py; independently checked marker().
- A live --last invocation recalled senai-compatible from the preceding session.
- Interactive senai chat opened in outputs/, displayed installed skills through /skills,
  and exited through /quit with status 0.
- Remaining full-project submission requirements are explicitly tracked in main task.md.

- Added a standalone new-user features guide and a 16-case manual QA checklist covering all implemented capabilities.

- Added architecture.md documenting actual execution paths, modules, state, errors, limits, and the test mapping; added an ongoing maintenance checklist.

- Fixed the reported non-Git command; all installed Codex 0.167.0 exec option names are recognized, with 60 passing tests and live C++/JSON verification.

- Implemented Telegram control on feature/telegram-bot with no new runtime dependencies; 100 tests pass, including offline end-to-end message/job/child/result verification. Subsequently, the user confirmed live operation on 2026-11-08.

- On feature/telegram-sessions: local-code pairing, automated protected configuration, and one persistent shared conversation; 126 tests pass. Two real Codex turns retained the same ID/context after a runner/store restart across simulated users. New wizard/pairing awaits live acceptance.

- Prepared four clean WSL worktrees with separate branches, isolated editable environments, and four self-contained handoffs. Each passed the 126-test baseline; the global senai install was unchanged.

## Telegram integration merge (2026-11-09)

Merged feature/integrations, including 26d8da1, in 2e50418. Review fix 7487862 preserves partial reply delivery across upgrades. Scope/readiness checks passed; all 151 regression tests passed on feature and merged main. No live Telegram configuration, state or session was accessed; bot was not restarted.

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

## Confirmed memory learning (2026-11-09)

Integrated 929a2ea in b6c56f7; successful-outcome evaluator wiring 4ffc1aa. Personal facts require explicit user retention confirmation; repetition never confirms. Only app-verified significant milestones qualify automatically. SOUL.md stays human-controlled. Installation-wide memory and frozen session snapshots preserved. Branch readiness/248 tests and combined 370 tests passed. See projectprogress/memory-learning.md. No push, deployment or production bot state used.

## New-user documentation and compatibility audit (2026-11-09)

Refreshed portable README/setup/command/compatibility/architecture/manual acceptance guides. Preserved earlier guides under projectprogress/history and labeled workstream records as historical. Parameterized contributor templates and removed user-wide install advice. Runtime source/scripts contain no developer-specific home paths. Updated CLI help to include memory and cron. Main and isolated fresh-checkout suites: 370 passed each. Local fresh clone dependency/install/entry-point checks passed; host ensurepip limitation is disclosed. No live providers, bot state or services used. No push performed.
