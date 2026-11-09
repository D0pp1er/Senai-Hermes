"""Coordinator composition of human profiles, shared cron drafts and session policy."""
from .cron.draft import Destination,build_draft
from .telegram.conversation import create_conversation_router,bind_schedule_creator
from .telegram.session_policy import SessionGate

def parse_schedule(when,repeat,*,now,timezone):
 draft=build_draft(name="preview",prompt="preview",when=when,recurrence=repeat,
     destination=Destination("preview","preview","telegram-shared",{"preview":True},"preview only"),
     now=now,timezone=timezone)
 return dict(at=draft.at,timezone=draft.timezone,every=draft.every,cron=draft.cron)

class GatedClaims:
 def __init__(self,store,gate):self.store,self.gate=store,gate
 def __getattr__(self,name):return getattr(self.store,name)
 def claim(self):
  with self.gate.execution():return self.store.claim()

def compose_router(base,scheduler,*,project,account,operators=(),timezone="Asia/Dhaka",clock=None):
 def idle():
  if scheduler is None:return True
  return (not any(row["status"] in ("running","retry","unknown") for row in scheduler.store.runs())
          and not any(row["status"] in ("pending","delivering","unknown") for row in scheduler.store.deliveries()))
 gate=SessionGate(is_idle=idle)
 if scheduler is not None:
  scheduler.runner=gate.wrap(scheduler.runner)
  scheduler.worker.store=GatedClaims(scheduler.store,gate)
 creator=bind_schedule_creator(scheduler.store,project=project,authorize_target=scheduler.authorize) if scheduler else None
 router=create_conversation_router(base,project=project,account=account,
    parse_schedule=parse_schedule if scheduler else None,create_schedule=creator,
    advanced_handler=scheduler.handle if scheduler else None,timezone=timezone,clock=clock,
    new_session_users=operators,session_guard=gate.idle)
 return router,gate
