"""Local operator destination discovery; metadata never substitutes for authorization."""
import json,sqlite3
from pathlib import Path
from .cron.draft import Destination

def users(project,account):
 path=Path(project)/"outputs/.senai-telegram"/account/"state.sqlite3"
 for parent in (path,*path.parents):
  if parent==Path(project):break
  if parent.is_symlink():raise ValueError("Unsafe Telegram authorization path.")
 if not path.is_file():return ()
 with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True) as db:
  paired=dict(db.execute("SELECT user_id,active FROM paired_users"))
 from .telegram.config import load_credentials,default_env_file
 legacy=()
 config=default_env_file(project)
 try:
  token,allowed=load_credentials(env_file=config if config.is_file() else None,require_users=False)
  if token.partition(":")[0]==account:legacy=allowed
 except ValueError:pass
 return tuple(sorted({user for user,active in paired.items() if active} |
                     {user for user in legacy if paired.get(user,True)}))
def target(project,account,user):
 return dict(platform="telegram",account=account,project=str(Path(project).resolve()),
             scope="telegram-shared",user_id=user,chat_id=user)
def destinations(project,account):
 return tuple(Destination(str(user),"Telegram private chat "+str(user),"telegram-shared",
            target(project,account,user),
            "Run senai telegram start for this project, or its standalone account worker; not both.")
            for user in users(project,account))
def accounts(project):
 parent=Path(project)/"outputs/.senai-telegram"
 if parent.is_symlink():raise ValueError("Unsafe Telegram account directory.")
 if not parent.is_dir():return ()
 return tuple(p.name for p in sorted(parent.iterdir()) if p.name.isascii() and p.name.isdecimal()
              and users(project,p.name))
class AuthorizedStore:
 def __init__(self,store,project,account):
  self.store,self.project,self.account=store,Path(project).resolve(),account
 def __getattr__(self,name):return getattr(self.store,name)
 def create(self,**values):
  destination=values.get("delivery_target")
  user=destination.get("user_id") if isinstance(destination,dict) else None
  if (type(user) is not int or user not in users(self.project,self.account)
      or destination!=target(self.project,self.account,user)
      or values.get("scope")!="telegram-shared"
      or Path(values["project"]).resolve()!=self.project):
   raise PermissionError("Destination is no longer authorized. Pair a private user and retry.")
  return self.store.create(**values)
def authorized_store(project,account):
 from .cron_runtime import telegram_store
 return AuthorizedStore(telegram_store(project,account),project,account)
