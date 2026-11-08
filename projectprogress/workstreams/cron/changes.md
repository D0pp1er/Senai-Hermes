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
