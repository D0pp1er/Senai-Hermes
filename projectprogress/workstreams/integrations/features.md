Current module usage/architecture: [Telegram README](../../../senai/telegram/README.md). This workstream file is retained as a historical milestone record.

> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

# Telegram optional voice setup

Telegram works without a voice key. During `senai telegram --configure` (with or
without `--start`), finish Telegram pairing, then choose Configure or Skip at the
optional voice step. Enter defaults to Skip. Skipping never deletes existing voice
settings; existing environment settings may still enable voice. A failed/cancelled
optional voice step leaves Telegram configured.

## Configure or update later

```bash
senai telegram --project /path/to/project --voice-configure
```

Enter the OpenAI voice API key only at the hidden local prompt. Enter with an existing
saved key keeps it unchanged; Enter with no saved key skips. Never put a key in chat,
command arguments, shell history, Git, logs, Telegram's credential file or outputs/.
Hidden input refuses an echoing/non-terminal fallback. Voice uses the existing OpenAI
speech API; API usage is separately billed. Configuration does not make a paid API call.

## Check or remove later

```bash
senai telegram --project /path/to/project --voice-check
senai telegram --project /path/to/project --voice-remove
```

These local commands need no Telegram token/pairing, never create/open job stores,
and never start/restart/poll a bot. Check verifies local configuration/permissions,
not remote API authorization, model access, billing or sound quality. Exit codes:
0 configured/success, 1 no key on check, 2 invalid config/arguments, 130 cancelled.
Removal is idempotent and removes only the saved voice file. Environment keys remain
supported and may still enable voice.

## Protected storage and precedence

Per canonical project: `$XDG_CONFIG_HOME/senai/voice/<project-hash>.json`, default
`~/.config/senai/voice/<project-hash>.json`. This is separate from Telegram credentials
and must stay outside the controlled project and Git repositories. File mode 600,
voice directory 700, atomic updates, no symlinks/hardlinks/shared permissions.
Read errors are reported without raw data; malformed optional config disables voice
at startup while Telegram continues. Configure again to replace a malformed file.

Key selection on bot startup:

1. `SENAI_TTS_API_KEY` environment variable.
2. Protected saved voice key.
3. Existing `OPENAI_API_KEY` environment fallback.

`SENAI_TTS_MODEL` and `SENAI_TTS_VOICE` remain supported. Dedicated voice environment
keys override file updates; the check command reports only the active source, never
the key. Native Codex `OPENAI_API_KEY` authentication is preserved. A file-loaded key
is never exported into the Codex child environment. No free TTS provider or paid
fallback change is part of this task; old unused local packages are not runtime dependencies.

## Applying changes

A bot reads voice configuration at startup. For an already-running bot, use its normal
Ctrl+C stop, let the active request finish and wait for the process to exit, then
start it once with the same project, environment/Telegram config and existing flags.
Do not start a duplicate bot or repeat Telegram pairing. Setup/update/removal commands
only print this guidance; they do not touch the running process. Without an active bot,
settings apply on the first start.

## Voice-first replies

`/voice QUESTION` sends only an AI-generated voice note when audio succeeds. Bare
`/voice` reads the latest successful answer from that private chat, also as audio
only. Accepted voice commands do not send a separate text acknowledgement/transcript.
The short AI-generated label remains on the voice note. Normal messages stay text.

Text is the fallback when voice is unconfigured, too long, cannot be generated, or
its saved audio is missing/corrupt or rejected/unavailable during upload. The full
answer is retained locally and sent as text on fallback. If that text send also fails,
retry resumes only text: no new model/speech call and no late audio after fallback.
A bare /voice without audio support returns the latest answer as text.

`/result` still explicitly retrieves text when requested. Already-partially-delivered
text from an older release finishes as text without adding audio. Requested images
are unaffected. Telegram authorization failures remain fatal if the bot cannot send
either format; no delivery is claimed. Configuration, pairing, jobs, media and exact
shared Codex sessions are retained. No live merge/restart is performed by this task.
