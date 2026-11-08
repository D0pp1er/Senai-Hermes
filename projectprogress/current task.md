# Current task

Operator-independent automated Telegram setup and one persistent shared Codex conversation.

Branch: feature/telegram-sessions.
Status: implemented and verified; documentation links/examples checked. New live Telegram onboarding
requires operator restart/setup, while the shared Codex session path is live-verified.

User decisions: local-code pairing; all paired users share the same conversation.

Completed:
- scripts/setup_telegram.sh: hidden token validation, code pairing, protected per-project
  env-file saving, and automatic startup; no manual ID lookup/export.
- Persistent paired accounts, one-use/expiring codes, local revocation, legacy config support.
- Exact native shared-session capture/resume, job/session tracing, old-state migration,
  interrupted-event recovery; no --last or silent one-off fallback.
- All 126 tests pass. Live Codex remembered a marker across a runner/store restart
  for another simulated Telegram user with the same saved session ID.
- Architecture, features, setup guide, README, and manual QA updated.

Next operator action: stop the old bot gracefully, then run scripts/setup_telegram.sh
with the project to control. No real token was read or changed during implementation.
