# Current task

Add a verifiable master plan and expand Codex CLI compatibility one capability per commit.

Status: completed for the documented compatibility baseline.

## Completed

- main task.md lists required, optional, process, and submission tasks with verification/TDD criteria.
- Separate capability commits cover model/configuration, images, web search,
  skill selection, session resume, interactive Codex, native commands, and code review.
- 40 offline tests pass with no skips, including real child-process transport tests.
- Live WSL code creation and context-preserving resume succeeded.
- Interactive launch, /skills list, and /quit were observed in a real terminal.

## Verification

```bash
cd /home/rk/SentiensHermes/senai
python3 -m unittest discover -s tests -v
senai --help
senai codex -- --version
senai chat
```

## Limits and next work

- Not a claim that every model/plugin/platform-specific native command was live-tested.
- Workspace-relocation flags conflict with outputs/ and are rejected.
- Research comparison, complete chat export, and Google Slides remain pending in main task.md.
- No additional implementation task is currently assigned.
