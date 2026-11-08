# Four parallel workstreams

This is the shared preparation baseline, not an implementation of the four features.
All worktrees use the same Git repository/history with independent working files.
The original /home/rk/SentiensHermes/senai checkout remains main and the integration coordinator.

| Workstream | Branch | WSL folder | Handoff |
| --- | --- | --- | --- |
| Integrations | feature/integrations | /home/rk/SentiensHermes/senai-integrations | [Prompt 1](prompts/01-integrations.md) |
| Memory | feature/memory | /home/rk/SentiensHermes/senai-memory | [Prompt 2](prompts/02-memory.md) |
| Cron | feature/cron | /home/rk/SentiensHermes/senai-cron | [Prompt 3](prompts/03-cron.md) |
| Skills | feature/skills | /home/rk/SentiensHermes/senai-skills | [Prompt 4](prompts/04-skills.md) |

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
is made inside each .venv. Activating one environment does not affect other terminals.
The existing global user senai command continues to point at the main checkout.

Use outputs/qa-project in the assigned worktree for runtime experiments. Do not point
parallel bots, memory stores, skill importers, or schedulers at the production project
/home/rk/SentiensHermes. Do not duplicate production tokens or private configuration.

## Ownership and integration

Read [execution-contract.md](execution-contract.md). Stable current APIs are frozen;
future shared hooks described there are proposals, not implemented functions.

Each feature owns its source package, test directory, and workstream progress directory.
Root cli.py, codex.py, prompts.py, options.py, workspace.py, pyproject.toml, requirements-dev.txt,
README.md, CHANGELOG.md, main task.md, and the aggregate progress/architecture/manualqa files
are maintained by the integration coordinator. Do not edit them simultaneously.

If a shared-file change is needed, document the minimal patch/interface requirement in
that feature's current task.md and continue independent module tests. Feature-local CLI
modules can be demonstrated without wiring the shared top-level router yet.
Declare feature dependencies in a uniquely named requirements-<feature>.txt if needed;
install only into your own .venv. The coordinator consolidates packaging later.

At completion, provide commit IDs, tests and QA evidence, dependencies, proposed integration
patches, migration needs, and limits. Do not merge yourself. The coordinator merges one
branch at a time, wires hooks, updates aggregate docs, and verifies the combined pipeline.

## Environment reproduction

WSL system Python lacks ensurepip. The initial environments are created with venv
--without-pip, then bootstrapped with pinned packaging wheels using pip --python.
A shared read-only wheel cache is under main's outputs/parallel/wheels. It contains
packaging tools, not runtime state or secrets. Final setup evidence is recorded in
main's outputs/parallel/environment-report.json and setup logs.

No feature implementation, Discord connection, live cron job, shared memory database,
or global skill import is enabled by this preparation.
