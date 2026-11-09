# Core-feature manual acceptance

For the complete skills workflow, use the [skills demonstration guide](skills-demonstration.md) and [fillable checklist](skills-demo-checklist.csv).

Run from a fresh clone with its own activated venv. Use your own authenticated
Codex account and a dedicated test bot. Keep results as pass/fail/not-run;
a provider error is not a passing test. Live model/speech calls may incur usage.

## 1. Package and offline baseline
Run python -m pip check, senai --help, codex --version and
python scripts/test.py (isolates saved defaults).
Expected: command resolves to this venv, no broken dependencies, tests pass.
Record OS/Python/Codex versions. Do not copy another checkout's .venv or outputs/.

## 2. Coding, editing, stdin and output scope
~~~bash
mkdir -p outputs/acceptance/project-a outputs/acceptance/project-b outputs/acceptance/installation
export SENAI_QA_PROJECT="$PWD/outputs/acceptance/project-a"
senai --project "$SENAI_QA_PROJECT" --skip-git-repo-check "Create hello.py that prints Hello"
python "$SENAI_QA_PROJECT/outputs/hello.py"
senai --project "$SENAI_QA_PROJECT" --skip-git-repo-check "Edit hello.py to print Hello again"
printf '%s
' 'Describe hello.py without edits' | senai --project "$SENAI_QA_PROJECT" --skip-git-repo-check
~~~
Expected: Hello, then Hello again; response matches saved code. Files stay in the
selected outputs/ workspace. Try an explicit -o path outside outputs/: it must fail.

## 3. JSON, native options, sessions and review
~~~bash
senai --project "$SENAI_QA_PROJECT" --skip-git-repo-check --json -o final.txt "Describe hello.py"
senai codex -- --version
senai codex -- exec --help
~~~
Expected: JSON events on stdout, final text file under project outputs/.
Record thread.started's UUID and use --resume UUID on a later request. Verify the
same ID and prior context. Before memory is enabled, --last is also available.
Try senai chat --project PROJECT and exit the native UI normally.
For review, create a separate disposable Git repo with staged/unstaged changes
inside outputs/ and use senai review --project PROJECT --uncommitted.
Optional model/profile/search/image/--skill checks require your own configured
resources; verify outputs instead of treating option acceptance as feature success.

## 4. Cross-project memory and confirmation
~~~bash
export SENAI_INSTALLATION_ROOT="$PWD/outputs/acceptance/installation"
senai --project "$SENAI_QA_PROJECT" --skip-git-repo-check "Remember my preference: Prefers cobalt blue"
senai --project "$PWD/outputs/acceptance/project-b" --skip-git-repo-check "What color do I prefer?"
~~~
Expected: USER.md under the installation root contains the fact; fresh B recalls it.
In an interactive terminal, say "I like concise answers": decline the save prompt,
verify no new fact, repeat, then explicitly accept. Repetition alone must not save.
Resume an earlier memory-enabled UUID after changing a profile: its snapshot stays
frozen. Another installation must not recall this installation's facts.
Automatic SOUL.md learning must fail. Evaluate-events is dry-run only. Milestone
verification uses trusted app code, not user-uploaded JSON/model claims; its behavior
is exercised by the offline event-source tests.

## 5. Telegram onboarding and normal replies
Use the setup guide with a new disposable project/test bot. Skip optional voice
at onboarding and verify normal text still works. Pair using the local code; an
unpaired account must not execute. Send a code request, inspect generated code,
then test /status, /result and /session. Restart gracefully and confirm the exact
native session ID is retained. Do not enable memory midway on an old session
without reading the missing-snapshot limitation. Use one bot instance only.

## 6. Voice, image and credential behavior
Configure voice later with --voice-configure for the exact test project.
Run --voice-check; this is local validation only. Restart gracefully once.
Send /voice Say hello briefly: expect audio only on success. Bare /voice should read
the latest answer. /result should explicitly return text.
Without a usable speech provider, expect text fallback. Use offline tests for forced
network/persistence failures; do not corrupt a real token or production state.
Remove saved voice config, check environment-key precedence and restart behavior.
Request a generated image: verify an actual Telegram photo appears. If the account
cannot generate images, record unavailable; text mentioning a file is not photo acceptance.

## 7. Cron management before live activation
~~~bash
senai cron --project "$SENAI_QA_PROJECT" list
senai cron --project "$SENAI_QA_PROJECT" create --name qa-reminder --prompt "Describe the project" --scope local --at "2035-01-01T09:00:00+06:00"
senai cron --project "$SENAI_QA_PROJECT" dry-run
~~~
Expected: stored schedule, no execution. Inspect show ID; edit using its revision;
repeat a stale edit and expect rejection. Test pause/resume/delete. Calendar and
interval rules are detailed in the cron guide. The sample date is illustrative:
choose a future offset-aware time when you test.

## 8. Scheduled execution and delivery (explicit opt-in)
Read the cron guide first. Account-specific schedules differ from local schedules.
Use only your own test bot/project, authorize the recipient, create a due schedule
in the account store, and explicitly start the documented worker. Stop the ordinary
bot first because they share a lock. Verify one artifact/result, durable runs and
deliveries history, and actual authorized Telegram receipt. Check worker-status.
Ctrl+C and restart: pending delivery must resume without rerunning completed work.
Use offline tests for uncertain execution, process death, partial sends and deadlines;
never blindly reclaim a real uncertain outcome.

No live worker is started by this checklist's management commands.
Live scheduled delivery remains not-run until you deliberately perform this stage.

## Finish
Stop test processes. Save a report under outputs/ containing versions, each test's
result and sanitized errors. Never include credentials. Do not delete native session
or bot state while a service is active. In the current shell, unset
SENAI_INSTALLATION_ROOT after isolated testing unless you intend to keep that root.
