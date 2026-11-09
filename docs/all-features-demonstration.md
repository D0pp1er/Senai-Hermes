# All-feature manual QA and viewer demonstration

Use this guide for the complete Senai harness. Record results in the
[all-feature CSV](all-features-checklist.csv). Detailed skill procedures remain in
[skills demonstrations](skills-demonstration.md); their 48 cases are included in the
combined CSV. This is a manual acceptance plan, not a claim that these steps passed.

## Presenter route and evidence

For a 20–30 minute presentation: setup/defaults -> create/edit/run code -> profile
paths and recall -> Telegram text/session -> optional photo/voice -> guided reminder
and actual delivery -> skill import/use/export -> histories and limitations.
Prepare slow live steps beforehand and show their original reports. Complete acceptance
takes longer. Record Pass, Fail or Not run, actual command, commit, evidence path and
limitations. Counts such as 272 or 622 describe historical automated suites, not features.

| Classification | Evidence needed |
| --- | --- |
| Offline/manual | Actual command output, configuration and files |
| Offline regression | Passing fixture contracts, actual count and commit |
| Live Codex | Real account execution and independently checked artifacts |
| Live Telegram/speech | Actual authorized receipt and playable audio/photo |
| Obsidian UI | Actual app viewing, separate from exported files |

## 1. Isolated installation and onboarding (I01–I07)

Use WSL Ubuntu, Python >=3.10, installed/authenticated Codex CLI and a fresh clone.
Use a dedicated test bot and state. Open a new WSL terminal:

~~~bash
git clone https://github.com/D0pp1er/Senai-Hermes.git
cd Senai-Hermes
export QA="$PWD/outputs/manual-qa-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$QA/project-a" "$QA/project-b" "$QA/installation"
export SENAI_CONFIG="$QA/defaults.json"
unset SENAI_INSTALLATION_ROOT
printf 'Project: %s\nInstallation: %s\n' "$QA/project-a" "$QA/installation"
codex login
bash scripts/setup_senai.sh
source .venv/bin/activate
senai setup --root "$QA/installation"
~~~

The install script runs initial setup with the clone as installation root. At its
project prompt paste the printed absolute project-a path, choose timezone, decline
Telegram for now and decline the optional global launcher. The final setup command
selects the isolated installation root; again choose project-a/timezone/no Telegram.
Shell variables are not expanded in interactive answers: paste expanded paths.

~~~bash
python -c 'import senai,sys; print(sys.executable); print(senai.__file__)'
python --version
codex --version
python -m pip check
senai --help
git rev-parse HEAD
~~~

Expected: this clone's venv/package; dependencies pass; printed profile paths; no
service starts. Saved non-secret defaults use SENAI_CONFIG. Repeat setup after adding
a profile note: contents must survive. Keep QA/SENAI_CONFIG in every test terminal.
Do not copy a venv from another checkout. The optional launcher can be checked separately:
it must preserve any existing launcher. Network/install errors are blockers, not passes.

## 2. Coding, stdin, workspace and options (C01–C10)

~~~bash
senai "Create hello.py that prints Hello"
python "$QA/project-a/outputs/hello.py"
senai "Edit hello.py to print Hello again"
python "$QA/project-a/outputs/hello.py"
printf '%s\n' 'Describe hello.py without editing it' | senai -
senai --json -o final.txt "Describe hello.py without editing it" > "$QA/events.jsonl"
cat "$QA/project-a/outputs/final.txt"
~~~

Expected: Hello then Hello again; accurate description; JSON events and final answer.
Generated files/final output resolve under selected outputs/. Inspect actual files.
Negative checks:

~~~bash
senai -o /tmp/senai-outside.txt "Say hello"
senai ""
~~~

Expected: actionable nonzero errors before model execution. outputs/ is a policy,
not a separate filesystem jail. Do not damage outside files to demonstrate that limit.

Optional account-dependent templates (replace placeholders):

~~~text
senai -m YOUR_MODEL -p YOUR_PROFILE -c KEY=VALUE "Describe hello.py"
senai --search "Check official documentation for this code"
senai -i /absolute/test-image.png "Describe this design"
senai --skill YOUR_INSTALLED_NATIVE_SKILL "Use this workflow"
~~~

