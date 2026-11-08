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
Foreground jobs get priority. Only when its queue is empty does the existing worker execute one cron occurrence. The polling thread drains scheduled delivery independently, including while Codex is busy. A sustained foreground backlog can delay cron and trigger its configured misfire policy. There is no independent hidden execution pipeline.

Scheduled requests use the existing CommandRunner with the same Telegram JobStore/native shared session and execution flags; separate cron UUID/attempt log directories avoid normal-job collisions. Scheduled results use text delivery (image/voice scheduling is not wired). Exact native resume and SENAI_INSTALLATION_ROOT memory behavior are preserved. A configured installation needs an existing frozen snapshot for an existing native session, as documented by memory integration.

Authorization is checked before creation/management, immediately before execution and again before every send chunk. Immutable run/destination snapshots are checked against the configured bot/account/project/scope. Existing Telegram job, pairing, cursor and session schemas are unchanged.

Completion writes its delivery intent atomically in the cron DB. DeliveryWorker resumes pending results after restart without rerunning Codex. Telegram message_id confirms acceptance. A transport-confirmed first-chunk rejection (ok=false, error_code=429) may safely retry up to three total attempts, 60 seconds apart. Network uncertainty, process death or a failure after any accepted chunk requires operator review; it is not automatically replayed. Pause/delete do not retract historical results. Revocation blocks pending sends. Execution retries remain opt-in and can repeat effects.

## Evidence
- Cron branch scope/readiness and 184 offline tests passed before merge.
- Combined suite at the initial integration: 299 tests passed. Supervised-worker milestone: 312 tests passed, including 48 cron feature tests and 29 coordinator cron tests.
- Native subprocess test verifies exact shared-session resume, installation memory injection, private-key exclusion, unchanged pairing/jobs and authorized text delivery.
- Packaging dependency check passed.
- Installed CLI disposable create/show/edit/dry-run/pause/resume/delete acceptance passed with zero execution runs.
- Logs: outputs/cron-combined-regression.log and outputs/cron-integration-green.log.
- Installed CLI evidence: outputs/cron-integration-qa/acceptance.json.
- Live scheduling/channel/daemon acceptance remains NOT RUN.

## Explicit supervised worker (2026-11-09)

Worker implementation: 58109c0. This command is available but has NOT been activated against live services. The following startup is for later explicitly authorized live QA:

    senai cron worker --project PROJECT --telegram-account BOT_ID --execution-timeout 300 --interval 1 --status-interval 5

Use main's activated .venv. Existing local Telegram credentials and the existing project/bot authorization database are required; never put tokens in command arguments. --env-file accepts the existing protected Telegram configuration format. The token's verified bot ID must match BOT_ID. Model/profile/search/skill and --skip-git-repo-check flags are supported. SENAI_INSTALLATION_ROOT, when configured, continues to use the same frozen native-session memory policy.

The standalone worker holds the SAME bot/project lock as the ordinary Telegram bot. Stop that bot gracefully before starting this worker; never run both against the same shared session. It does not poll incoming chats, consume Telegram offsets, regenerate pairing or recover/rewrite normal jobs. It refuses startup while a prior ordinary job is still marked running. Local schedule management remains available in another terminal:
    senai cron --project PROJECT --telegram-account BOT_ID list
    senai cron --project PROJECT --telegram-account BOT_ID runs
    senai cron --project PROJECT --telegram-account BOT_ID deliveries
    senai cron worker-status --project PROJECT --telegram-account BOT_ID

The worker consumes the ACCOUNT store, not PROJECT/outputs/.senai-cron/cron.db. Schedules created through /cron already have the required immutable account/project/scope/recipient metadata. Local CLI creation for this store must explicitly select --telegram-account, scope telegram-shared and the correct delivery target; arbitrary metadata never grants authorization. Default local-scope schedules are not silently adopted into a Telegram shared session.

Two supervised threads run independently: one serial execution loop and one durable delivery loop. A previously completed result can be sent while another Codex request is busy. Each loop polls at --interval seconds (positive, max 60); status snapshots are emitted at --status-interval (positive, max 60). Only one native task and one delivery are active in this process. A loop/status failure stops the supervisor with exit code 1; startup errors return 2. Status is printed and atomically persisted with mode 0600 to the account cron directory's worker-status.json. Counts use aggregate DB queries rather than loading all historical results.

--once claims at most one due execution and drains currently due delivery independently. It does not wait for delayed retry times. Without --once, the loop remains in the foreground. No crontab/systemd installation or background autostart is added.

### Bounded execution and shutdown
The worker uses the existing CommandRunner/Codex wrapper and exact Telegram shared native session. --execution-timeout defaults to 300 seconds (positive, max 3600). Native execution runs in a POSIX process group. On deadline, that group receives TERM then KILL cleanup; captured session identity is retained where available. The occurrence becomes unknown and its schedule is paused atomically, bypassing all execution retries. A failure notification is queued durably. External effects and independently detached processes cannot be rolled back; this is not exactly-once execution.

Ctrl+C or SIGTERM stops new claims, prints stopping status, and waits for active bounded execution and bounded network/DB calls to settle. Any result still pending delivery remains saved for the next start. Do not force-kill and immediately reclaim work: effects may already exist.

The ordinary bot's opt-in --enable-cron mode also now separates execution from delivery: existing execution worker runs due tasks only when foreground work is idle; its polling thread drains delivery independently. --cron-execution-timeout sets the scheduled native deadline (default 300). This alternative retains chat management and incoming messages; it must not run alongside the standalone worker.

### Recovery and uncertainty
- pending delivery: restart the same worker/configuration; it sends the saved result without rerunning Codex.
- running execution after process death: never automatically reclaimed. Prove the old worker/descendants stopped, inspect logs and external effects, then use the existing local interrupt management only after review.
- unknown execution: schedule stays paused. Review effects before deliberately editing/rearming and resuming; the same occurrence is not silently retried.
- delivering after sender death: blocked, not reclaimed. After establishing that sender stopped, the existing Store.abandon_delivery API fences its token and records unknown. No automatic resend is added.
- unknown send: investigate acceptance before any deliberate replacement request. Partial sends can duplicate if manually replayed.
- paused jobs never execute. Pause/delete do not retract already queued results; authorization is checked on every send chunk.
- RetryDelivery is raised only for a validated Telegram rejection (ok=false, error_code=429) before any chunk was accepted. An HTTP status alone, malformed response, network error or partial send remains unknown. Certified retry is bounded to three total attempts, 60 seconds apart.

### Offline acceptance
312 combined tests passed, including 13 new supervisor tests. A disposable end-to-end test invokes the real wrapper/CommandRunner subprocess path with an offline Codex executable and authorized offline Telegram adapter. Its result and delivery history persist; a second worker start sends no duplicate and performs no second execution. Tests cover independent delivery during a blocked task, paused jobs, process deadlines, unknown/in-flight recovery, singleton locking, transport certainty, SIGTERM and status failures.

Evidence: outputs/cron-supervised-regression.log, outputs/cron-supervisor-green.log and outputs/cron-supervisor-qa/acceptance.json. Real external Codex/Telegram scheduled execution/delivery remains NOT RUN pending explicit user instruction. No production bot state, live schedules or services were activated.
