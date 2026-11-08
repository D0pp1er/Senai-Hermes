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
Standard library only; no dependency or schema migration. Stored user prompts,
shared native session UUID, authorization and result delivery cursor are unchanged.
No sibling-feature imports or shared core/packaging edits.

## Limits
Short/plain-text responses are model instructions, not destructive Markdown
stripping or a strict length cap. User-requested code/detail is allowed. No live
Telegram/model verification performed, and no running bot was restarted.
Acknowledgements use random choice; consecutive repeats are possible. Direct
commands return their own response. Acknowledgement send failures retain existing
queue behavior; acknowledgements are not a separately durable outbox.
Discord remains pending; overall delivery manifest remains draft.
