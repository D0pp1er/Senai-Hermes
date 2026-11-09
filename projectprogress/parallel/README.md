> Contributor workflow template. Paths below are examples; existing worktrees and environments are not included in a clone. Ordinary users should follow the repository README.

# Four parallel workstreams

These are the contributor workstream boundaries. Product usage is documented in README.md.
All worktrees use the same Git repository/history with independent working files.
The original /path/to/workspace/senai checkout remains main and the integration coordinator.

| Workstream | Branch | WSL folder | Handoff |
| --- | --- | --- | --- |
| Integrations | feature/integrations | /path/to/workspace/senai-integrations | [Prompt 1](prompts/01-integrations.md) |
| Memory | feature/memory | /path/to/workspace/senai-memory | [Prompt 2](prompts/02-memory.md) |
| Cron | feature/cron | /path/to/workspace/senai-cron | [Prompt 3](prompts/03-cron.md) |
| Skills | feature/skills | /path/to/workspace/senai-skills | [Prompt 4](prompts/04-skills.md) |

## Use a worktree

Open a separate Codex chat for each feature and paste its handoff prompt. Select the
corresponding WSL folder if the app lets you choose a working folder; the prompt also
contains the absolute path so the agent can use WSL explicitly.

Inside each assigned folder:

```bash
source .venv/bin/activate
python -c 'import senai, sys; print(sys.executable); print(senai.__file__)'
python -m unittest discover -s tests -v
senai --help
```

Both printed paths must belong to that same worktree. A separate pip editable install
is made inside each .venv. Activating one environment does not affect other terminals or later tool calls.
Use the absolute .venv/bin/python or source activation in each separate shell call.
The existing global user senai command continues to point at the main checkout.

Use outputs/qa-project in the assigned worktree for runtime experiments. Do not point
parallel bots, memory stores, skill importers, or schedulers at the production project
/path/to/workspace. Do not duplicate production tokens or private configuration.

## Ownership and integration

Read [execution-contract.md](execution-contract.md). Stable current APIs are frozen;
any older proposal wording there must be checked against current source before use.

Each feature owns its source package, test directory, and workstream progress directory.
Root cli.py, codex.py, prompts.py, options.py, workspace.py, pyproject.toml, requirements-dev.txt,
README.md, CHANGELOG.md, main task.md, and the aggregate progress/architecture/manualqa files
are maintained by the integration coordinator. Do not edit them simultaneously.

If a shared-file change is needed, document the minimal patch/interface requirement in
that feature's current task.md and continue independent module tests. Feature-local CLI
modules remain independently testable; shared routing changes belong to the coordinator.
Declare feature dependencies in a uniquely named requirements-<feature>.txt if needed;
install only into your own .venv. The coordinator consolidates packaging later.

At completion, provide commit IDs, tests and QA evidence, dependencies, proposed integration
patches, migration needs, and limits. Do not merge yourself. The coordinator merges one
branch at a time, wires hooks, updates aggregate docs, and verifies the combined pipeline.

## Current versus historical state

The four modules are integrated on main. This file describes contributor isolation,
not pending product integration. Use the root setup script for a new checkout; do not
assume original local worktrees, wheel caches or QA state are distributed in a clone.
Old preparation counts and environment logs remain in Git history/CHANGELOG.

Mandatory additional guidance: [merge policy](MERGE_POLICY.md) and [ownership map](ownership.json). Fill the per-feature delivery.json and run the scope guard before committing or handing off.

Git pull/push and recovery guidance: [GIT_WORKFLOW.md](GIT_WORKFLOW.md). Preserve reviewed main merge history; use fast-forward-only pulls.
