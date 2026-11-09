# Senai

A local Codex CLI harness for coding, Telegram, installation-wide memory and scheduled work.

Supported baseline: WSL2 Ubuntu 22.04, Python 3.10+, Git and authenticated Codex CLI.
Last checked Codex: 0.167.0. Full native Windows support is not available; use WSL.

## Clone and install

Run in your WSL shell. Install Python with venv support, Git and Codex first.

~~~bash
git clone https://github.com/D0pp1er/Senai-Hermes.git
cd Senai-Hermes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m pip check
codex --version
codex login
senai --help
~~~

If ensurepip is missing on Ubuntu, install matching python3-venv through your OS
package manager. Do not install Senai with sudo or pip --user. Activate this venv
in every terminal. Senai reuses native Codex authentication and account limits.
Optional voice requires separately billed speech API access.

## First request

~~~bash
mkdir -p outputs/manual-project
senai --project "$PWD/outputs/manual-project" --skip-git-repo-check "Create hello.py that prints Hello"
python outputs/manual-project/outputs/hello.py
~~~

Expected: Hello. Each selected project gets outputs/ as its coding workspace.
Request paths are relative to that workspace; existing code must be there for editing.

## What is available?

| Feature | Current support |
| --- | --- |
| Coding | Write/edit, stdin, models/profiles/config, image context, search, installed skills, JSON output |
| Native modes | Interactive chat, review and argument forwarding within workspace restrictions |
| Telegram | Optional setup, local pairing/revocation, durable jobs, exact shared session, photo attachments |
| Voice | Optional protected key setup; audio-only /voice success, text fallback |
| Memory | Explicit installation root; global USER.md/MEMORY.md, frozen sessions, confirmed personal learning |
| Cron | One-shot/interval/calendar schedules, explicit supervised worker and independent authorized delivery |
| Discord, skill import/relearning | Not integrated on main |

## Guides

- [Setup and troubleshooting](docs/setup.md)
- [Command reference](docs/commands.md)
- [Manual acceptance checklist](docs/manual-testing.md)
- [Compatibility](docs/compatibility.md)
- [Architecture](docs/architecture.md)

## Verify and update

~~~bash
python -m unittest discover -s tests -v
~~~

Offline tests use disposable state and provider fixtures. They do not prove provider
access on your account. Follow the manual checklist for live checks. Installation
does not activate a bot or scheduler.

For updates, stop active work, check git status, use git pull --ff-only, then reinstall
with python -m pip install -e . inside this venv. Preserve reviewed merge history.

Generated artifacts/job/media/memory/cron state live under outputs/. Native Codex
uses its normal account/session directories. Protected Telegram/voice credentials
are stored outside Git in the local configuration directory. Never commit keys
or outputs/. Memory assumes one owner per installation; paired Telegram accounts
share its conversation. outputs/ is a workspace policy, not a filesystem jail.
External execution and sends are not guaranteed exactly once.

[Requirements](main%20task.md) and [workstreams](projectprogress/parallel/README.md)
are contributor records, not onboarding instructions.
