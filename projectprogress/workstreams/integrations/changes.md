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

## Merge review: pending delivery compatibility

Persist exact redacted message chunks before sending. Pre-upgrade partially sent replies retain legacy formatting; retries reuse saved chunks. The additive delivery_snapshots table does not rewrite jobs, offsets, authorization or shared sessions. Two regression tests failed before the fix and now pass. Full suite: 151 tests passed at 7487862. Live bot/config/state were not accessed.

## 2026-11-09: Telegram viewer context

- Prior conversational reply commit: 26d8da1.
- Every chat-style turn now identifies the reader as a Telegram user without
  access to the host filesystem; asks for useful inline content instead of local links.
- Do not invent public links or claim undelivered image/file/voice attachments.
- Current text-only capability stated explicitly. Necessary, requested troubleshooting
  paths must be labeled server-only. This is response guidance, not a path-redaction filter.
- Chat-style long-response/empty-response fallbacks no longer advertise local log paths.
- TDD: two new tests failed before implementation; 7 chat tests and 153 total offline
  tests now pass. Ownership guard and git diff --check pass.
