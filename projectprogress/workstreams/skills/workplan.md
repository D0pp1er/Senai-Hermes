# Revised skills workplan

Updated 2026-11-09 for requested Obsidian inventory and learning history.

## Progress estimate

Approximately 60% of the expanded goal is implemented. This is a rough scope-weighted planning estimate, not measured correctness or production readiness. Local registry/metadata (20/20), evidence/review/revision/check/activation/rollback foundation (25/30), feature-local management CLI/demo (15/15), public acquisition (0/10), Obsidian view (0/15), production wiring/live reuse (0/10). Total 60/100. Existing offline baseline: 209 tests pass; live improvement remains unverified.

## 1. Obsidian-readable inventory (next TDD step)

Add a one-way Markdown export from the chosen project registry to a dedicated outputs/skills-vault/ folder. Default vault layout: Index.md, Skills/<name>.md, History/<name>.md. It should open as an existing folder in Obsidian without community plugins or changes to an existing personal vault. Empty registries produce an honest empty index, not fake acquired skills. Export is a view of the same project registry; no global skill scan.

Index shows name, description, active version, origin and links. Each skill note includes active instructions, compatibility declarations, source/provenance and update state. Short history notes include dates, why changes were proposed, observed-check summaries, accepted versions and rollback events. Do not dump raw requests/results/logs by default. Keep stable names/links, proper flat Obsidian properties and generated notes separate from personal annotations. Refresh only exporter-owned content, preserve unrelated notes/.obsidian configuration and reject symlink/path escapes. Never write Markdown views into the hash-protected package folders.

TDD acceptance: empty export, two skills with different provenance, instruction/history links, repeat export after accepted update/rollback, valid Markdown properties, no registry mutation, user-note preservation, failed export without partial authoritative pages, no path escape. An automated snapshot/render check is not an observed Obsidian UI test.

## 2. Durable origin and learning-history classification

Add explicit provenance/origin fields as needed with an additive feature-local migration. Distinguish imported, learned_here and legacy unknown. Demo fixtures must be visibly synthetic. A skill originally imported and revised locally stays imported with a locally_revised flag; do not relabel its origin learned_here. Learned_here means a new reusable package created through this project's evidence-guided authoring flow, not installation of an existing package or a synthetic fixture. Proposed/rejected changes remain clearly distinct from accepted learning.

Export only claims backed by origin/activation/outcome records. Preserve original source alongside local revision history. Legacy rows with insufficient evidence remain unknown; do not infer origin from skill wording or invent dates. There are no verified real learned skills in the current test/demo inventory.

## 3. Public skill acquisition

Implement explicit GitHub repository/path imports pinned to an exact commit. Test bounded fetches, source revision/content hash, staged validation, duplicate conflicts, unsupported metadata and traversal/symlink rejection before live public-source QA. Never execute downloaded scripts, modify global registries, or silently replace locally revised content. Archives remain rejected until their traversal/symlink behavior has dedicated tests.

## 4. Real authoring/reuse validation

Provide a controlled path to author a new reusable instruction package from independently observed experience, alongside existing revision of imported packages. Add meaningful regression cases and a real isolated reuse demonstration; model explanations or synthetic checks alone do not establish improvement. Retain review/validation evidence and label manual/live checks accurately. Update Obsidian export to expose accepted learning and brief history.

## 5. Production integration and delivery

Coordinator wires selected context and observed outcomes into normal senai/Telegram execution and preserves shared sessions/native --skill. Feature code stays in owned paths. No merge/push/deploy is authorized by this plan. Verify combined pipeline/live acceptance separately, fill draft delivery contract with exact tested commits and run --ready before final delivery.

## User verification sequence

First deliver an export command plus exact vault folder and opening steps. User opens that folder using Obsidian Open folder as vault and checks the index, one skill, origin and short history. Then demonstrate that an accepted local revision and rollback change the exported history after refresh without mutating the skill registry. No Obsidian installation/UI verification has happened yet.

References consulted: https://obsidian.md/help/manage-vaults and https://obsidian.md/help/properties . Obsidian vaults are folders, and note properties are YAML; keep properties flat since nested property UI is unsupported.
