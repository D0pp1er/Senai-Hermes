> Historical workstream record. For current user setup, compatibility and manual tests, start at the repository README. Earlier counts and plans describe their recorded milestone.

# Cron objectives
- [x] Durable one-shot/elapsed-interval schedules with explicit timezone, project and scope.
- [x] Atomic claims, bounded retries, overlap protection and explicit recovery.
- [x] Injectable executor/delivery and durable results.
- [x] Feature-local CLI and operational verification.
- [x] Transactional outbox with independent restart-safe delivery.
- [x] Unknown outcomes blocked; certified transient retries bounded.
- [x] Calendar cron, explicit misfire controls, missed-occurrence history.
- [ ] Coordinator chat/delivery integration and authorized live acceptance.
- [x] Inspect local next run and safely edit schedules without overwriting active/stale work.
- [x] Provide exact safe management contract for later chat integration.
