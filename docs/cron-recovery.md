# Cron operation and recovery

Basic wizard and management: [README](../README.md#5-scheduling-without-json-or-iso-timestamps).
Time grammar, recurrence and module architecture: [cron module](../senai/cron/README.md).
Manual acceptance: [all-feature guide](all-features-demonstration.md#10-actual-scheduled-executiondelivery-r18r24).

## Stores and authorization

- Account store: PROJECT/outputs/.senai-cron/telegram/BOT_ID/cron.db.
- Advanced local store: PROJECT/outputs/.senai-cron/cron.db; no automatic local execution/delivery adapter.
- Friendly CLI creation selects an authorized destination and its matching account store.
  One eligible account is automatic; otherwise select it, or use --telegram-account ID.
- --local selects management-only local storage. Legacy full create --scope forms keep
  local behavior unless an account is explicitly selected. Stores are not auto-migrated.
- Creation, execution and each delivery chunk recheck authorization and pinned destination.
  User-supplied JSON never grants recipient access.

## Start and stop

After setup/pairing, run senai start (or senai telegram start) for the foreground
Telegram/cron service. Due cron work has execution priority; delivery drains independently.
A running task is not preempted; continuous due cron backlog can delay ordinary requests.
Saving/listing a schedule never starts execution.

Alternatively, stop the bot and run a standalone account supervisor:

~~~text
senai cron worker --telegram-account BOT_ID
senai cron worker-status --telegram-account BOT_ID
~~~

Never run both for the same project/account: they share singleton lock and native
session. Standalone mode does not poll Telegram, consume update offsets or regenerate
pairing. It refuses prior ordinary jobs still marked running. Both runners use the
existing authorized Codex pipeline, exact shared session, memory and selected skills.
Scheduled delivery currently supports text only.

Standalone --execution-timeout defaults to 300 seconds, maximum 3600. --interval and
--status-interval are positive and at most 60 seconds. --once claims at most one due
execution and drains currently due delivery; it does not wait for delayed retries.
Normal Telegram mode uses --cron-execution-timeout for scheduled execution.
Status is emitted and atomically saved with mode 0600 to account worker-status.json.
A loop/status failure stops the supervisor; startup failure returns 2.
Ctrl+C/SIGTERM stops new claims and waits for bounded active execution/network work.
No OS cron, systemd service or boot autostart is installed.

## Durable result and delivery

Completion persists result and delivery intent atomically in the cron DB. Pending
outbox entries survive restart without rerunning completed Codex work. Delivery runs
independently of task execution. Session switches share the claim/execution gate.
A selected installation needs its existing session's frozen snapshot; use an authorized
fresh transition for old sessions lacking one, not database deletion.

Only a validated Telegram rejection (ok=false, error_code=429) before any accepted
chunk certifies a safe retry: at most three total attempts, 60 seconds apart. HTTP
status alone, malformed response, network error and partial acceptance remain uncertain.
Execution retries are opt-in and can repeat external effects. External execution and
delivery are not guaranteed exactly once.

## Recovery decisions

| State | Operator action |
| --- | --- |
| Pending delivery | Restart same worker/configuration; saved result sends without another model run. |
| Running execution after process death | Establish old worker/descendants stopped; inspect logs and external effects before deliberate local interrupt management. Never automatically reclaim. |
| Deadline/unknown execution | Schedule is paused; inspect effects before explicitly editing/rearming/resuming. Same occurrence is not silently replayed. |
| Delivering after sender death | Establish sender stopped; trusted Store.abandon_delivery API fences its token and records unknown. No automatic resend. |
| Unknown/partial send | Investigate remote acceptance before a deliberate replacement. Replaying can duplicate accepted content. |
| Paused/deleted schedule | Future claims stop; already queued results are not retracted. Authorization still gates every send. |
| Revoked recipient | Pending sending is blocked; do not bypass authorization during recovery. |

A deadline sends TERM then KILL cleanup to the native process group and persists unknown
with a paused schedule and failure notification. Independently detached effects cannot
be rolled back. Never delete state while a service is active. Use disposable fixture
regressions for crash/partial-send/revocation tests, not production fault injection.
