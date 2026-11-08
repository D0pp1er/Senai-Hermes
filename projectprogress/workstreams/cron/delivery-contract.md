# Safe scheduling and delivery contract

2026-11-09: first durable-delivery milestone; no live scheduling enabled.

An occurrence is identified by schedule ID + scheduled_at UTC timestamp. Claiming it creates
its durable run and advances the schedule in the same SQLite transaction. Never automatically
reclaim an execution whose external effects may already exist. Explicit recovery requires
proving the old worker stopped. Execution retries are opt-in and can repeat external effects.
Pending retries block later occurrences of that schedule; separate schedules may execute concurrently.

Completion and its outbox insertion commit together, or neither commits. A delivery request
holds the immutable destination snapshot and references the durable result. Unique run_id
prevents multiple queued sends for one run. A targeted task queues even without an attached
sender. DeliveryWorker drains independently after restart, without calling the executor.
Pending delivery remains valid after pause/delete: those operations control future execution,
not already completed results. Revocation must be enforced by the delivery adapter at send time.

Send claim: pending -> delivering, increment attempt, issue a random ownership token.
Successful callback return -> delivered. RetryDelivery certifies no remote acceptance and
permits bounded delayed retry (default three total attempts, 60 seconds apart). Any other
exception -> unknown; never automatically resend. Process death while delivering leaves it
blocked. After confirming the sender stopped, abandon_delivery marks unknown and invalidates
its token. A late old sender cannot commit an outcome with that token. This fences bookkeeping,
not remote effects; do not abandon a live sender. Transport success means adapter-confirmed
acceptance, not that a person read the notification. No exactly-once external-send promise.

Existing Worker(store, executor, deliver) callback keeps receiving completed run dicts;
its callbacks now use the outbox, including idle ticks after restart. New adapters should use
DeliveryWorker(store, send) to receive target + run + stable delivery ID explicitly.
A legacy untargeted callback needs the same explicit destination configuration after restart.

Calendar/misfire milestone: five-field cron, explicit coalesce/skip with grace_seconds, and durable
misfire records are now implemented. See architecture.md for DST, bounded counting and exact
policy. Compatibility default coalesce still allows indefinitely late one-shots; use skip for
time-sensitive reminders. Chat management remains coordinator integration work.

Acceptance evidence: tests/cron/test_delivery.py covers restart, competing send claims,
transaction rollback, unknown send, stopped sender token invalidation, bounded certified retry,
old DB preservation, legacy callback recovery and no delivery before terminal execution.

Safe editing: update requires the last observed revision and refuses in-flight/retry work.
Completed runs and delivery destinations are immutable snapshots. Changing schedule text or
destination never rewrites pending notifications from previous completed runs. Pause/resume
remains separate from edit. A consumed reminder is rearmed only by explicitly setting at.
