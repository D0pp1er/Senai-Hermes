"""Per-user ephemeral chat drafts over the shared cron draft contract."""
import sqlite3
from datetime import timedelta
from .cron.draft import build_draft,preview_draft,commit_draft,Destination
from .cron.when import parse_when,EXAMPLES

class CronConversation:
 def __init__(self,manager,*,timezone="Asia/Dhaka",timeout=600):
  self.manager,self.timezone,self.timeout=manager,timezone,timeout
  self.drafts={}
 def wants(self,user,text):
  return user in self.drafts or text.split("@",1)[0].strip() in ("/cron create","/cancel") or text.strip().startswith("/cron@") and text.strip().endswith(" create")
 def cancel(self,user):self.drafts.pop(user,None)
 def destination(self,user):
  return Destination(str(user),"this private Telegram chat",self.manager.scope,self.manager.target(user),
                     "The running bot executes this schedule and sends its result here.")
 def reply(self,user,text):
  now=self.manager.store.clock();text=text.strip()
  if text.lower()=="/cancel":
   self.cancel(user);return "Cancelled. Nothing was saved."
  start=text in ("/cron create",) or text.startswith("/cron@") and text.endswith(" create")
  if start:
   self.drafts[user]={"stage":"name","expires":now+timedelta(seconds=self.timeout)}
   return "Create a schedule. /cancel stops without saving. Name?"
  state=self.drafts.get(user)
  if state is None:return "Send /cron create to start."
  if now>=state["expires"]:
   self.cancel(user);return "Schedule draft expired. Send /cron create to start again."
  if text.startswith("/"):return "Finish these questions or /cancel. Nothing saved yet."
  if len(text)>8000:return "Answer is too long. Try a shorter value or /cancel."
  try:
   stage=state["stage"]
   if stage=="name":
    if not text:raise ValueError("Enter a schedule name.")
    state["name"]=text;state["stage"]="prompt";return "Task? Example: summarize today's project changes."
   if stage=="prompt":
    if not text:raise ValueError("Enter the task to execute.")
    state["prompt"]=text;state["stage"]="when";return "First run? Examples: "+EXAMPLES
   if stage=="when":
    state["at"]=parse_when(text,now=now,timezone=self.timezone)
    state["stage"]="repeat";return "Repeat? once, daily, weekly, or every 2 hours. Enter once for a reminder."
   if stage=="repeat":
    state["draft"]=build_draft(name=state["name"],prompt=state["prompt"],
      when=state["at"].isoformat(),recurrence=text or "once",destination=self.destination(user),
      now=now,timezone=self.timezone)
    state["stage"]="confirm"
    return preview_draft(state["draft"])+"\nConfirm and save? yes/no or /cancel."
   if text.lower() in ("no","n"):
    self.cancel(user);return "Cancelled. Nothing was saved."
   if text.lower() not in ("yes","y"):return "Enter yes to save, no or /cancel to discard."
   self.manager.authorize(state["draft"].destination.target)
   identifier=commit_draft(self.manager.store,state["draft"],project=self.manager.project,
                            now=now,confirmed=True)
   self.cancel(user);return "Saved schedule "+identifier+". Its result will arrive in this chat."
  except PermissionError:
   self.cancel(user);return "Authorization changed. Nothing was saved."
  except (ValueError,sqlite3.Error) as error:
   if isinstance(error,sqlite3.IntegrityError):return "That name is already used. /cancel and choose a different name."
   return str(error)+" Try again or /cancel."
