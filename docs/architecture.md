# Architecture

CLI input -> validation/workspace -> prompt -> optional installation snapshot ->
existing Codex execution -> native UUID binding/final response -> successful-outcome learning.

Projects select outputs/. The explicit installation root independently selects global
USER.md/MEMORY.md. Fresh sessions read current facts; resumed sessions reuse frozen
snapshots. Personal facts need confirmation; automatic milestones need app-supplied
verification checks. SOUL.md remains human-controlled.

Telegram private input -> current pairing/authorization -> durable serialized jobs ->
CommandRunner/exact shared native session -> saved response/media -> authorized delivery.
Voice audio/fallback choice persists across retry. Optional credentials live outside
Git and load at startup.

Cron -> atomic claim/immutable destination -> existing authorized session runner ->
durable result/outbox -> independent DeliveryWorker. Deadlines pause uncertain
executions; ambiguous sends remain unknown. Standalone worker shares the bot lock.
Installation starts no worker, poller or external connection.

Native chat/review/forwarding do not inject Senai memory. outputs/ is a workspace
policy, not an independent jail. See detailed [cron](../projectprogress/cron.md) and
[learning](../projectprogress/memory-learning.md) contracts.
