# senai

A small Codex CLI wrapper for writing and editing code. Requires Python 3.10+
and an installed, signed-in Codex CLI (`codex login`). No runtime Python dependencies.

## Install in WSL

```bash
cd /home/rk/SentiensHermes/senai
python3 -m pip install --user --no-build-isolation -e .
export PATH="$HOME/.local/bin:$PATH"
senai --help
```

The editable install uses this checkout, so code changes apply immediately.
The PATH export is only needed if ~/.local/bin is missing from your shell PATH.
On distributions that disallow user pip installations, install into a virtual
environment with `python3 -m venv .venv`, activate it with
`source .venv/bin/activate`, and run `python3 -m pip install -e .`.

## Run

```bash
senai "Create hello.py that prints Hello"
senai "Edit hello.py to print Hello world"
senai --project /path/to/repo "Create a function that adds two numbers"
```

All generated code goes into `<project>/outputs/` (current directory by default).
The wrapper creates this folder and uses it as the Codex workspace. Existing
code must be inside outputs/ to be edited. Paths in requests are relative to
outputs/: ask for `hello.py`, not `outputs/hello.py`.
The parent project must be an existing Git repository (`git init` first).
Temporary response files also stay inside outputs/ and are removed after each
invocation. The final response is printed to your terminal.

Exit codes: 0 success, 2 input/execution failure, 130 interrupted.

## Verify

```bash
python3 -m unittest discover -s tests -v
senai --help
git log --oneline
```

Tests mock Codex to verify transport without consuming account usage.
For a live check, run the two hello.py examples and inspect outputs/hello.py.
Check generated code independently.

## Design and limits

- A modular Python package with a `senai` console entry point and no runtime dependencies.
- One request per invocation; no memory, scheduling, or messaging integrations.
- Uses existing Codex authentication and configuration; no separate API key.
- Runs `codex exec --sandbox workspace-write` in outputs/, with the request on stdin.
- Output scope is enforced by the selected workspace and explicit instructions;
  this is not an independent filesystem jail. Codex configuration, tools, and
  inherited project instructions still apply.
- No arbitrary Codex argument forwarding. Progress is buffered; only the final
  response is printed on success. Failures may leave partial edits.
- Development uses unittest with small red/green/refactor steps; see CHANGELOG.md.
- Reference: https://learn.chatgpt.com/docs/cli/reference

## Project layout

```text
senai/                 Python package
  cli.py               Command parsing and request orchestration
  prompts.py           Write/edit instructions
  codex.py             Codex subprocess adapter
  workspace.py         Output-directory validation
  __main__.py          python3 -m senai support
tests/                 unittest tests grouped by responsibility
projectprogress/       Objectives, achievements, and current task
outputs/               Generated code (ignored by Git)
pyproject.toml         Package metadata and console entry point
```

Keep command handling in cli.py, reusable instructions in prompts.py, and Codex
process details in codex.py. Add corresponding tests under tests/. Update
projectprogress/ and CHANGELOG.md when completing a change. Reinstall the editable
package after changing packaging metadata or entry points.

## Codex configuration

```bash
senai --model YOUR_MODEL --profile YOUR_PROFILE -c model_reasoning_effort=medium "Write code"
```

Model/profile availability is determined by your Codex installation and account.

## Image context

```bash
senai -i /path/to/design.png -i /path/to/detail.png "Build this design"
```

Image paths are relative to your calling directory. Files are read as context; generated code stays in outputs/.

## Web search

```bash
senai --search "Use current official documentation to implement this API"
```

This enables native Codex live search through its configuration.
