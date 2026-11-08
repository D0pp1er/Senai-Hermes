# Objectives

- [x] Accept a request through the installed senai command.
- [x] Pass input and context to Codex CLI and return the final response.
- [x] Keep generated product code in outputs/.
- [x] Keep implementation modular and tests under tests/.
- [x] Add Codex capabilities incrementally, with failing-first tests and one capability per commit.
- [x] Support model/configuration, images, search, explicit skill selection, and session resume.
- [x] Provide native interactive, review, and command-forwarding modes.
- [x] Record master requirements, verification, limitations, and progress.

The current compatibility baseline is complete. Full PDF submission requirements,
optional Hermes features, and their statuses are tracked in ../main task.md.
Native accounts, tools, and workspace-relocating flags retain documented limits.

- [x] Add Telegram transport around one-off senai execution, with private allowlist authorization, durable queue and replies.
- [x] User confirmed live Telegram operation after local setup (2026-11-08); detailed regression cases remain available.

- [x] Replace one-off Telegram turns with one durable shared Codex session.
- [x] Automate setup without personal IDs/paths in code; support local-code pairing and private config discovery.
- [ ] Manually accept the new setup/pairing flow after restarting the existing bot.
