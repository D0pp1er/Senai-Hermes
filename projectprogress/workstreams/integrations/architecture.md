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
