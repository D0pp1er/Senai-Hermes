# Integration requirements

## Shared patches
None needed for the Telegram chat improvement. All edits are feature-owned.
Coordinator merges feature/integrations; do not copy changes into production manually.

## Interfaces and compatibility
Router(store, allowed_users, username, *, max_pending=4, acknowledge=None)
accepts an optional zero-argument acknowledgement callback. Default retains legacy
queue acknowledgements. Normal Telegram CLI injects the approved random chooser.
CommandRunner(project, state_dir, *, store=None, skip_git_repo_check=False,
model=None, profile=None, search=False, skills=(), chat_style=False)
keeps literal input by default. Telegram CLI enables chat_style on every turn.
result_text(job) now returns only result for succeeded jobs; errors/interrupted
results retain request/status context. This is the requested presentation change.

## Dependencies, storage and migration
Standard library only; no new dependency; additive delivery snapshot table. Stored user prompts,
shared native session UUID, authorization and result delivery cursor are unchanged.
No sibling-feature imports or shared core/packaging edits.

## Limits
Short/plain-text responses are model instructions, not destructive Markdown
stripping or a strict length cap. User-requested code/detail is allowed. No live
Telegram/model verification performed, and no running bot was restarted.
Acknowledgements use random choice; consecutive repeats are possible. Direct
commands return their own response. Acknowledgement send failures retain existing
queue behavior; acknowledgements are not a separately durable outbox.
Discord remains pending outside this ready Telegram milestone.

## Merge review: pending delivery compatibility

Persist exact redacted message chunks before sending. Pre-upgrade partially sent replies retain legacy formatting; retries reuse saved chunks. The additive delivery_snapshots table does not rewrite jobs, offsets, authorization or shared sessions. Two regression tests failed before the fix and now pass. Full suite: 151 tests passed at 7487862. Live bot/config/state were not accessed.

## Viewer-context update and next media scope

No additional shared hooks, runtime dependencies or migrations for this change.
Media remains unimplemented. User wants newly generated/existing images delivered
in Telegram and outbound voice replies; inbound voice transcription is not requested.
Official API references: https://core.telegram.org/bots/api#sendphoto and
https://core.telegram.org/bots/api#sendvoice. Transport upload and model media generation
must be wired separately with offline injectable tests and live acceptance later.

## Image milestone

No shared-file changes/dependencies. Added BotService(..., media=None) and
CommandRunner(..., media=None), both backwards compatible. CLI opts into MediaOutbox.
Separate media.sqlite3 schema v1 is created in configured bot/project state; existing
Telegram tables untouched. Native Codex image_generation is enabled on this host,
but availability/account access and live generation are not verified by offline tests.
Reference: https://core.telegram.org/bots/api#sendphoto and
https://learn.chatgpt.com/docs/image-generation . No API image key is required by
this adapter; it delegates generation to installed Codex tools when available.
