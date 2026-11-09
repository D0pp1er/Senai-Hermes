# Command reference

Use senai --help and each command's --help for exact arguments.

| Command | Purpose |
| --- | --- |
| senai --project PROJECT "REQUEST" | Write/edit in PROJECT/outputs/ |
| senai - | Request from stdin |
| senai -m MODEL -p PROFILE -c KEY=VALUE "REQUEST" | Native configuration |
| senai -i IMAGE --search --skill NAME "REQUEST" | Image context/search/installed Codex skills |
| senai --json -o response.txt "REQUEST" | JSON events and saved final response in outputs/ |
| senai --resume UUID "REQUEST" | Exact native session |
| senai --last "REQUEST" | Native latest session, without installation memory |
| senai chat --project PROJECT | Native interactive terminal |
| senai review --project PROJECT --uncommitted | Read-only native review; also --base / --commit |
| senai codex --project PROJECT -- ARGS | Native argument forwarding |
| senai telegram --project PROJECT --configure | Bot onboarding |
| senai telegram --project PROJECT --pair-code | Local pairing code |
| senai telegram --project PROJECT --revoke-user ID | Revoke authorization locally |
| senai telegram --project PROJECT --voice-configure | Optional hidden voice-key setup |
| senai memory --installation ROOT COMMAND | Global installation memory management |
| senai cron --project PROJECT COMMAND | Schedule management only |
| senai cron worker --project PROJECT --telegram-account ID | Explicit execution/delivery supervisor |
| senai cron worker-status --project PROJECT --telegram-account ID | Saved worker health |

Telegram: /pair CODE, /help, /run REQUEST, /status, /result, /session,
/voice QUESTION and bare /voice. Success sends audio only; unavailable/failed audio
falls back to text. /result explicitly returns text. There is no /new/reset command.
Structured /cron management needs --enable-cron; see the cron guide.

Memory: remember, add/update/list/delete/context, profile-show/propose/apply,
session-context, evaluate-events. evaluate-events is a dry run, never trusted approval.
Personal confirmation and milestone checks are documented in the learning guide.

Cron: create/show/edit/list/runs/deliveries/misfires/dry-run/pause/resume/delete/interrupt.
Use --telegram-account ID to manage chat's store; edits require --expected-revision.
Interrupt requires proving the old worker stopped. See [cron details](../projectprogress/cron.md).

Convenience image/schema inputs resolve from the calling directory; outputs resolve
inside outputs/. Forwarded native input paths resolve from outputs/. Workspace
relocation/expansion flags are rejected. Native review uses Git repository scope,
potentially including the parent repository. MCP/plugins/models/skills are delegated
to Codex; Senai does not install/import/relearn arbitrary skills.
