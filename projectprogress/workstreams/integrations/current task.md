# Current task

Branch: feature/integrations
Worktree: /home/rk/SentiensHermes/senai-integrations

First milestone complete: contract plus working Telegram-compatible adapter.
Next: consult official Discord API/library documentation, write failing Discord
contract tests, then implement offline adapter and feature-local entry point.
Discord is not implemented or live-tested yet.

Shared integration changes needed for this milestone: none. All source changes
are within integrations/ and telegram/. Coordinator packaging review will be
needed when adding Discord dependencies or routing its feature-local entry point.
