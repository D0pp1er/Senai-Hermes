# Current task

Connect senai to a Telegram bot on feature/telegram-bot.

Status: in progress.

User choices: one-off requests; parent project /home/rk/SentiensHermes.

Plan:
1. Bot API/configuration with token-safe diagnostics and long reply splitting.
2. Durable job queue, authorized private-message routing, status, and duplicate protection.
3. Background execution and polling CLI with local setup instructions.
4. Offline integration tests, architecture/user/manual QA updates, and small commits.

Live verification needs a bot created through @BotFather and a locally configured
token/user allowlist. Do not put credentials in chat or Git.
