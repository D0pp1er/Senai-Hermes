# Cron architecture
Store owns an independent SQLite database; schedules carry canonical project, explicit scope,
prompt, timezone (default Asia/Dhaka), UTC due instant and enabled flag. Runs retain a
schedule snapshot even after deletion. BEGIN IMMEDIATE serializes claims across processes.
Worker.tick claims at most one run and invokes injected executor/run-result delivery callbacks.

Recurring schedules use elapsed seconds, not calendar cron expressions. UTC instants avoid
host timezone dependence; callers must supply aware start datetimes (DST fold explicit).
Missed intervals coalesce into one oldest due occurrence; the next due remains on the original
interval grid strictly after claim time. One-shot schedules are consumed at claim.
Running/retry rows block overlapping occurrences of that schedule. Pause prevents new claims
including retries; delete preserves run history. Already running work is not cancelled.
Retries default to zero; opt-in 0..10 additional attempts use a fixed positive delay, with the
same durable run ID and incrementing attempt. Retry may repeat external effects.

Crash recovery is deliberately manual: no lease expiry automatically re-executes work.
After proving the old worker stopped, interrupt marks a running row interrupted. A consumed
one-shot is not retried; recurring schedules can subsequently claim the next due occurrence.
SQLite claims are atomic, but arbitrary executor effects are not exactly once. A crash after
an external effect and before saving success leaves an ambiguous running run. Delivery is
best effort after durable completion; failure is recorded, without re-execution or automatic
redelivery. A crash before delivery can lose notification; consumers can inspect run history.

No dependencies beyond Python standard library/system IANA zoneinfo data. This is a new
feature-local database, not a migration of Telegram state. Shared CLI routing remains unwired.

CLI: .venv/bin/python -m senai.cron --project <directory> <command>.
Management and dry-run only; does not invoke Codex. Dry-run is an advisory snapshot,
not a reservation. Create requires an offset-aware ISO start; timezone is persisted metadata.
