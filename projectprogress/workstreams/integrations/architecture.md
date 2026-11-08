# Integrations architecture

## Transport and execution

IncomingRequest is immutable and distinguishes platform, bot account, canonical
parent project, event, sender, delivery target and session scope. TelegramAdapter
normalizes private messages and delegates authorization/pairing/commands to Router.
Request identity: (platform, account, project, event). Session scope: (platform,
account, project, telegram-shared). All authorized Telegram users intentionally share
one exact native Codex UUID per configured bot/project. No implicit cross-platform
sharing. Existing queue/executor and shared-session machinery are retained.

## Conversational replies

CLI opts into the five approved random acknowledgements; direct Router callers keep
legacy defaults. Success responses omit status headers; failures remain explicit.
Saved delivery_snapshots freeze text chunks across retries/upgrades. Chat style is
applied each turn, including resumed sessions: concise plain text, Telegram-viewer
context, accessible content rather than host-only links, no false delivery claims.
The media-enabled variant describes actual photo delivery. Existing code/literal
user requests are never stripped of Markdown characters.

## Images

CommandRunner receives MediaOutbox by injection. Its per-job attachments.json is an
explicit selection manifest: {"images":["relative/path.png"]}. The model may create
new images using installed Codex image generation, or select requested existing
workspace images. It must save/copy new images into outputs/. The adapter does not
implement its own image model/API. Generation availability is a runtime capability;
offline tests use fake Codex output and image fixtures.

MediaOutbox snapshots only selected PNG/JPEG files, at most four and 10 MiB each.
Reject absolute/outside/parent/hidden/private-state paths and symlinks, including
snapshot parent symlinks. Copy bytes before job completion and hash snapshots.
No blind directory scanning. BotAPI uses multipart sendPhoto with generic filenames
so upload metadata does not expose host paths. Permanent 400/413 rejection yields
an in-chat fallback; transient failures retain the upload cursor.

## Voice

/voice QUESTION queues one voice-enabled answer; bare /voice reads the latest
successful answer in that same private chat without a new model call. Ordinary
messages stay text; there is no global toggle or inbound voice transcription.
Missing speech configuration gives a short direct reply without enqueuing work.

Router records intent in media.sqlite3 before enqueue, bound to job ID, user, chat
and SHA-256 of the exact prompt. No command marker is embedded in prompt text; /run
with a literal /voice prefix retains its meaning. Orphan metadata from busy/duplicate
updates cannot match an unrelated prompt/identity. Native session mappings are not
changed by reading an existing answer aloud.

OpenAISpeech(text) returns bounded MP3 bytes from the official OpenAI speech API.
It is injected into CommandRunner; optional startup configuration reads local
OPENAI_API_KEY, SENAI_TTS_MODEL (default gpt-4o-mini-tts), SENAI_TTS_VOICE (coral).
No credential lookup/network work occurs on import. Speech is requested only for
/voice jobs; maximum 4000 text characters and 10 MiB audio, timeout 90 seconds.
Speech failure preserves text. BotAPI sendVoice includes an AI-generated caption.
Generated audio is snapshotted before job completion; delivery retries do not call
Codex or speech generation again. OPENAI_API_KEY is removed from child environment.

## Storage and delivery

Existing Telegram jobs DB unchanged by media: prior compatibility migrations and
delivery_snapshots remain intact. New independent media.sqlite3 schema v1 has:
- uploads(job_id PRIMARY KEY, items JSON, sent INTEGER)
- voice_requests(job_id PRIMARY KEY, user_id, chat_id, prompt_hash, mode)

State belongs to this configured bot/project under outputs/; artifacts remain local.
BotService delivers saved text chunks, pending media, then marks the job delivered.
Authorization is rechecked before each media upload. Snapshot hashes prevent sending
modified content. Revoked users receive no pending text/media. Missing/corrupt media
gets a brief fallback rather than blocking the outbox. A crash after successful
remote send but before cursor persistence may duplicate that item; exactly-once
remote delivery is not claimed. Interrupted execution is not silently rerun.
