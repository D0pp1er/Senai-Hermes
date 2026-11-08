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
upgrade before launching concurrent workers. Telegram DB untouched. No extra dependencies.

Pause/delete do not revoke already queued results; sender adapter must enforce current access.
No live channel checks performed. Calendar cron/misfire controls and chat commands remain next.
