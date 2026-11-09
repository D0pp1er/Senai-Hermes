# Current task

Branch: feature/skills
Worktree: /home/rk/SentiensHermes/senai-skills

Obsidian and Windows-local vault milestone completed. export_vault(registry, *, project, destination=None) and CLI export-obsidian [--destination PATH] create or refresh readable index/skill/history notes. Windows C:\ paths are translated with wslpath (no shell); /mnt/c destinations also supported. Default is the project's outputs/skills-vault. Registry stays authoritative and unchanged.

Twenty Obsidian/export tests pass, including six Windows-local destination/adoption tests. Full offline suite 272 passed. Actual two-skill export YAML/links/history independently verified. Obsidian 1.15.0 installed for the Windows user with explicit user authorization. User reported EISDIR for WSL UNC vault; a Windows-local copy solved it and user confirmed visibility. New command adopted that verified copy and refreshed twice while preserving Obsidian settings. Evidence outputs/skills-qa/windows-vault-report.json and obsidian-artifact-check.json.

Explicitly approved coordinator exception: synced only projectprogress/parallel/README.md byte-for-byte from main (adds Git-workflow link) because main advanced and the ownership guard rejected the older committed copy. No other shared files changed; scope now passes. No branch merge/rebase/push performed.

Next: final module delivery/--ready check, then coordinator reviews/merges and wires normal CLI/Telegram hooks per handoff.md. Export/feature-local demos and use are ready for direct user verification; production integration remains coordinator-owned, not claimed complete.
