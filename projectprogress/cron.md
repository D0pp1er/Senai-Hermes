# Cron integration

Integrated feature/cron through 46e739d. Merge: 6a50762; coordinator wiring: 7e6cf18.

## Current state
Live scheduling is disabled by default. No production bot restart, OS cron/systemd change, real scheduled execution or message delivery was performed. Tests use fake clocks, fake Codex/Telegram and disposable stores. No exactly-once external execution or delivery guarantee.

Dependencies from requirements-cron.txt are consolidated in pyproject.toml and installed only in main's .venv. Use that environment's senai command; the global editable installation was not modified.

## Safe local management
From /home/rk/SentiensHermes/senai, activate .venv. The management commands do not start a worker:
    senai cron --project PROJECT list
    senai cron --project PROJECT dry-run
    senai cron --project PROJECT create --name NAME --prompt TASK --scope local --at 2035-01-01T09:00:00+06:00
    senai cron --project PROJECT show ID
    senai cron --project PROJECT edit ID --expected-revision N --prompt NEW_TASK
    senai cron --project PROJECT pause ID
    senai cron --project PROJECT resume ID
    senai cron --project PROJECT delete ID

Create supports --every SECONDS or --cron '0 9 * * *', --timezone IANA (default Asia/Dhaka), --misfire skip|coalesce, --grace-seconds N and opt-in execution retries. --at must include a UTC offset. Local defaults retain the feature contract (coalesce); time-sensitive reminders should explicitly use skip.

Default local store: PROJECT/outputs/.senai-cron/cron.db.
Telegram store: PROJECT/outputs/.senai-cron/telegram/BOT_ID/cron.db.
To inspect/manage the same Telegram schedules locally:
    senai cron --project PROJECT --telegram-account BOT_ID list
    senai cron --project PROJECT --telegram-account BOT_ID deliveries
All feature-local management commands remain available; local operators are trusted and must confirm old workers stopped before interrupt/abandon recovery. A bot store is not automatically populated from old local schedules.

## Optional chat management (not activated)
A future explicitly authorized bot start can add --enable-cron to its existing command. This opt-in adds /cron handling and an idle callback on its existing single execution worker. It creates no second poller or scheduler daemon.

Authorized private-chat syntax:
    /cron
    /cron create {"name":"check","prompt":"Summarize project status","at":"2035-01-01T09:00:00+06:00"}
    /cron list
    /cron show ID
    /cron edit ID REVISION {"prompt":"Updated task"}
    /cron pause ID
    /cron resume ID
    /cron delete ID
    /cron runs
    /cron deliveries

Create JSON also accepts timezone, every OR cron, misfire, grace_seconds, retries and retry_delay. Chat defaults to skip after 120 seconds. Confirmations show ID, name, next local time, timezone, recurrence, misfire, this-chat destination and revision. Management is explicit structured input, not a model's inferred intent. Owner/account/project/scope are fixed by the adapter; chat cannot override destination or manage another user's schedules. Updates are deduplicated using the existing Telegram cursor; a crash between cursor consumption and management commit can require user inspection/reissue. Stale edits are rejected for fresh review.

## Execution, memory and delivery
Foreground jobs get priority. Only when its queue is empty does the existing worker execute one cron occurrence, then drain one delivery. A sustained foreground backlog can delay cron and trigger its configured misfire policy. There is no independent hidden execution pipeline.

Scheduled requests use the existing CommandRunner with the same Telegram JobStore/native shared session and execution flags; separate cron UUID/attempt log directories avoid normal-job collisions. Scheduled results use text delivery (image/voice scheduling is not wired). Exact native resume and SENAI_INSTALLATION_ROOT memory behavior are preserved. A configured installation needs an existing frozen snapshot for an existing native session, as documented by memory integration.

Authorization is checked before creation/management, immediately before execution and again before every send chunk. Immutable run/destination snapshots are checked against the configured bot/account/project/scope. Existing Telegram job, pairing, cursor and session schemas are unchanged.

Completion writes its delivery intent atomically in the cron DB. DeliveryWorker resumes pending results after restart without rerunning Codex. Telegram message_id confirms acceptance. A first-chunk 429 may safely retry up to three total attempts, 60 seconds apart. Network uncertainty, process death or a failure after any accepted chunk requires operator review; it is not automatically replayed. Pause/delete do not retract historical results. Revocation blocks pending sends. Execution retries remain opt-in and can repeat effects.

## Evidence
- Cron branch scope/readiness and 184 offline tests passed before merge.
- Combined suite: 299 tests passed, including 48 cron feature tests and 16 coordinator tests.
- Native subprocess test verifies exact shared-session resume, installation memory injection, private-key exclusion, unchanged pairing/jobs and authorized text delivery.
- Packaging dependency check passed.
- Installed CLI disposable create/show/edit/dry-run/pause/resume/delete acceptance passed with zero execution runs.
- Logs: outputs/cron-combined-regression.log and outputs/cron-integration-green.log.
- Installed CLI evidence: outputs/cron-integration-qa/acceptance.json.
- Live scheduling/channel/daemon acceptance remains NOT RUN.
