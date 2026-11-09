# Historical record — superseded user guide

# Telegram: automated setup and one persistent shared conversation

The Telegram adapter is operator-independent: no personal Telegram ID or project
path is hardcoded. Any private account can pair using a code obtained locally.
As requested, **all paired accounts share one Codex session and output workspace**.
They can therefore access earlier conversation context; pair only accounts that
should share that context. Private /status and /result replies remain scoped to
the requesting chat, but the model conversation itself is shared.

The original bot was user-verified live. This new pairing/setup/session revision
has 126 passing automated tests plus a live Codex session-continuity check; its
full Telegram onboarding still needs your manual acceptance.

## 1. One-command setup

Create a bot with official @BotFather using /newbot if you do not already have one.
Stop an already running copy of the bot with Ctrl+C and let active work finish.
From the senai repository checkout:

```bash
bash scripts/setup_telegram.sh --project /path/to/project --skip-git-repo-check
```

Replace /path/to/project with the directory you want controlled. Omit
--skip-git-repo-check when normal Codex Git checks are appropriate. The script uses
the installed Python package; install senai first if the module is unavailable.
It can run for any WSL user and project, without editing the script.

The script automatically:

1. Prompts for the bot token with hidden input; Enter reuses a saved/exported token.
2. Validates the bot identity and checks for a conflicting webhook.
3. Prints a private `/pair CODE` message, valid for ten minutes and one use.
4. Waits for you to send that exact message to your bot in a private Telegram chat.
5. Records the paired user automatically; no numeric ID lookup or export is needed.
6. Saves the token atomically in a private mode-600 env file outside the project.
7. Starts the bot, using the validated token and selected project/options.

The pending-message backlog is drained before the pairing code is shown, so a
quickly sent valid pairing message is not skipped. If an expired code is submitted,
a fresh code is printed. An existing webhook is never deleted automatically.

Equivalent Python command:

```bash
senai telegram --configure --start --project /path/to/project --skip-git-repo-check
```

To configure only, omit --start. No code request runs during the pairing wizard.
The token is never printed or passed as a command-line argument. Do not paste it
into chat, a model prompt, or Git.

## 2. Restart without repeating manual setup

```bash
senai telegram --project /path/to/project --skip-git-repo-check
```

Configuration is discovered from:

```text
${XDG_CONFIG_HOME:-~/.config}/senai/telegram/<project-path-hash>.env
```

The wizard prints the exact path. The hash identifies the resolved project path,
so continue using the same --project value. The file contains only the bot token;
paired accounts and session mapping live in the project's state database.

Explicit configuration remains supported:

```bash
senai telegram --env-file /private/path/telegram.env --project /path/to/project
```

The env file accepts TELEGRAM_BOT_TOKEN and optional legacy
TELEGRAM_ALLOWED_USER_IDS assignments. Exported values override file values on
ordinary launches. If you change bots/tokens, remove stale exported values first.
The configure-and-start path uses the token just validated by the wizard.

Credential files created by the wizard must remain outside the controlled project.
Symlinked credential files are refused. Credential variables are removed from the
senai/Codex child environment. No credential file is created in Git by setup.

## 3. Pair another Telegram account

While the service runs, open another local WSL terminal:

```bash
senai telegram --project /path/to/project --pair-code
```

Give the printed `/pair CODE` to the intended account privately. That account
sends it to the bot in a private chat. It is then authorized without changing
source or typing its numeric ID into configuration.

Codes are random, single-use, expire after ten minutes, and are stored only as
hashes. Issuing a new code invalidates the previous unused code. Startup also
prints a local code for convenient additional pairing. Already paired users do
not need to pair again after reconnecting or restarting the bot.

Revoke access locally:

```bash
senai telegram --project /path/to/project --revoke-user NUMERIC_USER_ID
```

Explicit revocation overrides even an old environment allowlist. New/queued
execution and pending replies are blocked for that user. An already executing
request is not cancelled; this adapter still has no /cancel command.

