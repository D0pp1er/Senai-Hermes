# Integrations architecture

senai.integrations.contract defines immutable IncomingRequest and structural
TransportAdapter: normalize, authorize, handle, delivery_parts and send_text.
Normalization preserves original text, including commands. It does not grant
permission or enqueue work; Telegram Router remains responsible for command
parsing, pairing, authorization, queue bounds and atomic duplicate consumption.

Request identity is (platform, verified bot account, canonical parent project,
event ID). Delivery target and sender are distinct fields even though Telegram
currently accepts only matching private chat/user IDs. Session scope is
(platform, account, project, session name). Telegram uses telegram-shared,
shared intentionally among authorized users, matching existing durable storage.
Future transports must use a distinct platform scope; no implicit cross-platform
history sharing is authorized by this contract. Native UUIDs remain in JobStore;
scope metadata does not create, replace or select native sessions.

TelegramAdapter delegates to the existing Router and shares its validated private
message parser. Telegram CLI constructs it after bot identity verification.
BotService receives the adapter as its router and optional delivery transport.
Existing worker, CommandRunner, SQLite cursor, delivery part cursor and retry
behavior remain in place. The optional transport preserves old service callers.
Delivery redacts before Unicode-aware splitting and propagates errors for outbox
retry. A crash after a successful remote send but before saving its part cursor
can still duplicate that part; exactly-once remote delivery is not claimed.

Adapters/stores are bound to one configured bot/project; normalized identity is
metadata, not a new multi-platform database. Do not point two transport workers
at the same legacy store. No schema migration or external dependency required.

## Telegram conversational presentation

chat.py holds five approved random acknowledgement options and a per-turn response
style preamble. Telegram CLI opts into Router acknowledgement injection and
CommandRunner(chat_style=True). Style instructions apply even when resuming old
shared history; saved requests remain verbatim. Default direct constructor callers
keep legacy acknowledgements/literal requests. Successful replies and /result omit
request/status headers; failures remain explicit. The API already sends plain text
without parse_mode. We prefer plain text through instructions rather than stripping
Markdown characters and damaging code. Ordinary replies target 1-3 short sentences;
necessary detail and explicitly requested code remain allowed.

## Merge review: pending delivery compatibility

Persist exact redacted message chunks before sending. Pre-upgrade partially sent replies retain legacy formatting; retries reuse saved chunks. The additive delivery_snapshots table does not rewrite jobs, offsets, authorization or shared sessions. Two regression tests failed before the fix and now pass. Full suite: 151 tests passed at 7487862. Live bot/config/state were not accessed.

## Remote viewer context

chat_request states the user reads only Telegram, cannot open host files, and needs
inline content or a genuinely accessible link. File paths are not erased blindly;
explicit troubleshooting paths remain possible when labeled server-only. Capability
instructions are text-only until actual media delivery is implemented. They prohibit
claiming that media was delivered without confirmation. These are model preferences,
not a guarantee against all model-generated local-path references. Long-response and
empty-response runner fallbacks also avoid inaccessible host log links in chat mode.

Media roadmap (not implemented): explicit authorized artifact selection inside the
configured outputs workspace, photo/file upload, and an outbound voice path with an
injected speech generator. Image generation and speech synthesis are distinct from
Telegram transport; neither is supplied by this patch. No inbound transcription is
requested. Retain text replies and short status messages alongside future media.

## Image delivery

MediaOutbox(workspace, state_dir) owns separate media.sqlite3 with an uploads table:
job_id primary key, immutable JSON items, and sent cursor. No Telegram jobs schema
change. Runner writes per-job attachment-manifest instructions; Codex selects existing
or newly generated PNG/JPEG files via {"images":["relative/path.png"]}. The runner
validates and snapshots selected bytes before marking success. PNG/JPEG signatures,
10 MiB/image, four images, visible relative paths only; no symlinks, private state,
URLs, parent traversal or outside files. Media credentials stay outside the model.
BotService sends its saved text snapshot first, then pending media, then marks delivery.
Revocation is checked before each upload. Retry resumes media without rerunning the
job or already-sent text. Permanent 400/413 rejection becomes a brief chat fallback.
Snapshot hashes detect modification. Crash after remote send before local commit may
still duplicate an attachment; exactly-once remote delivery is not claimed.
