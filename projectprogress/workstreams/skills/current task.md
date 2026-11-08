# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Metadata compatibility milestone implemented before public imports. YAML parser supports standard optional license/compatibility/allowed-tools/metadata fields, folded/quoted scalars, comments, nested inert Hermes metadata and metadata.version. Original documents are byte-preserved. Revisions preserve optional declarations. Optional compatibility_check(metadata) can reject select/execute; declarations grant no permissions.

New dependency PyYAML==6.0.3 is pinned in requirements-skills.txt and installed only in this checkout .venv. Rerun feature dependency installation in other environments; coordinator consolidates packaging. No root pyproject edit.

Eight metadata tests and one additional CLI metadata test added; red tests exposed overly long descriptions and rejected valid YAML. Reviewer->proposal->validation->activation metadata preservation verified offline. No live skill execution.

Next step: public GitHub repository source adapter with explicit pinned commit/path, bounded staged downloads, provenance and traversal/symlink rejection tests before network QA. Archive imports still rejected. Normal production execution/outcome/review hooks remain coordinator-owned and unapplied.

Reread MERGE_POLICY.md before each implementation step. Full suite/scope required before commit; delivery draft.
