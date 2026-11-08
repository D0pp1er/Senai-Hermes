# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Pinned public GitHub acquisition implemented. Registry.import_github(repository, *, commit, path, fetch=None) and CLI import-github require a full immutable commit SHA and explicit package path. Commit/tree identities and every Git blob are verified; bounded downloads validated before atomic registry import. Symlinks/submodules/unsafe paths/truncated trees/duplicates/conflicts rejected; scripts copied as inert files, never run. Existing local importer uses the same atomic file-bundle path.

Thirteen offline source tests pass. Actual unauthenticated CLI import PASS: openai/skills commit 49f948faa9258a0c61caceaf225e179651397431, skills/.system/skill-creator; seven preserved files, package SHA-256 a617b59ca9bc4cf6e15744b6fe4896f1408eac4c1c2d072cc066f720148b59e0. Retained QA project outputs/skills-import-demo/run-izmdpt0k. Report outputs/skills-qa/github-import-report.json. No imported scripts executed/global registries touched.

User also independently confirmed live corrective-reuse demo status completed in outputs/skills-live-demo/run-k7msx0uu. Production routing still unimplemented. Next: actual user-task usability/native execution adapter and durable origin/new-skill authoring records, with coordinator integration proposals. Obsidian export remains LAST.

Reread MERGE_POLICY.md before each implementation step. Scope/full suite before commit; delivery remains draft until complete evidence/--ready.