## 4. Use the shared conversation

| Telegram message | Result |
| --- | --- |
| `/start` or `/help` | Usage and commands. |
| Plain text request | Execute the next turn in the shared conversation. |
| `/run your request` | Execute a turn explicitly. |
| `/session` | Show the saved shared Codex ID, or that the first request will create it. |
| `/status` | Your latest three job states. |
| `/result` | Resend your latest completed result without re-executing it. |
| `/pair CODE` | Authorize a private account with a locally issued code. |

Example continuity check:

```text
Remember this conversation marker: TELEGRAM_MEMORY_731. Reply stored.
What exact marker did I give you earlier?
```

The second message must recall TELEGRAM_MEMORY_731 without the marker being
included in that message. Restart the bot and repeat the second question; /session
must show the same ID. Another paired account uses that same shared conversation.

The first post-upgrade request creates the shared session. Later turns resume
its exact verified native thread ID using --resume; --last is never used. A failed
resume preserves the mapping and reports failure rather than silently creating a
new one-off conversation. Earlier independent v1 sessions are not merged together.

Requests remain serialized through one worker (four pending/running jobs by default).
Local files also persist, so later turns can edit earlier generated code. Replies
are plain text and split safely for long Unicode responses. Large replies are
truncated at 60,000 characters with a reference to complete local output.

## 5. Execution options and files

```bash
senai telegram --project /path/to/project --skip-git-repo-check --search
senai telegram --project /path/to/project --model YOUR_MODEL --profile YOUR_PROFILE --skill YOUR_INSTALLED_SKILL
```

--skill is repeatable. --max-pending controls queue capacity; --poll-timeout
controls long polling. Models, profiles, skills, and tools still need native setup.
Remote text is a literal request, never a shell command or arbitrary CLI flags.

The worker uses normal workspace-write execution with --ask-for-approval never.
Protected operations fail rather than waiting for a terminal approval. No approval
or sandbox bypass is enabled automatically. Native configuration/tools still apply;
this wrapper is not an independent filesystem jail.

```text
<project>/outputs/                         generated files
  .senai-telegram/<bot-id>/
    bot.lock
    state.sqlite3                         jobs, paired users, code hashes, shared session ID
    jobs/<request-id>/stdout.txt           native JSONL events
    jobs/<request-id>/stderr.txt           diagnostics
    jobs/<request-id>/response.txt         final response
```

The native Codex transcript remains in its normal Codex state location. The local
DB also retains Telegram requests/results and a session_id on each new job.
Do not publish bot state or tokens. Stop the old bot before switching code versions;
already running Python processes do not reload this change automatically.

## 6. Reliability and limits

- Duplicate updates do not re-execute work; failed sends retry saved result delivery.
- A reply part may be duplicated if Telegram accepted it immediately before a crash.
- Accepted queued jobs persist; previously running jobs are marked interrupted and
  are not automatically repeated. A new session ID found in an interrupted job's
  event log is recovered before interrupted-job handling.
- Explicit revocation is checked again before queued execution and result delivery.
- New messages sent while the bot is offline are skipped at startup. This does not
  erase the stored conversation, paired users, queued work, or completed results.
- Ctrl+C stops polling and waits for active work to finish. Pending work/results remain saved.
- No remote cancellation, voice/photos, attachments, file downloads, or service autostart.
- The PC, WSL process, and outbound internet must remain available. No public port,
  tunnel, or desktop Remote connection is required.

## 7. Verify

```bash
python3 -m unittest discover -s tests -v
bash scripts/setup_telegram.sh --help
senai telegram --help
```

Current evidence: 126 tests; real Codex remembered a marker after runner/store
restart and a simulated second Telegram user, with the same saved ID. New wizard
and pairing tests use fake APIs/private temporary files, not your live token.
See [manualqa.md](../tests/manualqa.md), QA-20, for new live acceptance steps.
Official protocol sources: https://core.telegram.org/bots/api and
https://learn.chatgpt.com/docs/non-interactive-mode