Use actually supported configuration/files and verify behavior. Native --skill is
separate from imported registry skills. Option acceptance alone is not feature success.

## 3. Sessions and native modes (N01–N06)

Find thread.started in events.jsonl and copy its native UUID:

~~~text
senai --resume ACTUAL_UUID "What did hello.py print after the edit?"
senai chat
senai codex -- --version
senai codex -- exec --help
~~~

Expected: exact resumed UUID/prior context; native UI exits normally; installed help.
Native chat/review/passthrough do not inject Senai semantic memory. Memory-enabled
ordinary requests require explicit --resume UUID; --last/--ephemeral are unsupported.

For native review create a disposable Git fixture:

~~~bash
mkdir -p "$QA/review-project"
git -C "$QA/review-project" init
printf 'print("review fixture")\n' > "$QA/review-project/example.py"
git -C "$QA/review-project" add example.py
senai review --project "$QA/review-project" --uncommitted
~~~

Assess actual review relevance. Review is Git scoped and may include parent repositories.
Workspace expansion/relocation flags are rejected; exercise combinations offline.

## 4. Memory, user and soul profiles (M01–M12)

~~~bash
senai memory path
senai user path
senai soul path
senai memory add "The QA project codename is Amber Kite"
senai user add "My favorite color is cobalt blue"
senai soul add "Answer clearly and explain verification"
senai memory show
senai user show
senai soul show
senai user add "My favorite color is cobalt blue"
senai "What is my favorite color and the QA project codename?"
~~~

Expected: profiles under QA/installation/outputs/.senai-memory/, existing text preserved,
no duplicate note, fresh request recalls both facts. Test senai memory add without text
in a terminal: it prompts. Non-TTY missing text must fail without waiting. SOUL writes
here are human-authorized; automatic learning cannot edit SOUL.

Same installation, different project:

~~~bash
senai --project "$QA/project-b" --skip-git-repo-check "What is my favorite color and QA codename?"
~~~

Expected: same installation facts available. A separate empty installation must not
contain them. Create one and test a fresh request:

~~~bash
python - <<'PY'
import os
from pathlib import Path
from senai.memory import setup_profiles
root = Path(os.environ['QA']) / 'other-installation'
root.mkdir(exist_ok=True)
print(setup_profiles(root))
PY
senai --installation "$QA/other-installation" "Do you know my favorite color? Do not guess."
~~~

Inspect its profiles/context too: a coincidental model guess does not establish a leak.
Frozen snapshot test: retain the original memory-enabled UUID. Add a new user note,
then compare that exact resumed UUID with a fresh session. Old snapshots stay unchanged;
fresh sessions load current profiles. Do not put the new value in the test question.
Use snapshot records/offline tests as stronger evidence than model inference alone.

Confirmation test: in an interactive successful request say I like concise answers.
Decline retention, inspect USER.md; repeat and decline again. Repetition must not save.
Repeat and explicitly confirm; inspect the file. Explicit Remember my preference
requests authorize retention. Only trusted app-verified significant milestones qualify
automatically. Uploaded JSON/model claims cannot declare themselves verified. Use
learning/event-source fixtures for automatic milestones and the human-only SOUL gate.

## 5. Telegram onboarding, pairing, jobs and sessions (T01–T10)

Create your own disposable bot with @BotFather. Configure locally:

~~~bash
senai telegram configure
senai telegram --check
senai telegram start
~~~

Enter secrets only at hidden local prompts; skip voice initially. Follow local pairing
instructions. Keep only one poller per bot/project. A second test terminal must use the
same QA/SENAI_CONFIG. Configuration check alone does not prove execution/delivery.

Send in the paired private chat:

~~~text
/help
/status
Create telegram-hello.py that prints Telegram works
/result
/session
~~~

Expected: real generated file executes; response, private status, text replay and native
UUID available. Ask a follow-up about that file. An unpaired test account must not
execute. All paired accounts share model context/workspace; private delivery does not
isolate model memory. Pair another account only if trusted to share that context.

