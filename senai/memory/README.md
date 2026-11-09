# Memory

One senai installation has one owner and shared profiles across projects and sessions.

## Usage

After senai setup, use the saved installation:

```bash
senai memory add "Finished the first release"
senai user add "Prefers concise replies"
senai soul add "Be clear and thoughtful"
senai memory show
senai user path
```

The root CLI supplies the saved installation and streams to profile_main. For an
explicit standalone adapter, use python -m senai.memory.profile_cli --installation ROOT
followed by memory, user or soul and its action. Root commands need no repeated path.

Every kind supports `add [TEXT]`, `show`, `path`, and explicit `setup`.
Without TEXT, add prompts once with an example when stdin is a terminal.
Noninteractive missing/empty text returns an actionable error without waiting.
Explicit arguments authorize a human append, including SOUL changes.
Automatic learning cannot use this human-only command.

Setup can create a missing installation folder and the three empty profile files.
It preserves existing text and rejects unsafe paths or invalid existing files.
Path and show never create files, directories or databases. Add requires an existing
installation/profile directory; use setup first if it is missing. A missing target
file can then be created by the explicit add command. Profile-only operations do not
open SQLite or alter settings/session state.

Files are under the selected installation:

- `outputs/.senai-memory/MEMORY.md`: core events and milestones.
- `outputs/.senai-memory/USER.md`: preferences, habits, likes/dislikes and significant choices.
- `outputs/.senai-memory/SOUL.md`: explicit human-authored identity/style.

The path command prints the exact absolute filename for direct editing with Codex.
Use show to inspect it. Each file is limited to 4000 characters; shorten a full file
explicitly rather than expecting silent eviction. Credential-looking/control-character
content is rejected. Duplicate notes (case/whitespace normalized) are not appended again.

A session uses a frozen copy loaded at its start. Editing profiles does not rewrite
existing native chats. To load changes, start a fresh request without --resume/--last.
For Telegram, an explicitly permitted /new followed by Confirm starts a fresh shared
session; do not delete profile files or snapshot databases to force a refresh.

Advanced APIs remain available:

```bash
.venv/bin/python -m senai.memory --installation /path/to/installation add "Detailed fact" --provenance manual
.venv/bin/python -m senai.memory --installation /path/to/installation session-context release
.venv/bin/python -m senai.memory --installation /path/to/installation evaluate-events tests/memory/fixtures/noteworthy-events.json
```

The advanced add still stores a SQLite entry; the shortcut add appends Markdown.
Legacy `--project PROJECT --scope SCOPE` mode retains its behavior. No old data is
automatically imported. All automatic personal observations require explicit retention
confirmation; repetition alone is insufficient. Only significant validator-verified
milestones can qualify automatically. The evaluator produces proposals, not writes.

## Architecture

Public human command API:

```python
profile_main(kind, argv, *, installation, stdin, stdout, stderr) -> int
setup_profiles(installation) -> dict[str, Path]
```

The coordinator selects the saved installation and supplies streams. Helpers do not
infer roots from cwd/home, read global defaults, mutate environment, invoke a model,
send messages or start services. There are no import-time writes.

`profile_commands.py` validates paths and uses the existing installation profile store.
Append reads the old revision, preserves old content, creates a human proposal and
applies it with an atomic file replacement under the profile lock. Changed revisions
produce a retry message instead of overwriting concurrent edits. File creation uses
private permissions. Cooperative locks do not protect against hostile external races.

`profile_cli.py` is the standalone demonstration adapter. `profiles.py` owns file
validation/proposals/atomic writes. `installation.py` selects one-owner global state.
`store.py` owns detailed SQLite facts; `context.py` and `session.py` construct bounded
advisory context. `noteworthy.py` evaluates trusted structured evidence without I/O.
`candidates.py` preserves the older explicit marked-line candidate path.
Core `memory_runtime.py` owns native-session/snapshot binding and learning composition.

Shortcut statuses: 0 success/help/duplicate, 2 actionable validation/storage/usage error,
130 cancelled input. Text is not echoed in error messages. No new dependencies or
schema migration are introduced; WSL/POSIX file locking is required.

Verify from an installed checkout using isolated defaults:

~~~bash
python scripts/test.py discover -s tests/memory -v
~~~

See [learning contract](../../docs/memory-learning.md), [architecture](../../docs/architecture.md)
and [manual acceptance](../../docs/all-features-demonstration.md).
