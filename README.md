# Senai — local coding harness

Senai connects a simple CLI and Telegram bot to the installed Codex CLI. It adds
durable jobs, optional voice/photos, human-editable installation memory, and scheduled
tasks with authorized delivery.

**Verified baseline:** WSL2 Ubuntu 22.04, Python 3.10, Codex CLI 0.167.0.
Python >=3.10 is required. The full harness uses POSIX locks/process groups and is
not supported directly on Windows; use WSL. Other platforms remain unverified.
Latest combined offline suite: **474 passing tests** at integration 8fe1098.
Provider access and live behavior must be verified with your account.

## 1. Install once

Prerequisites: Git, Python with venv support, and installed/authenticated Codex CLI.
Install Codex using its [official guide](https://developers.openai.com/codex/cli/).

~~~bash
git clone https://github.com/D0pp1er/Senai-Hermes.git
cd Senai-Hermes
codex login
bash scripts/setup_senai.sh
~~~

The script creates .venv, installs dependencies, checks packaging, then runs setup.
If Ubuntu lacks venv support, it asks before installing OS packages with sudo.
Setup selects one project, installation root and timezone (default Asia/Dhaka),
creates missing profiles, prints their paths and optionally configures Telegram.
Voice setup is optional and can be skipped. Existing profile contents are preserved.
No bot or scheduler starts automatically.

An optional ~/.local/bin/senai launcher avoids venv activation in future terminals.
It never overwrites an existing command. Ensure ~/.local/bin is in PATH.
Otherwise activate once per terminal:

~~~bash
source .venv/bin/activate
~~~

No account, bot, API key, personal path or runtime database is bundled. Repository
read access is required if the repository is private. Dependencies are declared in
pyproject.toml; do not install this checkout with sudo or pip --user.

### Saved defaults

After setup, ordinary commands do not need project/installation/trust flags:

~~~bash
senai "Create hello.py that prints Hello"
senai cron list
senai start
~~~

Non-secret defaults live at ~/.config/senai/defaults.json (or XDG_CONFIG_HOME);
SENAI_CONFIG selects another configuration file. Setup saves canonical project and
installation paths, timezone and the non-Git trust preference. Explicit flags remain
available for advanced overrides. An explicitly different project does not inherit
the saved project's non-Git trust automatically.

## 2. First code request

~~~bash
senai "Create hello.py that prints Hello"
senai "Edit hello.py to print Hello again"
printf '%s
' 'Describe hello.py without editing' | senai -
~~~

Files are relative to the saved project's **outputs/** workspace. Run generated code
from that directory using the appropriate interpreter/compiler. The final model answer
is printed; verify actual files/tests rather than trusting a success assertion.

Advanced examples:

~~~bash
senai --project /absolute/project --skip-git-repo-check "Create hello.py"
senai --json -o response.txt "Describe the workspace"
senai -i /absolute/design.png "Implement this design"
senai --search "Check official documentation for this implementation"
senai --skill INSTALLED_SKILL "Use this workflow"
senai -m MODEL -p PROFILE -c KEY=VALUE "Describe the code"
~~~

Models, search, image tools, skills and profiles depend on your Codex configuration.
Image/schema input paths resolve from the calling directory; response output paths
resolve inside outputs/. --skill selects an installed Codex skill; it does not import,
install or relearn arbitrary skills.

## 3. Human memory, preferences and identity

Setup prints the actual paths. For the chosen installation ROOT:

~~~text
ROOT/outputs/.senai-memory/
  SOUL.md       Human-controlled identity and response style
  USER.md       Confirmed user preferences and personal facts
  MEMORY.md     Explicit memories and verified significant milestones
  memory.db     Advanced detailed facts
  native-snapshots.sqlite3   Frozen native-session context
~~~

Normal human commands use the saved installation automatically:

~~~bash
senai memory add "Completed the first release"
senai memory show
senai memory path
senai user add "Prefers concise answers"
senai user show
senai user path
senai soul add "Answer clearly and explain verification results"
senai soul show
senai soul path
~~~

Omit text after add to get an interactive prompt. Noninteractive missing text returns
an actionable error. Explicit human SOUL edits are allowed; automatic learning cannot
modify SOUL.md. You can also edit the printed files directly alongside Codex.
Append preserves existing text, validates limits and deduplicates notes.

**One installation has one owner.** Its profiles are shared across that installation's
projects and sessions. Fresh sessions load current profiles. Resumed native sessions
reuse frozen snapshots and do not refresh when you edit profiles.

Ordinary personal observations need explicit retention confirmation. Repetition never
confirms them. Interactive CLI may ask a yes/no question after successful execution;
noninteractive observations are not silently saved. Explicit save requests also work:

~~~bash
senai "Remember my preference: Prefers concise replies"
senai "Remember in MEMORY.md: The project codename is Amber Kite"
~~~

Only app-supplied, verified significant milestone checks qualify automatically.
Model output or uploaded JSON cannot declare itself verified. No autonomous milestone
classifier is bundled.

Advanced memory APIs remain available:

~~~bash
python -m senai.memory --installation ROOT add "Detailed fact" --provenance human
senai memory --installation ROOT add "Detailed fact" --provenance human
~~~

Those explicit advanced add/provenance forms write SQLite facts. The simple
senai memory add form appends MEMORY.md. See [learning details](projectprogress/memory-learning.md).

## 4. Telegram

Create your own bot with official Telegram @BotFather. During setup, enter its token
at the hidden local prompt and follow local pairing instructions. Never put a secret
in chat, command arguments, logs or Git.

~~~bash
senai telegram configure
senai telegram start
~~~

Start uses saved project/trust defaults and enables cron. Run only one instance per
bot/project. Stop with Ctrl+C and wait for active work to finish before restarting.

| Telegram input | Behavior |
| --- | --- |
| Plain text or /run REQUEST | Authorized coding request |
| /help | Commands and usage |
| /pair CODE | Pair using locally issued code |
| /status | Private job status |
| /result | Explicitly resend latest completed text |
| /session | Show active shared native session |
| /voice QUESTION | Audio-only success, text fallback |
| /voice | Read latest successful answer; text fallback |
| /cron create | Guided scheduling |
| /cron list | Inspect schedules owned by this chat |
| /cancel | Cancel current draft without deleting existing work |
| /new | Permission-gated fresh shared session with confirmation |

All paired accounts share the same model conversation and project workspace.
Pair only accounts trusted to share context; private delivery is not model isolation.
Authorization is rechecked before execution and delivery. Jobs, text chunks, image
snapshots and voice fallback choices persist for restart/retry.

### Optional voice and photos

~~~bash
senai telegram voice-configure
senai telegram voice-check
senai telegram voice-remove
~~~

Voice configure uses hidden local input and a protected project-scoped file outside
Git. Key precedence: SENAI_TTS_API_KEY, protected saved file, OPENAI_API_KEY.
Native Codex authentication is preserved; the dedicated voice key is excluded from
Codex children. Voice-check validates local configuration only, not API billing/access.
Changes load after an operator-managed graceful restart; no automatic reload is claimed.

Successful /voice sends audio only, without a duplicate text acknowledgement.
Missing/failed audio uses text fallback, and retries retain that choice. /result
still returns text. Speech uses separately billed OpenAI API access; normal text and
photos do not require the voice key. Incoming voice transcription is not implemented.
Image generation requires account/tool support; actual selected PNG/JPEG files can
be attached (up to four, 10 MiB each). A text path is not proof of photo delivery.

### Fresh sessions after profile edits

/new affects everyone sharing the bot and future scheduled tasks. Pairing alone
does not grant this power. The local operator must explicitly grant it on startup:

~~~bash
senai telegram start --new-session-user TELEGRAM_USER_ID
~~~

Repeat the option for multiple operators. /new previews the effect; reply Confirm
or /cancel. Pending/running foreground work and pending/retrying/unknown scheduled
work block the switch. A shared execution gate also protects cron claims.
The old mapping is archived; jobs, pairing, media, native history and old memory
snapshots remain intact. The next request starts a new native UUID and reads updated
profiles. Nothing resets automatically on startup.

An old session created before memory snapshot recording cannot silently adopt current
memory. An authorized /new transition resolves that mismatch. Do not delete databases
or reset a live session manually as a routine workaround.

## 5. Scheduling without JSON or ISO timestamps

### CLI wizard

~~~bash
senai cron create
~~~

It asks, in order:
1. Name — for example Tea break.
2. Task — for example Reply with: Time for tea.
3. First run — for example in 2 minutes, today at 10pm, tomorrow at 1 am,
   or 10 november 2pm.
4. Repeat — once, daily, weekly, or every 2 hours.
5. An authorized destination.
6. A resolved local date/time/timezone preview and explicit yes/no confirmation.

No schedule is written before confirmation. Invalid/past/ambiguous times require
clarification. Noninteractive input requires full advanced flags instead of hanging.
The destination and its account store are selected together. Missing authorization
does not create an unsendable task.

~~~bash
senai cron list
senai cron show SCHEDULE_ID
senai cron pause SCHEDULE_ID
senai cron resume SCHEDULE_ID
senai cron delete SCHEDULE_ID
senai cron runs
senai cron deliveries
~~~

One eligible Telegram account is selected automatically; multiple accounts require
selection. --telegram-account ID selects an account explicitly. --local selects the
advanced local store. Full legacy create --scope forms retain local behavior unless
an account is explicitly selected. Editing requires the last observed revision.

### Telegram wizard

Send /cron create, then answer the same name/task/time/repeat questions.
Review the preview and reply **Confirm**, or /cancel. Drafts are private per chat,
expire after ten minutes, and persist across restart while valid. Duplicate updates
do not create another schedule. /status still works during a draft. An uncertain
creation receipt requires review instead of automatic repetition.

### Execution and delivery

Saving/listing a schedule does not start a worker. For the persistent main service, run senai start. It uses the existing Telegram service, enables cron, and gives due cron work priority over ordinary requests. Telegram must already be configured.

An alternative standalone foreground supervisor is available:

~~~bash
senai cron worker --project PROJECT --telegram-account BOT_ID
senai cron worker-status --project PROJECT --telegram-account BOT_ID
~~~

Stop the ordinary bot first: they share a singleton lock and native session.
Standalone worker does not poll incoming Telegram messages. It executes one task
at a time and drains delivery independently. --execution-timeout defaults to
300 seconds (max 3600); --once does one claim plus currently due delivery.
Ctrl+C/SIGTERM stops new claims and waits for bounded active work. Results/outbox
survive restart without rerunning completed Codex work.

Deadlines mark unknown and pause the schedule. In-flight/uncertain work is not
automatically reclaimed. RetryDelivery requires transport-confirmed rejection
before any accepted chunk; ambiguous/partial sends remain unknown.
External execution/delivery is not guaranteed exactly once. Review effects before
manual recovery. Pausing/deleting future work does not retract pending results.
Scheduled delivery is currently text, not voice/photos.

Detailed calendar/DST/retry/recovery rules: [cron guide](projectprogress/cron.md).

## 6. Native interactive modes

~~~bash
senai chat
senai review --uncommitted
senai review --base main
senai codex -- --version
senai codex -- exec --help
~~~

These delegate to installed Codex. Native interactive/review/passthrough does not
inject Senai semantic memory. Review is Git-repository scoped and may include a
parent repository. Workspace expansion/relocation flags are rejected.
Memory-enabled ordinary requests require exact --resume UUID; --last/--ephemeral
are not supported in that mode. outputs/ is a policy, not a separate filesystem jail.

## 7. CLI/API smoke-test guide

Senai is a CLI/Python harness, not an HTTP API server. There are no REST endpoints.

Run from the installed checkout with its venv active:
~~~bash
senai --help
senai telegram --help
senai memory path
senai user path
senai soul path
senai user add "My favorite color is cobalt blue"
senai "What is my favorite color?"
senai cron list
python -m pip check
python -m unittest discover -s tests -v
~~~

Expected: paths point to the saved installation; a fresh coding session recalls
cobalt blue; cron list starts no execution; dependencies and offline tests pass.
For full acceptance follow [manual tests](docs/manual-testing.md), using your own
disposable project/test bot. Live model/speech/provider calls may incur usage.

Telegram checks:
- Plain request returns a response; /session remains stable across normal restarts.
- /voice Say hello briefly yields audio only on success; /result returns text.
- /cron create -> in 2 minutes -> Confirm produces durable history and authorized delivery.
- Edit USER.md, perform an authorized /new -> Confirm, then ask a fresh request:
  edited facts appear, and earlier history is retained.
- Test cancellation, revoked users and uncertain failures with offline fixtures rather
  than damaging production state.

### Python extension boundaries

| API | Contract |
| --- | --- |
| senai.memory.profile_main(kind, argv, installation=..., stdin=..., stdout=..., stderr=...) | Human memory/user/soul add/show/path/setup |
| senai.memory.setup_profiles(root) | Initialize missing profiles; preserve existing contents; return exact paths |
| InstallationRuntime(root).execute(request, workspace, executor=...) | Saved frozen native context and successful-outcome learning |
| OutcomeLearning(memory, confirm=..., checks=...) | Explicit personal confirmation / trusted milestone checks |
| parse_when(text, now=..., timezone=...) | Aware future time or clarification |
| build_draft / preview_draft / commit_draft | Shared pure preview and explicit confirmed schedule commit |
| Worker(store, executor).tick() | Claim and persist one due outcome |
| DeliveryWorker(store, send).tick() | Independent authorized delivery; unknown outcomes fenced |
| ConversationRouter / SessionGate | Durable chat drafts, explicit /new policy, serialized execution boundary |

Use trusted app evidence/authorization when implementing callbacks. A JSON object
claiming verified=true or an arbitrary destination does not grant permission.

## 8. Architecture

~~~text
CLI / Telegram input
        |
saved defaults + authorization + validated workspace
        |
        +--> Human profile commands --> atomic profile writes (SOUL human-only)
        |
        +--> Ordinary request --> frozen installation snapshot
        |                          |
        |                    Codex CLI / exact native UUID
        |                          |
        |                    durable response + outcome learning
        |
        +--> Guided schedule --> shared parser/draft --> explicit confirmation
                                   |
                               cron store/claim
                                   |
                         SAME authorized Codex runner
                                   |
                         durable result + delivery outbox
                                   |
                      independent authorized message delivery
~~~

Main modules:

| Module | Responsibility |
| --- | --- |
| cli.py, defaults.py, onboarding.py | Command routing, saved configuration, initial setup |
| workspace.py, prompts.py, codex.py, native.py | Output scope and native execution |
| memory/ and memory_runtime.py | Profiles, facts, snapshots and confirmed learning |
| telegram/ | Pairing, jobs, media/voice, durable conversation state and session history |
| cron/ | Time rules, drafts, durable schedules/runs/outbox and worker primitives |
| telegram_composition.py | Shared parser bridge, operator permissions, execution and claim gate |
| cron_runtime.py, cron_routing.py, cron_supervisor.py | Authorized routing, matching stores and supervised execution |

Project artifacts/jobs/media/cron live under PROJECT/outputs/. Profiles/snapshots use
the explicitly selected installation's outputs/.senai-memory/. Credential files
remain outside Git under local configuration storage. Startup pins project,
installation and timezone; changing another checkout's defaults cannot silently
retarget those running executors. Foreground and cron runners share one gate;
cron claims also take that gate so /new cannot race a new execution claim.

Module guides:
- [Memory usage and architecture](senai/memory/README.md)
- [Telegram usage and architecture](senai/telegram/README.md)
- [Cron usage and architecture](senai/cron/README.md)

## 9. Delivery status and limitations

Integrated profiles and guarded Telegram composition: 8fe1098.
Memory feature through 94cb6f4; integrations feature through 2e09f9a.
Both feature readiness checks passed; independent feature suites passed 393 and
418 tests; combined suite passed 474 tests. These are offline checks using
disposable state and provider fixtures. They do not prove live account availability.
No production restart, schedule activation, push or deployment was performed for
this integration.

Known limits: full native Windows support, Discord, incoming voice transcription,
automatic snapshot refresh, autonomous milestone classification, arbitrary skill
import/relearning, scheduled media and OS-service autostart are not shipped on main.
Old-session memory needs a deliberate fresh transition. Voice reload requires an
operator-managed restart. Unknown external outcomes require review.

To update: stop active work, check git status, use git pull --ff-only, then reinstall
inside the checkout's venv. Do not rebase reviewed main history or force-push to hide
conflicts. Contributor history/contracts live under projectprogress/ and are not
required for ordinary onboarding.

## Main service: cron-first execution

~~~bash
senai start
~~~

This is an alias for the existing configured Telegram/cron service, not a second
daemon. It stays in the foreground until Ctrl+C or a fatal service error.
The main thread handles polling and delivery; one execution worker checks due cron
work first and runs ordinary requests when none is due. Native calls still share the
existing execution/session gate. Delivery stays responsive while execution is busy.

A running task is not preempted. A continuous cron backlog can delay ordinary
requests. Existing deadlines, unknown-outcome recovery, singleton locking and
graceful shutdown remain unchanged. Stop with Ctrl+C and wait for active bounded
work. Nothing installs boot autostart, starts a second poller, or activates a service
merely from installation. The separate cron worker command remains an alternative,
not something to run alongside this service for the same bot/project.
