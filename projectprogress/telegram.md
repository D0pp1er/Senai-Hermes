# Control senai from Telegram

Status: implemented and verified offline; the user confirmed live Telegram operation on 2026-11-08. New installations still require a bot token and numeric user ID. No credentials are
included in this repository.

The selected setup runs independent one-off Codex requests against
`/home/rk/SentiensHermes`. Generated code goes into that project's outputs/.

## 1. Create your bot

In Telegram, open the official **@BotFather**, send `/newbot`, and follow its
name/username prompts. Keep the issued bot token private. Do not paste it into
this chat, a prompt, a screenshot, or Git.

Official Bot API reference: https://core.telegram.org/bots/api

## 2. Configure the token in WSL

Open your Ubuntu terminal:

```bash
cd /home/rk/SentiensHermes/senai
export PATH="$HOME/.local/bin:$PATH"
git branch --show-current
senai telegram --help
```

Expected branch: feature/telegram-bot. Existing editable installs pick up this
code automatically. If the senai command is absent, use the installation section
in [features.md](features.md).

Run this command, paste the token into its hidden prompt, and press Enter:

```bash
read -r -s -p "Telegram bot token (hidden): " TELEGRAM_BOT_TOKEN
printf '\n'
export TELEGRAM_BOT_TOKEN
```

Check credentials without polling or executing a request:

```bash
senai telegram --check
```

Expected: the bot username and confirmation that no webhook is active. A bot
already using a webhook needs a separate/dedicated bot or explicit removal of
its existing webhook. senai never silently deletes a webhook.

## 3. Discover your numeric Telegram user ID

In the same terminal:

```bash
senai telegram --setup
```

The terminal shows an exact random `senai-setup-...` phrase and your bot's username.
Open that bot's private chat in Telegram and send the phrase exactly. The terminal
then prints `TELEGRAM_ALLOWED_USER_IDS=<your number>` and exits.

Setup only reads the matching private message. It does not run code or send a reply.
Set the printed ID locally, replacing the placeholder:

```bash
export TELEGRAM_ALLOWED_USER_IDS=YOUR_NUMERIC_USER_ID
```

Use the numeric user ID, not a username or the bot's own ID. The allowlist is
mandatory. Multiple explicitly authorized users may be comma-separated; they
share the same configured project and execution queue.

## 4. Start the bot

Keep this terminal running:

```bash
senai telegram --project /home/rk/SentiensHermes --skip-git-repo-check
```

Wait for `Senai Telegram is ready as @...` before sending work. Messages sent
before startup are intentionally skipped; they will not unexpectedly execute
later. Then send `/start` in the bot's private Telegram chat.

The PC and WSL bot process must remain awake and online. This uses outbound HTTPS
long polling; no public server, inbound port, tunnel, or desktop Remote setup is needed.
The bot uses your existing Codex CLI login. It does not need a separate model API key.

## 5. Send requests and inspect status

| Telegram message | Result |
| --- | --- |
| `/start` or `/help` | Show bot usage. |
| `Create telegram_hello.py that prints Telegram is working` | Queue an independent senai request. |
| `/run Edit telegram_hello.py to print Hello again` | Queue a request explicitly. |
| `/status` | Show your three most recent requests and their states. |
| `/result` | Resend your latest completed result; does not execute it again. |

Accepted work receives a request ID. One worker executes requests sequentially,
while polling remains responsive to /status. Up to four queued/running jobs are
accepted by default; extra requests receive a busy response and are not saved as jobs.

Only configured users in private chats are authorized. Groups, other users, bot
accounts, edited updates, and non-text messages do not execute code. Telegram
message text is always a literal request, never a shell command or native CLI
option list. Unknown slash commands display help instead of executing.

Generated files stay in `/home/rk/SentiensHermes/outputs/`. For example:

```bash
python3 /home/rk/SentiensHermes/outputs/telegram_hello.py
```

Final success/failure replies return to the requesting private chat. Long results
are split into plain-text messages without breaking Unicode. Replies longer than
60,000 characters are truncated; complete stdout/stderr remain in local job logs.
Local file links in a reply are not downloadable files on your phone.

## 6. Configure the bot's execution defaults

These are local startup options, not commands that strangers can send remotely:

