# Cron integration notes

No shared patches applied. Coordinator should route senai cron to senai.cron.__main__.main.
Inject authorized existing Codex execution/session adapter into Worker; preserve configured
session policy. Do not import sibling branches or start a separate hidden agent pipeline.

Use DeliveryWorker(store, send) for routing: send(item) receives target dict, completed run,
stable item id, attempt and ownership token. Decode run.snapshot for project/scope. Authorize
recipient/project/scope at creation AND send time; target JSON alone conveys no authorization.
Return only on confirmed transport acceptance. Raise RetryDelivery only when the transport
can certify no acceptance; ambiguous errors must remain unknown. Configure the same bounded
retry policy on every sender restart. No production adapter or permission model is added here.

Additive storage upgrade: nullable schedules.delivery_target plus deliveries table in the cron
DB. Existing rows remain untargeted; no historical outputs are retroactively enqueued. Initialize
upgrade before launching concurrent workers. Telegram DB untouched. Calendar dependencies are pinned in requirements-cron.txt; install only into this worktree .venv.

Pause/delete do not revoke already queued results; sender adapter must enforce current access.
No live channel checks performed. Calendar cron/misfire controls are implemented. Chat commands remain coordinator work.

Schema contract v3: nullable cron; misfire='coalesce' and grace_seconds=120 defaults preserve
old records; misfires table added. Calendar dependency croniter==6.2.4 plus pinned transitive
python-dateutil/six/tzdata. Coordinator consolidates packaging later. Chat-created time-sensitive
reminders should explicitly choose misfire='skip' with a user-appropriate grace; use coalesce
for useful late reports. Show timezone and next run when confirming schedule creation.

Safe edit API for chat adapters: get(schedule_id) -> schedule including revision and
next_due_local; update(schedule_id, *, expected_revision, **changes) -> updated schedule.
Authorize project/scope/owner before lookup and update. Carry revision from the user's viewed
schedule; show conflicts and ask them to review fresh state instead of blindly retrying edits.
Do not alter another user's project/scope/destination. Reject edits while running/retrying.
Schedule confirmation should show name, local next time, timezone, recurrence, misfire policy,
destination and revision. Rule/timezone changes require explicit aware at; metadata-only
edits must not rearm completed one-shots. Existing results/delivery snapshots stay unchanged.
Schema v4 adds revision INTEGER NOT NULL DEFAULT 1, preserving old data. No new dependencies.
Shared chat routing is deliberately a coordinator proposal; this feature does not modify it.

## Coordinator integration on main

Merged feature/cron through 46e739d (6a50762); wiring 7e6cf18. Consolidated pinned dependencies, shared senai cron management, opt-in /cron management, existing serialized native-session execution, and currently authorized durable text delivery. All 299 combined tests passed; installed CLI fixture QA and dependency checks passed. Production state/services untouched; live scheduling remains disabled and unverified. See projectprogress/cron.md for usage and limits.

Feature-local CLI main now accepts optional keyword-only store_factory for the shared --telegram-account store selector; prior callers retain their default behavior. Telegram activation requires --enable-cron. CommandRunner shares the existing native session store; the existing worker serializes foreground and cron execution. DeliveryWorker uses confirmed authorized text delivery with conservative unknown outcomes. Account-specific cron databases are additive and separate from Telegram state.

## Supervised cron worker (2026-11-09)

Added explicit senai cron worker / worker-status commands in 58109c0. Execution and delivery loops are independent; scheduled native execution has a configurable process-group deadline. Unknown execution pauses the schedule and bypasses retries; ambiguous sends remain unknown. Singleton locking preserves Telegram's exact shared-session policy. Existing bot --enable-cron mode also drains delivery independently. All 312 tests passed, including disposable offline pipeline/authorized-delivery and restart acceptance. Live acceptance remains pending explicit instruction; production services/state were not used. Startup, shutdown and recovery: projectprogress/cron.md.
