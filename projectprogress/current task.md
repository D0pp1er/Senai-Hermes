# Current task

Connect senai to a Telegram bot on feature/telegram-bot.

Status: implementation verified offline; live onboarding pending user credentials.

User choices: one-off requests; /home/rk/SentiensHermes as the parent project.

Completed:
- Standard-library HTTPS Bot API client, secret-safe configuration/errors, reply splitting.
- Mandatory private user allowlist, run/help/status/result commands, bounded durable jobs.
- Separate worker, literal senai child requests, bot credentials removed from child environments.
- Duplicate handling, result-delivery retries, single-process lock, restart recovery.
- Setup/check commands; architecture, user setup, features, and manual QA documentation.
- All 100 tests pass offline. No live Telegram connection has been claimed.

Next user step: create a bot with @BotFather, enter its token in a hidden WSL
prompt, run senai telegram --setup, then configure the printed numeric user ID.
See telegram.md for exact steps. Never paste or commit the bot token.
