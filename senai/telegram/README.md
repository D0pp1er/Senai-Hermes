> Main composition is integrated at 8fe1098. See the repository README for current root commands, permissions and startup. Earlier proposal wording below documents the feature API boundary.

# Telegram

## Usage

Use the configured project and installation from the root setup guide. Root aliases
and defaults belong to the coordinator. Current commands include:

| Command | Purpose |
| --- | --- |
| `senai telegram start` | Start one bot using saved defaults; cron is enabled by the root alias. |
| `senai telegram configure` | Protected Telegram token/pairing wizard, with optional voice Configure/Skip. |
| `senai telegram voice-configure` | Configure/update a voice key through hidden local input. |
| `senai telegram voice-check` | Check local voice settings/permissions; no API call or key output. |
| `senai telegram voice-remove` | Remove only the saved voice key; env support remains. |

The long flags (`--configure`, `--voice-configure`, `--voice-check`, `--voice-remove`)
still work. Never put secrets in chat, command arguments, Git, logs or outputs/. Voice
credentials use private project-scoped JSON outside the project; Telegram credentials
remain separate. Changing a saved voice key takes effect after an operator-managed
graceful restart; never launch a second poller. This module does not restart live services.

### Requests, images and voice

Paired/allowed private users send text or `/run TASK`. Normal responses are brief plain
text; selected/generated PNG/JPEG images can be attached from the outputs workspace.
`/voice QUESTION` produces only a voice note on success; bare `/voice` reads the latest
successful answer in that private chat. Text is the fallback for unavailable speech or
failed audio delivery. `/result` explicitly resends text. Voice setup remains optional;
normal text and images need no voice key. Native generation/voice account availability
is a runtime prerequisite, not an offline-test claim.

`/status`, `/result`, `/session`, `/help`, and local pairing/revocation remain available.
All authorized accounts share the configured native conversation and generated files;
private result routing is not a partition of that shared model context.

### Guided schedules

The new UX is exposed by `create_conversation_router` and requires coordinator wiring
with the cron team's parser and authorized destination/creation callbacks. The legacy
startup is not silently replaced in this feature branch. Without those callbacks,
requests get an actionable operator message and cannot create an unsendable schedule.

Once composed, `/cron create` asks one question at a time:

1. A short unique name, such as Tea break.
2. The task, such as Remind me to make tea.
3. When: examples include today at 10pm, tomorrow at 1 am, 10 november 2pm,
   in 2 minutes, or an explicit timestamp with offset.
4. Repeat: for example once, daily, or every 2 hours (supported by the injected parser).
5. A preview with name/task, full local date/time/timezone, repeat, destination,
   lateness policy and retries. Reply `Confirm` or `/cancel`.

No JSON, schedule IDs or scope strings are needed in this flow. Dates/ambiguity are
resolved by the cron parser, never by a second Telegram time parser. Relative reference
time is frozen for the preview; a past preview must be corrected, not silently moved.
Drafts are private per account/chat and expire after ten minutes, except uncertain action receipts which require explicit review/cancellation. Restart preserves an
unexpired draft. Invalid fields get examples/retry prompts; `/cancel` changes no schedule.
Commands such as `/status` still work during a draft without becoming task input.

Advanced `/cron create {"name":"Tea","prompt":"Make tea","at":"2030-11-10T09:00:00+06:00"}`
remains available and also previews before creation. Calendar previews use the existing
cron helper to show the actual first occurrence. Other advanced cron commands delegate
to the existing coordinator runtime; argument/revision errors get actionable help.

Creation gets a durable claim before the callback. If a crash/backend failure makes the
outcome uncertain, review `/cron list` before cancelling/restarting; cancellation clears
only the draft and warns that the earlier action may already have happened; the app will not
retry creation automatically. Duplicate Telegram updates do not create another schedule.
No real schedule or production state is used in the offline tests.

### Fresh shared conversations

`/new` is disabled unless an operator explicitly grants the account in local policy and
a shared execution guard is provided. Pairing alone does not grant permission to reset
everyone's context. An enabled `/new` shows a warning and requires `Confirm` or `/cancel`.

It refuses queued/running work from any user, and the coordinator's guard must cover
foreground/cron execution plus any queued/uncertain scheduled work. Confirmation checks
current authorization, the exact previewed native UUID and queue state again. Starting
another conversation does not revoke users, remove old jobs/results/files/media or delete
native transcripts. The prior UUID mapping is archived privately; future requests start
a new native UUID. Existing archives cannot be silently rebound as fresh. Nothing resets
on startup. There is no remote history-switch/restore command in this increment.

The action affects all authorized users and future scheduled tasks using the shared
conversation. Old native histories/memory snapshots remain intact. Fresh conversations
can read the configured installation's updated profile through the existing child-CLI
memory defaults; the installation owner must not change per request.

### Status and reload

