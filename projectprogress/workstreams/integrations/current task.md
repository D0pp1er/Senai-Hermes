# Current task

Telegram UX implementation complete for feature-owned APIs; final verification/readiness
records are pending. Cron conversation commit: 8d59901. Added safe /new and explicit
installation pin hook, with senai/telegram/README.md combining Usage and Architecture.

Coordinator still supplies the cron parser, binds authorized schedule creation, wraps
both runners with the same gate plus scheduler-idle predicate, passes explicit /new
operator policy and frozen startup installation/timezone, and wires the outer router.
No shared source/defaults/aliases changed; no parser invented. No production/live activity.
