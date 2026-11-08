# Integrations change notes

Maintain dated, feature-local changes and short commit IDs here. Root CHANGELOG.md is coordinator-owned.

## 2026-11-09: Telegram chat replies

- Earlier transport contract commit: c8df4d6.
- Added five user-approved randomly selected acknowledgements at normal Telegram startup.
- Accepted requests get acknowledgement before final delivery; duplicates, unauthorized
  events, busy queues and direct commands do not get misleading acceptance messages.
- Added Telegram-only short plain-text model instructions on each new/resumed turn.
- Successful result delivery and /result omit the status header; failures retain it.
- Existing Router and CommandRunner constructors keep legacy defaults; Telegram startup
  opts into acknowledge=acknowledgement and chat_style=True.
- RED: test_telegram_chat failed on missing chat module. GREEN: 5 new behavior tests,
  149 full-suite tests pass; ownership guard and diff whitespace check pass.
- Logs: outputs/qa-integrations/regression.log and chat-tests.log (local, ignored).
