# Architecture

Product usage: [README](../README.md). Verification: [all-feature guide](all-features-demonstration.md).

## Ordinary execution

~~~text
CLI / Telegram message
  -> saved startup defaults + current authorization
  -> validated PROJECT/outputs workspace
  -> frozen installation snapshot + explicit immutable registry-skill context
  -> existing Codex CLI / exact native session UUID
  -> durable result + outcome records
  -> confirmed/trusted learning + authorized delivery
~~~

The CLI accepts quoted requests or stdin. senai chat calls the same execute_request
function with persisted local turns/native IDs, including skill/memory context and
outcome learning. It no longer launches native interactive Codex directly. codex.py runs native execution and captures
the final answer separately from diagnostics; failures propagate. JSON/native options
are preserved within workspace constraints. Native interactive passthrough/review delegate
to Codex separately and do not inject Senai semantic memory. outputs/ is a scope policy,
not a separate filesystem jail; review is Git scoped.

## Modules and boundaries

| Module | Responsibility |
| --- | --- |
| cli.py, defaults.py, onboarding.py, chat.py, chat_store.py | Routing, saved configuration, setup and short commands |
| workspace.py, prompts.py, codex.py, native.py | Workspace validation, instructions, native process/option handling |
| memory/, memory_runtime.py, outcome_learning.py | Human profiles, detailed facts, frozen sessions, confirmed/trusted learning |
| skill_ui.py, skill_context.py, skills/ | Explicit package selection, immutable context, digest outcomes, checked proposals/history |
| telegram/ | Private authorization/pairing, durable jobs, conversations, text/media/voice |
| cron/ | Time parsing/drafts, durable schedules/claims/results/outbox and delivery primitives |
| telegram_composition.py | Conversation/cron parser composition, operator policy, shared execution gate |
| cron_routing.py, cron_runtime.py, cron_supervisor.py | Authorized account stores, existing executor adapter, supervised loops |

## Installation memory

One installation has one owner; USER.md/MEMORY.md/SOUL.md are shared across its projects.
Fresh sessions load current profiles. Resumed sessions reuse their frozen native snapshot.
Human commands explicitly append profiles, including SOUL; automatic learning cannot
modify SOUL. Personal facts require confirmation. Only app-verified significant milestones
qualify automatically. Model prose/uploaded JSON never verifies itself. See
[learning contract](memory-learning.md) and [memory module](../senai/memory/README.md).

## Skill context and learning

Accepted project-local skills are selected explicitly. Each ordinary request copies exact
version/digest instructions/resources into bounded reference context before the existing
executor. Outcomes retain that digest; absent an independent checker they are unverified.
Advanced authoring runs retain their own evidence reports. Stage/review proposals remain
inactive until independent passing checks and explicit acceptance/activation. Rollback
restores accepted history. Obsidian export is explicit one-way projection, not a watcher.
See [skills module](../senai/skills/README.md).

## Telegram and main service

senai start (or senai telegram start) runs the configured foreground Telegram/cron service.
The main thread polls input and drains delivery; one serialized execution worker checks
due cron before ordinary queued requests. Active calls are not preempted; sustained cron
backlog can delay manual work. Delivery stays independent of native execution.

All paired accounts share native model context/workspace. Private delivery is not model
isolation. Authorization is checked before execution and delivery. Text chunks, image
snapshots and voice fallback choices persist across retries. Voice is optional and its
key remains independent of native Codex authentication.

/new requires explicitly configured operator permission, an idle shared gate and a
confirmation. It archives the old active mapping; jobs/history/pairing/media remain.
Foreground execution, cron claims and session switches share the gate. Startup project,
installation/timezone are pinned so external defaults edits cannot retarget runners.
See [Telegram module](../senai/telegram/README.md).

## Scheduling and uncertainty

~~~text
guided CLI/chat fields -> authorized destination + preview -> explicit confirmation
  -> durable schedule -> atomic due claim -> same authorized Codex/session runner
  -> result + delivery intent in one transaction -> independent authorized sending
~~~

Standalone cron worker is an alternative supervisor, not a second bot. It shares the
singleton lock/session and does not poll incoming Telegram. Management never starts a
worker. Deadlines pause unknown executions; ambiguous/partial sends need review.
Certified-not-accepted sends alone can safely retry. External effects are not guaranteed
exactly once. See [cron module](../senai/cron/README.md) and [recovery](cron-recovery.md).

## Storage and lifecycle

| Scope | Data |
| --- | --- |
| Local configuration | Non-secret saved defaults; protected credentials outside Git |
| INSTALLATION/outputs/.senai-memory/ | Human profiles, detailed facts and frozen native snapshots |
| PROJECT/outputs/ | Generated artifacts, jobs/conversations/media, cron state, skill registry/settings/context |
| Separate module SQLite stores | Additive module-local migrations; no shared global migration counter |

CLI chat transcripts live in PROJECT/outputs/.senai-chat/history.sqlite3, partitioned
by installation root and protected by a project-local chat lock. Pending turns persist
before execution; final replies persist before display. Crash-interrupted turns become
unknown, never automatic retries. /new archives the prior conversation by retaining it
and selecting a fresh one. Telegram state/session mappings stay separate.

See [four module sequence diagrams](sequence-diagrams.md).

No import/install starts a poller, schedule, daemon or API connection. Ctrl+C/SIGTERM
stops new claims and waits for bounded active work. Saved pending results survive restart.
No OS service/autostart is installed. Do not delete state while services run.
