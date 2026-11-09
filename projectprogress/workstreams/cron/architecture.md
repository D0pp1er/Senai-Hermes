> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

# Cron architecture

Store owns a feature-local SQLite DB under <project>/outputs/.senai-cron/. Importing modules
creates no DB, threads or schedules. Store construction additively upgrades its own tables;
BEGIN IMMEDIATE serializes migration column checks and all execution/delivery claims.

Schedules carry canonical project, explicit scope, prompt, IANA zone (default Asia/Dhaka),
enabled flag and UTC next_due. Runs retain immutable snapshots after schedule deletion.
Worker invokes injected execution; DeliveryWorker invokes injected transport independently.
Completion and delivery enqueue are one transaction. See delivery-contract.md for send recovery.

Calendar helper uses pinned croniter over local naive wall clocks, then explicitly resolves
fold=0 and validates by a UTC round trip. Nonexistent wall times are skipped; repeated wall
minutes run once at their earlier occurrence. --at is an aware lower bound for cron (inclusive),
a due instant for one-shots/intervals. --cron and --every cannot coexist. Five-field cron supports
ordinary ranges/lists/steps and month/weekday names; DOM and DOW use standard OR semantics.
Seconds/year fields, macros, hashed/random fields and special L/W/# syntax are rejected.
Calendar matching searches at most eight years and 1500 wall candidates; unreachable dates
are rejected before creation. Elapsed intervals preserve duration independently of DST.

Claim atomically creates the run and moves next_due strictly after the injected clock.
Running/retry rows block overlap for that schedule. Execution retries are opt-in (0..10), fixed
positive delay, same run ID and incremented attempt. Unknown execution effects are never
reclaimed automatically. Operator interrupt requires verifying the old worker has stopped.

Misfire policy is coalesce (compatibility default) or skip. Skip suppresses a due occurrence
when now-first_due > grace_seconds; equality still runs. Grace is 0..86400 seconds, default 120.
A recurring backlog is always collapsed, never replayed. Coalesce executes the oldest due
occurrence once and records other collapsed slots. Skip executes none and records the gap.
A skipped one-shot is retired (next_due=NULL) without execution/delivery. Schedule advance,
misfire event and optional run insertion commit atomically. Events retain history after deletion.
Intervals count exactly; calendar enumeration stops at 1000 due slots, with count_capped=1
meaning missed_count is a lower bound (999 collapsed, or 1000 skipped). A late single catch-up
can record missed_count=0 because it ran. Claim examines at most 100 schedules per call.

Pause blocks future claims including retries, without cancelling active execution or delivery.
Delivery adapters must enforce current authorization at send time. CLI management and advisory
dry-run start no executor. Dry-run shows due, would_skip and ready retries without reserving work.
No chat/production adapter or always-on scheduler is integrated; shared CLI wiring is coordinator-owned.

## Safe schedule management
Store.get(id) returns the saved row plus next_due_local (ISO instant in its IANA zone).
Store.update(id, *, expected_revision, **changes) uses a single write transaction to check
revision, reject active/retry work, validate all fields and update atomically. Creation starts
at revision 1; pause/resume, due advance, retry claim and edits increment it. A stale editor
must read again. Project/scope/identity/enabled/DB fields cannot be edited through update.
Temporal rule or timezone changes require an explicit aware at. Metadata-only edits preserve
next_due exactly, including NULL for consumed one-shots, and preserve enabled state.
Completed run snapshots and already queued destinations never change. Editing a destination
changes future occurrences only. CLI show/edit expose these APIs; --expected-revision is
required. --cron/--every/--once replace the recurrence kind, with --at required for a change.