```bash
senai telegram --project /home/rk/SentiensHermes --skip-git-repo-check --search
senai telegram --project /home/rk/SentiensHermes --skip-git-repo-check --model YOUR_MODEL --profile YOUR_PROFILE --skill YOUR_INSTALLED_SKILL
```

- --model / --profile select existing Codex settings.
- --search enables native live search for requests.
- --skill can be repeated for installed workflows.
- --max-pending sets total running/queued capacity (1-100, default 4).
- --poll-timeout sets long-poll duration (1-30 seconds, default 10).

Use available models/profiles/skills. The bot does not install tools or skills.
Each request starts a fresh conversation; generated files persist in the shared
workspace, so later requests can still edit earlier files.

Remote jobs use the normal workspace-write flow with `--ask-for-approval never`:
action requests requiring additional interactive permission fail rather than
waiting for a terminal approval. No sandbox/approval bypass is enabled by the adapter.
This is not a separate security jail for arbitrary Codex tools/configuration.

## 7. Optional persistent local configuration

For later sessions, you may create a private env file outside the project and
outside the Codex output workspace, for example `~/.config/senai/telegram.env`:

```text
TELEGRAM_BOT_TOKEN=YOUR_PRIVATE_BOT_TOKEN
TELEGRAM_ALLOWED_USER_IDS=YOUR_NUMERIC_USER_ID
```

Protect it with mode 600 and use:

```bash
chmod 600 "$HOME/.config/senai/telegram.env"
senai telegram --env-file "$HOME/.config/senai/telegram.env" --project /home/rk/SentiensHermes --skip-git-repo-check
```

The loader accepts only these two KEY=VALUE assignments (optional matching quotes),
not shell scripts, `export` commands, or variable interpolation. Already-exported
environment values take precedence over the file. Do not commit the real file.
Bot credential variables are removed from the senai/Codex child environment.

## 8. State, retries, and shutdown

State is under the selected project's outputs/:

```text
outputs/.senai-telegram/<bot-id>/
  bot.lock
  state.sqlite3
  jobs/<request-id>/stdout.txt
  jobs/<request-id>/stderr.txt
```

The SQLite store retains the update cursor, authorized prompts, job states, results,
and sent-reply progress. Keep it private; it contains conversation content.

- Duplicate updates do not rerun jobs.
- Telegram send/network failures retry delivery without re-executing completed work.
- A result part can be duplicated if the process crashes after Telegram accepts it
  but before its local delivery marker is saved. Exactly-once delivery is not promised.
- On restart, previously running work becomes interrupted and is not automatically
  retried. Inspect outputs/logs before manually resubmitting.
- Already accepted queued work remains queued and can run after restart, subject
  to the current allowlist. New messages sent while the service was offline are skipped.
- /status and /result are private to the requesting user. Revoked users cannot run
  already queued work or receive pending results.
- One process may poll a bot/project at a time. Do not run the same bot in multiple projects.

Press Ctrl+C once in WSL to stop polling. The adapter waits for any active request
to finish before exiting; queued jobs and pending replies remain saved for restart.
This version has **no /cancel command**, no automatic background-service installation,
no voice/photo/file attachments, and no file-download interface.

## 9. Troubleshooting and verification

| Symptom | Check |
| --- | --- |
| Missing token/allowlist error | Configure both in the same terminal, or use --env-file. |
| Telegram status 401 | Recheck/reissue the BotFather token. |
| Existing webhook error | Use a dedicated polling bot or explicitly manage its current webhook. |
| Already-running/409 error | Stop the other local poller before starting a new one. |
| No reply | Wait for ready, check numeric ID and private chat, then send /start again. |
| Request queued but no result yet | Ask /status; Codex can take time. Result polling may add about 10 seconds. |
| Codex login or permission error | Fix Codex locally; remote work cannot answer interactive approvals. |
| Local network error | Check internet; durable completed results remain pending for delivery. |

```bash
cd /home/rk/SentiensHermes/senai
python3 -m unittest discover -s tests -v
senai telegram --help
```

All 100 current tests pass offline. Telegram API calls use fixtures in tests, and
an integration test uses a real senai child plus fake Codex. The user confirmed live Telegram operation on 2026-11-08; individual manual QA subcases have not all been independently recorded.
See [manualqa.md](../tests/manualqa.md) for live Telegram acceptance checks.