Record /session, Ctrl+C and wait for shutdown, restart same command. Exact UUID, jobs
and pairing must persist. Request a long benign response to inspect chunk completeness.
Use offline fixtures for forced transport failures, durable retries and singleton races.

## 6. Optional voice and photos (V01–V07)

Before voice setup, /voice Say hello briefly should fall back to text. Stop the test bot:

~~~bash
senai telegram voice-configure
senai telegram voice-check
senai telegram start
~~~

Use your own speech key at the hidden prompt. Native Codex login is not speech API
access; speech has separate provider access/billing. Voice-check validates local settings,
not credits. Skipping voice is valid and does not disable text/photo capability.

In Telegram:

~~~text
/voice Say hello briefly
/voice
/result
~~~

Expected: playable audio only on successful voice requests, without duplicate text;
/result explicitly returns text. Missing/failed audio falls back to text. Retry choice
persistence needs offline fault tests. Incoming voice transcription is not implemented.
Request a simple generated image using available tools: an actual photo must appear/open,
not just a filename. Up to four eligible PNG/JPEG images, 10 MiB each. Record account/tool
unavailability as Not run, not successful photo delivery.

Optional disposable removal test: stop, run senai telegram voice-remove, voice-check,
then restart. Environment keys can still take precedence; removal affects only saved
voice credentials. Do not show keys in logs/CSV. Keys stay outside Git/outputs. Verify
native authentication preservation using fixtures rather than exposing its files.

## 7. Fresh Telegram sessions and updated profiles (T11–T14)

Restart your test bot with the actual numeric operator ID when ready:

~~~text
senai telegram start --new-session-user YOUR_TELEGRAM_USER_ID
~~~

Without this permission, a paired account's /new must refuse. With it, /new -> /cancel
retains UUID. Add a profile note, then /new -> Confirm while idle; next normal request
creates a different UUID and loads the new profile. Old jobs/history/pairing/media remain.
The switch affects everyone and future scheduled work. Pending/running/unknown work
blocks it; use offline fixtures for races. Old sessions without snapshots need an explicit
fresh transition, never database deletion. Restart alone must not reset the session.

## 8. Guided cron creation and management (R01–R12)

Configure/pair the test bot first, then stop its process for management-only checks.

~~~bash
senai cron create
~~~

Answer name QA reminder; task Reply with: Scheduled test worked; first run tomorrow
at 1 am; repeat once; select the authorized test chat; confirm yes. Prompts may phrase
labels differently. Check exact local date/time/timezone, destination and lateness/retry
policy. No raw JSON or timestamp is needed. Missing authorization must fail clearly.

Repeat and /cancel or answer no: nothing saved. Try invalid/past/ambiguous times: examples
and clarification required. Supported future inputs include in 2 minutes, today at 10pm,
tomorrow at 1 am, 10 november 2027 2pm. Choose future dates relative to testing day;
yearless past dates never silently roll forward. Repeats: once/daily/weekly/every 2 hours.

Copy actual IDs/revisions into these templates:

~~~text
senai cron list
senai cron show SCHEDULE_ID
senai cron pause SCHEDULE_ID
senai cron resume SCHEDULE_ID
senai cron edit SCHEDULE_ID --expected-revision CURRENT_REVISION --prompt "Reply with: Updated scheduled test"
senai cron runs
senai cron deliveries
senai cron delete SCHEDULE_ID
~~~

Read revision from show. Reusing a stale revision must reject, preserving newer data.
Pause/delete change future eligibility, not already pending delivery. CLI and bot must
use the same account store. Multiple accounts need selection; --telegram-account ID is
available. For a management-only local fixture:

~~~bash
senai cron --local create --name local-preview --prompt "Describe the workspace" --scope local --when "in 2 hours"
senai cron --local list
senai cron --local dry-run
~~~

Local stores do not supply an automatic execution/delivery adapter. Calendar/DST,
skip/coalesce, retries, overlap and atomic claim edge cases belong in offline tests.

## 9. Telegram cron wizard (R13–R17)