Use `/status` for jobs, `/session` for the active conversation and the local voice-check
command for saved voice settings. Saved settings are not proof of a running process's
active configuration. No automatic restart or remote reload is implemented. A future
status command should show only redacted startup-snapshot capabilities. A future key-only
reload should be local/operator-authorized, idle-gated and atomically update both speech
and routing; it must not retarget project/installation defaults. Coordinator review is
required before exposing that behavior. Until then, use the normal graceful restart.

## Architecture

### Composition boundary

`ConversationRouter` wraps the existing `Router`; `TelegramAdapter` wraps the result.
The coordinator supplies `TelegramCron.handle` as the advanced handler and keeps the
same cron worker, independent delivery callback and foreground executor. Putting the
old cron runtime outside the conversation router would intercept `/cron create` first.

Public entry points:

- `create_conversation_router(base_router, **kwargs) -> ConversationRouter`.
- `ConversationRouter(base_router, *, project, account, parse_schedule=None,
  create_schedule=None, advanced_handler=None, timezone='Asia/Dhaka', clock=None,
  draft_ttl=600, new_session_users=(), session_guard=None)`.
- `bind_schedule_creator(store, *, project, authorize_target, scope='telegram-shared')`.
- `SessionGate(*, is_idle=None)`, `.execution()`, `.idle()`, `.wrap(runner)`.

The proposed parser contract, awaiting cron/coordinator composition:
`parse_schedule(when, repeat, *, now, timezone) -> dict` with an aware future `at`,
optional matching `timezone`, positive integer `every` seconds or `cron` (mutually
exclusive). The cron owner must reject ambiguous dates/years/DST folds/gaps rather than
silently choose an interpretation. Tests inject this parser; no unmerged sibling import
or natural-language implementation is added here.

`create_schedule(spec, *, target, request_key) -> nonempty schedule ID` receives a canonical
account/project/user/private-chat destination. Reauthorize it in the backend. The helper
adapts the already merged cron Store. `DraftFieldError(field, message='')` certifies a
validation rejection with no persisted schedule; unknown errors are not safe to retry.
The request key is stable per draft for optional backend idempotency; existing Store
safety is supplemented by the persisted pre-call claim and name uniqueness.

### State and transitions

`conversations.sqlite3` is a separate mode-600 bot/project-scoped DB beside Telegram
state. It stores the namespace and per-user/chat draft JSON (phase, expiry, frozen spec,
confirmation claim/receipt). No draft answer is queued to Codex. Eligibility, authorization
and mention checks precede transitions. The existing Telegram update cursor deduplicates
handled events. One router instance runs under the existing bot singleton; the in-process
router lock serializes transitions. A crash between the separate queue cursor and draft
write can require re-entering a field; a persisted creation claim prevents automatic
duplicate creation after an uncertain callback outcome.

Fresh confirmation uses the same gate as execution. `JobStore.fresh_shared_session`
locks its existing DB transaction, rechecks authorization/all pending jobs/the expected
UUID, archives the old UUID as a reserved `telegram-history:` session row, then removes
only the active pointer. Existing session schema is reused; no jobs/pairing/media migration.
`session_history()` is a protected local API, not a public history browser. The coordinator
must wrap both foreground and cron runners in the same gate and supply an additional
idle check for scheduler pending/running/retrying/unknown state; a plain status read is
not an execution lock.

### Configured memory and installation pinning

Existing `CommandRunner` uses this checkout's `sys.executable -m senai`, exact native
`--resume UUID`, and shared child-CLI defaults. Configured memory is already enabled by
those defaults; no alternate installation is inferred. Optional `installation=ROOT`
pins the coordinator's startup-selected owner; `installation=''` explicitly pins the
absence of memory config; default `None` preserves legacy default resolution. The
coordinator must pass the same frozen root to foreground and scheduled runners. Explicit
flags prevent changing saved defaults in another checkout from retargeting a pinned
runner. Project/trust/timezone pinning and root aliases remain coordinator-owned.

### Existing delivery guarantees

Text and media snapshots/cursors, private authorization at execution/delivery, voice-only
success/text fallback decisions and conservative cron outcomes are retained. Retries do
not rerun Codex/speech unnecessarily. Remote acceptance followed by a network/local
persistence failure can remain ambiguous; exactly-once external delivery is not claimed.
No import starts a worker, contacts an API, creates a database or activates a schedule.

### Verification

Run `.venv/bin/python -m unittest discover -s tests -v` and
`.venv/bin/python scripts/check_workstream_scope.py --feature integrations --ready`.
Focused UX tests: `tests.integrations.test_conversations`,
`tests.integrations.test_new_session`, `tests.integrations.test_telegram_ux_memory`.
They use injected clocks/parsers, fake Codex and temporary state only. Live Telegram,
natural-language parser composition, credentials, bot restart and actual scheduling
remain coordinator/operator acceptance tasks.
