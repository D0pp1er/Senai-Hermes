# Current task

Document the current execution architecture and its maintenance rules.

Status: complete.

Verification: execution paths checked against current source; local links, code fences, Bash examples, and git diff whitespace checks pass. No runtime code changed.

Deliverable: architecture.md covering the two execution paths, all command modes,
module responsibilities, option translation, output/state ownership, error behavior,
and verification links.

Maintenance: update architecture.md whenever execution behavior changes.
Previous feature and manual QA work remains in features.md and ../tests/manualqa.md.
