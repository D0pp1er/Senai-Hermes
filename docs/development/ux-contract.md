# UX redesign contract v1

User goal: one configured project, many native sessions, one installation owner.
Manual QA confirmed real Telegram scheduled delivery and edited global profile recall.
Actual latest voice playback was not confirmed. The QA checkout was
/home/rk/Senai-Hermes-manual-qa; development remains in the assigned worktrees.

## Shared defaults (coordinator implemented)
senai.defaults:
- config_path(environ=None) -> Path
- load_defaults(*, environ=None) -> dict
- save_defaults(value, *, environ=None) -> Path
- apply_defaults(argv, value) -> list[str]
Non-secret schema: project and installation (absolute existing directories),
timezone (IANA), skip_git_repo_check (bool). Store defaults at XDG_CONFIG_HOME/
senai/defaults.json; SENAI_CONFIG overrides the file for tests/separate installs.
No credentials in this file. No import-time writes or environment mutation.
Explicit flags override saved settings; explicit project overrides do not inherit
saved non-Git trust. Unconfigured legacy invocations remain compatible.
The installation is explicitly chosen during setup and saved, not inferred per request.

Coordinator owns senai/defaults.py, onboarding.py, root cli.py, packaging, setup script,
cron_runtime/supervisor and cross-feature composition tests. Feature chats must not edit
these shared files. Propose hooks in integration-notes.md; coordinator wires them.
Read these APIs as implemented; report missing seams instead of inventing alternatives.

## Target commands
bash scripts/setup_senai.sh: venv/dependencies, saved defaults, profile paths,
optional Telegram credential wizard and non-overwriting optional PATH launcher.
senai telegram start: saved project/trust, memory from saved defaults, cron enabled.
senai telegram voice-configure/check/remove: short aliases.
senai cron list: uses saved project; no live worker implicitly started.
senai cron create: interactive name/task/when/repeat/destination + confirmation.
senai memory add TEXT -> explicit append MEMORY.md.
senai user add TEXT -> explicit append USER.md.
senai soul add [TEXT] -> HUMAN command append SOUL.md, never automatic learning.
Keep advanced explicit flags/APIs backward compatible.

## Chronology and interaction
Default timezone from setup, initially Asia/Dhaka. Accept at least today at 10pm,
tomorrow at 1 am, 10 november 2pm, in 2 minutes, and explicit ISO timestamps.
Resolve with injected aware clock and timezone. Confirm full resolved local date/time,
timezone, recurrence and destination before persisting. Never silently choose an
ambiguous date/year/DST fold or schedule a past reminder. Show examples/retry prompts.
CLI interactive creation with no TTY must return actionable error or accept full flags,
never hang. Telegram /cron create asks sequential questions, supports /cancel, timeout,
and per-user drafts; duplicate updates must not create duplicate schedules.
No JSON, scope strings, IDs or ISO timestamps required in the normal flow.
Do not silently create an unsendable local schedule. A saved local task must have a
documented execution/delivery path; coordinator owns final local/account adapter choice.
No live operation or production-state QA during this work.

## Feature boundaries
Cron: parser, CLI wizard, public injectable draft/validation helpers under senai/cron.
Integrations: Telegram conversation state and commands under senai/telegram/integrations;
consume cron helpers only after their contract is agreed/available. Use injected parser
in tests if not yet merged; no copying a second date parser.
Memory: profile shortcut helper under senai/memory; root routing is coordinator-owned.
Skills: preserve unmerged skill work. Review usability/docs only; no skill integration
or new unrelated skills feature is authorized by this UX task.

## Docs and delivery
One README per source module, with Usage and Architecture sections, not separate
duplicated module guides. Coordinator keeps root README, quickstart, manual QA and
cross-module architecture. Historical git records are not onboarding.
Do not delete governance, other workstreams' contracts or active handoff records.
No root doc edits from feature chats. TDD, small commits, full suite and --ready.
No push, rebase/reset, prod bot restart, real scheduler activation or secret disclosure.

Coordinator final composition must pin the configured installation/context at bot startup so changing active defaults in another checkout cannot silently retarget a running bot. Wizard/profile helpers and final account destination selection remain pending feature delivery.

Cron composition is now implemented on main in ad81604: senai/cron_chat.py owns the ephemeral conversation adapter called by TelegramCron.handle; integrations should reuse that path rather than implementing a second /cron wizard. senai/cron_routing.py supplies authorization-backed Destination/store composition. Profile shortcuts remain separate pending work.
