# Revised skills workplan

Updated 2026-11-09: user needs a working demonstration fast. Obsidian export is deferred until LAST. This is backlog ordering, not a scheduled automation.

## 1. Working terminal demonstration (current delivery)

`python -m senai.skills demo --live` imports an intentionally lossy CSV-identifier fixture, runs real Codex, records independently checked failure evidence, requests an inactive correction, regression-checks real candidate output, activates it, reopens the registry, reuses it on held-out input and restores the baseline. Four Codex calls maximum; optional --model. Default demo remains offline-simulated.

Live acceptance observed: baseline values [[1,2],[10,20]] lost identifier strings/zeros; candidate produced [["001","002"],["10","20"],["003","9"]], passing 4/4 regression checks; held-out result [["007","000","42"]] passed 2/2. Registry audit retained import/activate/rollback. Evidence retained in outputs/skills-qa/live-demo-report.json and its isolated project. This is a controlled corrective example, not evidence of universal improvement or new-skill discovery. Regression failure/no-change/transport failure is reported honestly and never promoted as success.

## 2. Acquisition and real-task usability

DONE: pinned public GitHub acquisition with thirteen validation/provenance/traversal/symlink tests and real official-package QA; local import compatibility retained. DONE: ordinary run CLI uses saved context/resources and explicit checks; real imported skill-creator produced a local instruction artifact with existence and format checks. Further task-specific semantic checks remain caller-defined. Normal senai execution adapter stays coordinator-owned.

## 3. Accurate origin and learning records

Add explicit imported/learned_here/unknown provenance where needed; synthetic fixtures visibly labelled. An imported skill revised here remains imported with a locally_revised flag. Genuine new-skill authoring must be evidence-guided and separately validated. No false learned_here labels based on installation, a demo or wording.

## 4. Production integration and final verification

Coordinator wires context, observed outcomes and optional review hooks into normal CLI/Telegram while preserving native --skill and shared sessions. Verify combined pipeline on isolated state. Keep feature dependencies/migrations in owned paths and declare exact tested commits in final delivery; run --ready when scope is actually complete. No merge/push/deploy is authorized by this plan.

## 5. Obsidian export (LAST; not currently implemented)

One-way Markdown projection from registry into a separate outputs/skills-vault/ folder: Index.md, Skills/<name>.md and concise History/<name>.md. Show active instructions, source, version, imported/learned labels, local revisions, checks and rollbacks. Use flat Obsidian properties and stable links; preserve unrelated notes/.obsidian settings and never edit hashed packages. Empty inventories remain empty, unknown origins unknown, demo evidence synthetic/controlled. No community plugin or personal vault needed by default.

TDD acceptance when resumed: empty export, origin correctness, concise history/link accuracy, refresh after revision/rollback, unchanged registry, user-note preservation, symlink/path rejection and failed-export handling. User then opens the generated folder as an existing vault. No export work or Obsidian UI operation is part of the current demo milestone.

References retained for later: https://obsidian.md/help/manage-vaults and https://obsidian.md/help/properties .
