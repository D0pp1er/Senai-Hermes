> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

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

## Optional voice setup handoff (supersedes environment-only setup instructions)

Storage increment b57379a; CLI/setup increment follows in Git history. See features.md
for operator commands, precedence and graceful-restart guidance. No coordinator-owned
source changes, dependency additions or migrations needed. Existing installed CLI
routes through the feature-owned Telegram CLI; root dispatch stays untouched.

New APIs in senai.telegram.voice_config:
- default_voice_file(project, *, environ=None) -> Path
- write_voice_key(project, key, *, environ=None)
- read_voice_key(project, *, environ=None) -> str | None
- remove_voice_key(project, *, environ=None) -> bool
- resolve_voice_key(project, *, environ=None) -> VoiceKey | None (secret excluded from repr)
- configure_voice(project, *, stdout, prompt=None, environ=None) -> bool
- offer_voice_setup(project, *, stdout, choice=None, prompt=None, environ=None) -> bool
- manage_voice(project, action, *, stdout, stderr, prompt=None, environ=None) -> int
- speech_from_configuration(project, *, environ=None) -> OpenAISpeech | None

Existing environment users and native Codex API auth remain supported. A saved dedicated
voice key intentionally takes precedence over generic OPENAI_API_KEY, isolating voice
from native authentication. Removing the saved key does not unset environment variables
or instantly disable a running bot; messages explain the restart/env behavior.
/voice still sends text plus matching audio. No real key, Telegram API, speech API,
production state, merge, bot stop/start or live restart was used for this task.

Coordinator handoff: review feature/integrations with tested implementation fa9c209 plus final records. Rerun --ready and 210 tests; no shared source patches, dependencies or migrations required. Do not restart the live bot as part of this task. Existing credentials/state/native UUID and text-plus-audio semantics are preserved.

## Current voice output policy: audio only, text fallback

This requested change supersedes earlier text-plus-audio instructions. No new key,
provider, environment/auth change or shared source patch. Only an additive
voice_delivery table in media.sqlite3; no Telegram jobs/session/credential migration.
New APIs: has_voice(job_id) -> bool; deliver_voice(job, api, *, authorized) -> str
(audio/fallback/revoked); deliver(job, api, *, authorized, skip_voice=False).
A stored audio/fallback choice keeps restarts from producing both formats. Existing
text delivery snapshots/part cursors remain usable; already-partial legacy text
finishes without audio. No text acknowledgement for accepted /voice requests.
Normal chat, photo delivery, explicit /result, optional key setup and native auth stay.
No merge/restart/live API playback performed; coordinator review is the next step.

## Voice-only integration (2026-11-09)

Merged feature/integrations through fadeea4 (tested implementation c858952) in af84cc2. Feature scope/readiness and all 216 branch tests passed again. Resolved the Telegram CLI startup conflict by combining protected optional speech loading with existing cron deadlines and independent delivery callbacks. Added tests/coordination/test_voice_cron_composition.py for configured/unavailable speech alongside cron startup. All 345 combined tests passed. Logs: outputs/qa-integrations/coordinator-voice-review.log in the feature worktree, and outputs/voice-only-combined-regression.log plus outputs/voice-cron-composition.log on main.

Current /voice policy supersedes prior text-plus-audio documentation: audio only on successful upload, text fallback when unavailable/failing, no text acknowledgement, and persisted audio/fallback choice across delivery retries. Legacy partial text replies finish as text. Explicit /result still returns text. Optional local voice configuration commands are included; setup remains skippable. New voice_delivery storage is additive and media-local.

No Telegram credentials, production jobs/pairing/media/native authentication/session state were accessed or changed. No bot restart, live API test, push or deployment was performed. No further blocking code fixes found. Later operator-managed live QA should verify /voice QUESTION, bare /voice, explicit /result, unavailable-key fallback and restart/retry continuity. Network acceptance followed by local persistence failure remains an acknowledged ambiguity; no exactly-once claim.

Safely update the feature worktree using a fast-forward merge (do not rebase already-integrated history). The coordinator has NOT updated that worktree:
    cd /home/rk/SentiensHermes/senai-integrations
    git status --short
    git branch --show-current
Stop if the tree is not clean or the branch is not feature/integrations. Then:
    git merge --ff-only main
    source .venv/bin/activate
    python -m pip install -e .
    python -m pip check
    python -m unittest discover -s tests -v
    python scripts/check_workstream_scope.py --feature integrations --ready
Reinstalling in this worktree's .venv includes the cron dependencies now present on main; never use pip --user or reinstall globally. If fast-forward refuses because new feature commits were added, stop for coordinator review; do not reset or automatically rebase. These commands do not restart the bot or migrate live runtime state.

## Telegram UX contract proposal — cron conversation

Feature-owned factory: create_conversation_router(base_router, **kwargs) returns
ConversationRouter(base_router, *, project, account, parse_schedule=None,
create_schedule=None, advanced_handler=None, timezone='Asia/Dhaka', clock=None,
draft_ttl=600, new_session_users=(), session_guard=None).

Requested cron-team parser seam (not yet merged; injected in tests):
parse_schedule(when: str, repeat: str, *, now: aware datetime, timezone: str) -> dict
with at (aware datetime), optional timezone (must match input), every (positive int
seconds or None), cron (five fields or None). No additional natural-language parser
is implemented here. Cron owner must reject past/ambiguous date/year/DST interpretations
and support the UX-contract examples. Relative reference time is frozen when the
user answers when; confirmation checks future time again instead of moving a relative
reminder. Explicit advanced ISO/calendar inputs reuse datetime and merged next_after.

create_schedule(spec, *, target, request_key) -> nonempty schedule ID. spec contains
name,prompt,at(aware),timezone, optional every/cron, misfire,grace_seconds,retries,
retry_delay. target is canonical Telegram account/project/scope/user/private-chat.
request_key is stable per draft, reserved for coordinator/backend idempotency support.
A persisted 'creating' claim precedes callback execution; unknown callback outcomes
remain uncertain and are not automatically retried. DraftFieldError(field,message)
certifies no schedule was persisted and safely retries the named field. Raw exception
messages are never shown. bind_schedule_creator(store, *, project, authorize_target,
scope='telegram-shared') adapts the already merged Store with destination authorization.

Coordinator composition: construct TelegramCron as today; pass its handle method as
advanced_handler, bind its store/authorize through the helper, supply the cron parser,
then wrap the conversation router in TelegramAdapter. Leave the existing foreground,
cron worker and delivery callbacks unchanged. Do not put TelegramCron outside this
router: its legacy /cron create handler would intercept wizard messages first.
Other advanced actions delegate; old generic rejection text is mapped to action-level
instructions. No shared source/router/defaults changes applied by this feature.

State: protected conversations.sqlite3 beside the per-bot state DB, bound to canonical
account/project. Drafts isolated by user/chat, expire after 10 minutes, preserve creation
receipts/uncertainty over restart. Telegram queue cursor handles duplicate events.
No schedules created until explicit Confirm. JSON advanced create also previews.
Parser/creation callback absence yields an actionable local-operator message, never
an unsendable schedule or model execution. Fresh-session policy is the next increment.
