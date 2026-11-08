# Cron changes

2026-11-09
- c77df9e: durable schedules, atomic due claims and injected worker.
- 176c97a: feature-local management/dry-run CLI.
- Current milestone: transactional durable delivery outbox; token-checked completion;
  bounded certified-not-accepted retries; unknown outcomes never automatically resent.
- Studied official Hermes jobs.py, scheduler_tick.py, missed_runs.py and delivery_queue.py.
  References: https://github.com/NousResearch/hermes-agent/tree/main/cron and
  https://hermes-agent.nousresearch.com/docs/developer-guide/cron-internals .
  Source review only; Hermes was not installed or executed.

- 8335f7c: completed outbox/recovery milestone; test and API contract in delivery.json.

2026-11-09 calendar/misfire milestone:
- TDD red: missing cron/misfire arguments; then failing CLI flag and random-expression checks.
- Add bounded five-field wall-clock matching, gap skip/fold=0 DST policy, skip/coalesce rules,
  atomic missed-slot history and non-mutating preview. Old schedule defaults are preserved.
- Add pinned feature-only calendar dependency; no global or shared packaging edits.

- aaae7f6: calendar/misfire implementation; 171 offline tests pass on exact commit.

2026-11-09 safe management:
- TDD red: get/update APIs absent, then show/edit CLI absent.
- Atomic revision-checked edits reject stale editors and active/retry work; expose local next
  time; preserve paused/consumed schedules and historical delivery snapshots.
- Additive revision migration; shared validation for create/edit. No dependency changes.
