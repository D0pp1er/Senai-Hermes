> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

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

## Friendly UX contract (implemented public API, 2026-11-09)
- parse_when(text, *, now, timezone) -> aware datetime; raises TimeClarification(ValueError)
  with actionable text for unsupported/ambiguous/past/year/DST input. Clock always injected.
- Destination(key, label, scope, target, execution_hint): immutable adapter-provided option.
  target is a JSON-serializable dict; adapter is responsible for authorization and store choice.
- build_draft(*, name, prompt, when, recurrence, destination, now, timezone,
  parser=parse_when) -> ScheduleDraft; pure, no writes. recurrence: once/daily/weekly,
  every N seconds/minutes/hours/days, or cron EXPR. First-run time is always asked separately.
- preview_draft(draft) -> str: full local time/zone, recurrence, destination and execution hint.
- commit_draft(store, draft, *, project, now, confirmed) -> str | None:
  confirmed=False writes nothing; confirmed=True revalidates future time then Store.create.
  Adapter owns duplicate-update suppression, per-user drafts, timeout and /cancel state.
- cron.__main__.main(argv=None, *, store_factory=None, stdin=None, stdout=None,
  stderr=None, clock=None, timezone=None, destinations=()) -> int.
  destinations are trusted Destination options for the selected store; timezone overrides saved
  defaults. No destination adapter means wizard refuses without creating an unsendable task.
  Coordinator must inject account-specific authorized options AND matching store_factory,
  or a real local executor/delivery adapter; never guess a local delivery path or start a worker.
These implemented signatures are the published integration contract; shared adapters remain
coordinator/integrations-owned. Do not copy a second time parser into Telegram.

Friendly UX implementation commits: fa67c50 (parser/drafts), 20f3245 (wizard/module README).
Exact code commit 20f3245a0848655f681dceb7b82280b7de71f12b passed 401 full offline tests. Real PTY acceptance with a fake
route saved one disposable schedule and zero execution runs. Runtime/delivery/worker code and
DB schemas were untouched. Coordinator may now compose these helpers; no Telegram UX adapter
is changed here. Missing route returns a clear error with no save. No live friendly UX checks.

## Friendly scheduling integration (2026-11-09)

Merged c240922 in cdd0375; coordinator wiring ad81604. Feature readiness and 401 tests
passed again; 409 combined tests passed, including 8 destination/conversation tests.
No live service, schedule execution or provider call was activated.

After saved setup and Telegram pairing:
    senai cron create
asks name, task, first run (for example today at 10pm, tomorrow at 1 am, in 2 minutes),
recurrence, authorized destination, then a complete timezone-aware preview and yes/no.
Nothing is saved until confirmation. Non-TTY use requires the documented full flags.
The CLI reads existing local authorization without polling Telegram. It supplies matching
Destination options and the account-specific authorized store. Revocation is rechecked
on create. No usable destination means a clear error, not an unsendable local task.
With one eligible account, account-store management is selected automatically; multiple
accounts require an explicit selection. --telegram-account remains available.
--local selects the advanced local store explicitly. Full create flags with --scope
retain their legacy local behavior unless --telegram-account is explicitly selected.

In a cron-enabled bot:
    /cron create
asks name -> task -> first run -> repeat -> preview -> yes/no. Delivery is fixed to
that authorized private chat. /cancel discards the ephemeral draft; timeout is ten
minutes from creation. Drafts are per-user and disappear on process restart.
Duplicate updates do not create twice. Revocation cancels the draft. Invalid time/
repeat input retries the same question with actionable help. Confirmation revalidates
the previewed fixed instant and authorization. JSON advanced creation remains supported.

Both interfaces consume shared parse_when/build_draft/preview_draft/commit_draft; there
is no second date parser. Existing claim/retry/deadline/delivery/session semantics remain.
Saving does not start a worker. Normal senai telegram start opts into the existing cron
loop; no bot was started or restarted during this integration.

Evidence:
- feature outputs/cron-qa/coordinator-ux-review.log
- main outputs/friendly-routing-red.log and friendly-routing-green.log
- main outputs/friendly-cron-combined.log

Manual checks for later: create from CLI and Telegram, cancel, enter an invalid/past time,
confirm the resolved local timezone/time and destination, and verify list/show use the
same account store. Live UX acceptance is still pending explicit operator testing.
