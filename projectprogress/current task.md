# Current task

Prepare four parallel WSL feature environments and self-contained chat prompts.

Status: complete.

- Four worktrees/branches: integrations, memory, cron, skills.
- Each has its own isolated .venv and editable senai command.
- All 126 baseline tests passed in each worktree (504 baseline checks total).
- Import paths verified from outside the repositories; user site is disabled.
- Existing global senai install remains bound to the original main checkout.
- Four complete prompts and shared ownership/execution-boundary guidance are committed.

Next user step: open four chats and paste the assigned prompt. Feature coding begins
in those chats; main remains the integration coordinator. See parallel/README.md.
