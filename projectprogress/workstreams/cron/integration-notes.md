# Cron integration notes

No shared patches applied. Coordinator should route senai cron to senai.cron.__main__.main.
Inject authorized existing Codex execution/session adapter into Worker; preserve configured
session policy. Do not import sibling branches or start a separate hidden agent pipeline.

Use DeliveryWorker(store, send) for routing: send(item) receives target dict, completed run,
stable item id, attempt and ownership token. Decode run.snapshot for project/scope. Authorize
recipient/project/scope at creation AND send time; target JSON alone conveys no authorization.
Return only on confirmed transport acceptance. Raise RetryDelivery only when the transport
can certify no acceptance; ambiguous errors must remain unknown. Configure the same bounded
retry policy on every sender restart. No production adapter or permission model is added here.

Additive storage upgrade: nullable schedules.delivery_target plus deliveries table in the cron
DB. Existing rows remain untargeted; no historical outputs are retroactively enqueued. Initialize
upgrade before launching concurrent workers. Telegram DB untouched. Calendar dependencies are pinned in requirements-cron.txt; install only into this worktree .venv.

Pause/delete do not revoke already queued results; sender adapter must enforce current access.
No live channel checks performed. Calendar cron/misfire controls are implemented. Chat commands remain coordinator work.

Schema contract v3: nullable cron; misfire='coalesce' and grace_seconds=120 defaults preserve
old records; misfires table added. Calendar dependency croniter==6.2.4 plus pinned transitive
python-dateutil/six/tzdata. Coordinator consolidates packaging later. Chat-created time-sensitive
reminders should explicitly choose misfire='skip' with a user-appropriate grace; use coalesce
for useful late reports. Show timezone and next run when confirming schedule creation.