Start only the test bot. /cron create asks name -> task -> time -> repeat -> preview ->
Confirm. Choose a future one-shot initially. Destination is that authorized private chat.
Compare /cron list with CLI list. During a draft /status remains a command; /cancel saves
nothing. Invalid answers retry the same field. Drafts are per chat, expire after ten
minutes and valid drafts survive restart. Use natural expiry or offline fake-clock tests.
Duplicate updates/uncertain creation receipts require fixture tests. Do not resend Confirm
blindly after a crash; inspect list/history first.

## 10. Actual scheduled execution/delivery (R18–R24)

This stage explicitly activates only your disposable schedule. Stop standalone workers:

~~~bash
senai start
~~~

This uses the configured Telegram service with cron enabled; due cron work has priority.
In that chat create a one-shot for in 2 minutes with task Create scheduled-proof.txt
containing Scheduled test worked, then reply Scheduled test worked. Confirm the preview.
Optionally pause a second disposable schedule before due and verify it never executes.

~~~bash
cat "$QA/project-a/outputs/scheduled-proof.txt"
senai cron runs
senai cron deliveries
~~~

Expected: actual artifact, one completed durable run, persisted result/outbox and actual
authorized text receipt. Record IDs/timestamp. Listing or fake executor output is not
live acceptance. Alternate supervisor, with bot stopped and actual account ID:

~~~text
senai cron worker --telegram-account BOT_ACCOUNT_ID
senai cron worker-status --telegram-account BOT_ACCOUNT_ID
~~~

Standalone worker does not poll messages and shares bot lock/session. Never run both
for one bot/project. Ctrl+C/SIGTERM stops new claims and waits for bounded active work;
delivery drains independently. Stop/restart idle: completed work must not rerun.
Use offline integration fixtures for pending-delivery restart, process death, deadlines,
partially accepted sends, revocation and unknown work. Only transport-confirmed rejection
can safely retry; uncertain effects need review. No exactly-once guarantee. Scheduled
delivery is text only. See [cron recovery](../projectprogress/cron.md).

## 11. Skills and Obsidian (S01–S48)

Follow [the detailed skills guide](skills-demonstration.md) in its own disposable shell
and registry. All its rows are included in the combined CSV. It covers:

- Local/workflow import, cancel, list/show/use, origins and persistence.
- Native versus registry skills, per-request overrides and multiple selections.
- Exact-digest outcomes; unchecked success prose stays unverified.
- Pinned public imports, integrity checks and rejection behavior.
- Author -> stage -> independent checks -> accept -> held-out reuse.
- Evidence-guided revisions -> validation -> activation -> rollback.
- Synthetic lifecycle demo versus optional actual-model correction demo.
- Obsidian path prompt/display, explicit refresh, note protection and Windows viewing.
- Telegram/cron inheritance and session/project compatibility.

Authoring run reports remain separate from normal requests. No automatic activation,
weight training, Telegram skill-management UI or Obsidian watcher is implemented.

## 12. Architecture, regression and evidence (A01–A06)

~~~text
CLI / Telegram -> defaults + authorization + outputs workspace
 -> frozen installation memory + selected skill context
 -> existing Codex CLI / native session
 -> persisted response + checked/confirmed learning
 -> authorized text / photo / optional voice delivery

cron wizard -> confirmation -> durable schedule/claim
 -> same authorized executor -> durable result/outbox
 -> independent authorized delivery
~~~

Profiles/snapshots are installation-wide. Registry/jobs/media/cron are project scoped;
credentials stay outside Git. /new shares an execution gate with cron. Startup context
is pinned: changing defaults cannot silently retarget running executors. Native modes
are separate from ordinary memory/skill-context injection. Senai offers CLI/Python APIs,
not HTTP endpoints. See [README architecture/API](../README.md).

Run isolated regression and retain real status:

~~~bash
set -o pipefail
python scripts/test.py 2>&1 | tee "$QA/offline-tests.log"
~~~

Record count/commit; historical 622 is not a claim about an unrun checkout. Fixtures
exercise transport ambiguity, gate races, migrations, snapshots and safe learning.
They do not establish live provider permissions or universal model reliability.

Stop your test processes; inspect/delete/pause only your own test schedules. Do not
remove state while workers run. Retain sanitized CSV and artifacts under QA, excluding
secrets/personal transcripts. Exit the test shell to restore its environment.
