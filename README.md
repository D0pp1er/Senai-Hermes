# senai

A small Python CLI wrapper for asking Codex CLI to write or edit code.
Scope: one request, project context, Codex execution, and the final response.

Requires Python 3.10+ and Codex CLI installed and signed in (`codex login`).
No Python dependencies are required.

Development uses unittest and small red/green/refactor steps. See CHANGELOG.md.

## Run

From this folder:

```powershell
python senai.py --project "C:\path\to\your\repo" "Create a function that adds two numbers"
python senai.py --project "C:\path\to\your\repo" "Edit the function to reject non-numeric arguments"
```

The target must be an existing Git repository (use `git init` first).
The request goes through stdin to `codex exec`; Codex reads project files and
AGENTS.md, makes changes, and the wrapper prints its final response.
Exit codes: 0 success, 2 input/execution failure, 130 interrupted.

## Verify

```powershell
python -m unittest -v
python senai.py --help
git log --oneline
```

Tests mock Codex to verify transport without consuming account usage.
For a live check, use a disposable Git repo, request a small file, inspect
the new file's contents, then request an
edit and inspect its contents again. Check any generated code independently.

## Design and limits

- Python standard library only. No API key is required by the wrapper; it uses
  the existing Codex CLI authentication and configuration.
- One request per invocation. No memory, scheduling, integrations, or arbitrary
  Codex argument forwarding.
- Write/edit is the offered workflow, guided by instructions; this is not a
  security filter that can guarantee rejection of every other natural-language task.
- Codex may run tools to inspect and validate code under its workspace sandbox.
  Existing Codex configuration and project instructions still apply.
- Progress is buffered; only the final response is printed on success. No retry
  or timeout is imposed because writing code can take a variable amount of time.
- Codex failures can leave partial file edits. Inspect the working tree afterward.
- Reference: https://learn.chatgpt.com/docs/cli/reference
