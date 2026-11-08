# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

First local-registry milestone implemented. Next: add verified outcome records and explicit versioned candidate revisions with injected regression validation and rollback; start with failing tests.

Remaining handoff scope: real archive/public repository import, revision lifecycle and feature-local CLI. Archives are currently rejected wholesale, so traversal and archive symlinks cannot be extracted. No network fetching or automatic skill authoring exists.

Minimal coordinator integration: construct Registry under the selected project's outputs/, pass explicit selected names to select(), and consume returned Skill instruction text/path through an execution adapter. execute(request, names, executor=...) invokes a supplied callback with (request, tuple[Skill, ...]); it does not call Codex. Native --skill and existing prompt/session machinery remain untouched. No shared patches required for module tests.

Dependencies: Python 3.10+ standard library only. New registry.sqlite3 is independent of existing state; no existing DB migration. No global installation/configuration changes.
