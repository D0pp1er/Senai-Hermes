> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

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

## Optional voice-key setup: storage increment

TDD: missing voice_config module reproduced, then 13 tests passed for private file handling, hidden input/Skip, replacement/removal, precedence, and redaction. Protected voice JSON is separate from Telegram credentials and outside Git/project. CLI wiring follows.

## Optional voice setup: CLI increment

- Storage commit b57379a; added --voice-configure/--voice-check/--voice-remove.
- Optional Configure/Skip after Telegram setup, automatic protected-key load at startup.
- Local check is explicit about not validating remote authorization/billing.
- Echoing input fallback and raw parser/prompt errors are blocked; replacement is atomic.
- Standalone commands never touch Telegram credentials, DBs or a bot process.
- Regression fixtures verify old state/session byte hashes and native API authentication.
- /voice text-plus-matching-audio behavior unchanged. No merge or production restart.

## Voice setup delivery evidence

- b57379a: protected optional voice credentials.
- fa9c209: optional initial offer and standalone voice commands.
- Exact tested implementation: fa9c20963ec146339c1c409573255b667b571c33.
- 210 full regression tests and 26 new setup/config tests PASS. Scope/diff PASS.
- Readiness metadata updated for coordinator review; no merge/restart/API/live activity.

## Voice-only output

User requested audio-only /voice success, text fallback. Updated durable delivery choice, omitted voice acknowledgements, added no-key/legacy/retry coverage and revised setup/help/docs. 216 offline tests pass. No changes to credentials/native auth/shared session, no live restart or merge.

Voice-only implementation commit c858952; exact tested commit c858952a171916d28ed34941417c5ce56e4a4baf. 216 full tests and 23 voice tests PASS; scope/diff PASS. Ready for coordinator review, live playback NOT RUN.

## UX cron conversation increment

Fast-forwarded clean feature worktree to e4791e8 as authorized. Baseline 376 tests passed. RED missing conversation module and calendar-preview mismatch reproduced; GREEN 18 conversation tests and 394 full tests pass. Added separate draft state/factory and injected parser/creator contracts. No shared code, production state, service or actual scheduler activation touched.
