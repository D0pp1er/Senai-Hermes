# Integration notes: Telegram media milestone

## Integration

No coordinator-owned code patches, sibling imports or packaging dependencies needed.
Merge feature/integrations through the coordinator only; do not auto-merge/push.
Image milestone: cebfe57. Voice milestone commit is recorded in changes.md/history.
Existing Telegram CLI constructs injected media/speech components; top-level CLI is
unchanged. Discord remains a separate deferred workstream target.

## Interfaces

Router(store, allowed_users, username, *, max_pending=4, acknowledge=None,
voice_enabled=False, media=None). Voice disabled unless configured at startup.
CommandRunner(project, state_dir, *, store=None, skip_git_repo_check=False,
model=None, profile=None, search=False, skills=(), chat_style=False, media=None,
speech=None). Its __call__(job) still returns (status, text).
BotService(api, store, router, runner, *, poll_timeout=10, transport=None, media=None).
MediaOutbox(workspace, state_dir): prepare(job_id, manifest), add_voice(job_id, content),
record_voice_request(job_id, job, *, reuse=False), voice_mode(job),
deliver(job, api, *, authorized).
OpenAISpeech(key, *, model='gpt-4o-mini-tts', voice='coral', opener=None):
__call__(text) -> bytes (MP3), raises sanitized SpeechError on failure.
BotAPI.send_photo(chat_id, path) and send_voice(chat_id, path) -> Telegram result.
New kwargs are optional; existing direct callers retain old behavior.

## Configuration and external services

Standard library only; no pip/global installations. Image generation delegates to
installed Codex built-in tools; image_generation flag is enabled here, but a real
model/image invocation was not performed. Availability/account support may vary.
/voice uses the OpenAI Speech API, which needs a local API key and API billing;
ChatGPT/Codex sign-in alone is not used as speech authorization. No live API call
was made. Set SENAI_TTS_API_KEY in the bot process environment only (OPENAI_API_KEY is a supported fallback); do not put it in
chat, tracked files, Telegram credential env files (which accept only Telegram keys),
or command arguments. The dedicated SENAI_TTS_API_KEY is omitted from Codex child environments. Existing
OPENAI_API_KEY/native Codex API authentication is preserved.
Optional SENAI_TTS_MODEL and SENAI_TTS_VOICE customize the speech client.

## Migration and rollback

Media creates its own bot/project media.sqlite3 plus media/<job>/ snapshots; no
Telegram jobs/session/user schema edits. CREATE TABLE IF NOT EXISTS is additive.
Do not delete old jobs, native UUID mappings, text snapshots or media state. Rollback
to a text-only release cannot deliver pending media; retain its DB/files for a later
compatible restart. Back up both stores together when the service is stopped.
No automatic cleanup of historical artifacts is introduced.

## Verified and unverified

184 deterministic offline tests pass, including 31 media/voice tests. Fake network,
fake model/speech and temporary fixtures only. Live Telegram photo/voice playback,
image generation, actual TTS authorization/quality and production restart NOT RUN.
Model response formatting/image manifest compliance remains runtime-dependent.
Limits: PNG/JPEG only, 4 images, 10 MiB/image; speech 4000 chars, 10 MiB; text remains
available; /result resends text only; /voice requests latest audio explicitly.

## Primary documentation

https://core.telegram.org/bots/api#sendphoto
https://core.telegram.org/bots/api#sendvoice
https://developers.openai.com/api/docs/guides/text-to-speech
https://learn.chatgpt.com/docs/image-generation

Optional key storage uses separate version-1 JSON; no Telegram config or DB migration. No new runtime dependency. Old voice environment helper remains supported unchanged.
