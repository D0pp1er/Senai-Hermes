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

## 2026-11-09: image attachments

Implemented bounded multipart sendPhoto, selected-image manifests and independent
media.sqlite3 snapshots/cursors. Runner asks built-in Codex image generation to
save new artifacts inside outputs/ and select up to four PNG/JPEG files for delivery.
Existing images can be selected in natural language. No folder scanning or automatic
attachment of unrelated images. 11 media tests pass; full suite: 164 tests.

## 2026-11-09: /voice replies

- Image milestone commit: cebfe57.
- /voice QUESTION: one text + voice answer; /voice: read latest successful answer
  from this chat without another model turn. Normal messages remain text.
- Optional injected OpenAI MP3 speech with local config, bounded text/audio and
  generic errors; missing config and synthesis failures preserve normal text use.
- Persist voice intent separately, bound to prompt/sender/chat, preserving literal
  /run input. Durable audio retry does not regenerate or repeat completed text.
- Added AI-generated voice caption, queued restart/revocation/isolation regressions,
  snapshot corruption and parent-symlink checks.
- TDD evidence: missing speech module, literal-mode and snapshot-boundary failures
  reproduced before their implementations. Final: 183 tests, 30 media/voice tests.
- Logs under outputs/qa-integrations/: voice-red.log, voice-green.log,
  voice-literal-red.log, media-boundary-red.log, media-voice.log, regression.log.

Voice implementation commit: c6b930a. Follow-up native-auth regression preserves existing OPENAI_API_KEY for Codex, while filtering a dedicated SENAI_TTS_API_KEY from children. Expected full suite: 184 tests.

## Final media handoff evidence

- cebfe57: image attachments.
- c6b930a: explicit /voice replies.
- a78aa29: native Codex API authentication compatibility.
- Exact tested source commit: a78aa29447c62fac8f60377eb1b3b74a9f8a67dd.
- 184 full-suite tests and 31 focused media/voice tests pass; logs retained locally
  under outputs/qa-integrations/. Scope guard and whitespace check pass.
- Delivery status ready means ready for coordinator review of this media milestone,
  not live acceptance, deployment or completion of Discord. No merge/push/restart.
