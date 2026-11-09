# Setup and troubleshooting

Follow README clone/venv steps in the WSL Linux filesystem. Dependencies (croniter,
python-dateutil, six, tzdata) install from pyproject.toml. Repository read access is required if the GitHub repository is private. No personal venv, account,
bot, runtime state or API key is bundled.

On Ubuntu, if these prerequisites are missing, install them before creating the venv:

~~~bash
sudo apt update
sudo apt install git python3 python3-venv python3-pip
~~~

Install Codex separately following the [official Codex CLI guide](https://developers.openai.com/codex/cli/); no Codex binary or model access is bundled.

## Telegram and voice

Create your own dedicated bot with official @BotFather. With the venv active:

~~~bash
mkdir -p outputs/telegram-project
senai telegram --project "$PWD/outputs/telegram-project" --configure --start --skip-git-repo-check
~~~

Follow local pairing instructions. Optional voice setup can be skipped.
Never paste keys in chat, tracked files or command arguments.

Later start one copy with the same project:
~~~bash
senai telegram --project "$PWD/outputs/telegram-project" --skip-git-repo-check
~~~

Later voice setup/check/removal:
~~~bash
senai telegram --project "$PWD/outputs/telegram-project" --voice-configure
senai telegram --project "$PWD/outputs/telegram-project" --voice-check
senai telegram --project "$PWD/outputs/telegram-project" --voice-remove
~~~

Configuration uses hidden input. Check validates local availability/permissions,
not API authorization or billing. Precedence: SENAI_TTS_API_KEY, protected saved
voice file, then OPENAI_API_KEY. Native Codex authentication remains independent.
Changes apply at startup: Ctrl+C, wait for exit, restart once with the same project.
All paired accounts share model conversation context; pair only trusted accounts.

## Installation memory

Choose one existing root and keep it constant across projects:
~~~bash
mkdir -p outputs/manual-installation
export SENAI_INSTALLATION_ROOT="$PWD/outputs/manual-installation"
~~~

Alternatively use --installation ROOT for ordinary requests. Profiles live at
ROOT/outputs/.senai-memory/. One installation has one owner. SOUL.md is human-controlled.
Enable memory before a fresh session. Profile shortcuts are now available:
senai memory add/show/path, senai user add/show/path, senai soul add/show/path.
Edited profiles load in fresh sessions; old snapshots remain frozen.
An explicitly authorized Telegram /new followed by Confirm starts a fresh native
conversation without deleting history. Grant permissions locally with
senai telegram start --new-session-user ID. Pairing alone does not grant /new.
See the current README for full setup, permissions and test commands.

## Scheduling

Management/list/dry-run never start workers. Use disposable projects first.
Local and Telegram-account stores are distinct. The standalone Telegram worker
requires existing paired/authorized state and holds the same lock as the ordinary
bot; do not start both for one bot/project. See [cron](../projectprogress/cron.md).

## Troubleshooting

| Symptom | Action |
| --- | --- |
| senai not found | Activate this checkout's venv; reinstall -e . |
| ensurepip unavailable | Install matching OS Python venv support |
| codex missing/login error | Install/authenticate Codex in the same WSL environment |
| Not inside trusted directory | Use a trusted Git project or explicitly --skip-git-repo-check |
| Voice returns text | Check local voice configuration for the exact project and provider availability |
| Missing frozen snapshot | Use a fresh CLI session or disable memory for the old bot session; do not delete state blindly |
| Cron never runs | Check correct store, due time, pause state and explicit worker startup |
| Rebase conflict during pull | Stop and review; use fast-forward-only updates |

Use your own test bot, disposable projects and installation root. Never copy another
operator's credentials, pairing state or native session into acceptance tests.
