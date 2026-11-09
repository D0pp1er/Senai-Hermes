"""Explicitly saved, non-secret single-project defaults; no writes on import."""
import json,os,tempfile
from pathlib import Path

FIELDS={"project","installation","timezone","skip_git_repo_check"}
def config_path(environ=None):
 env=os.environ if environ is None else environ
 return Path(env.get("SENAI_CONFIG",str(Path(env.get("XDG_CONFIG_HOME",str(Path.home()/".config")))/"senai/defaults.json"))).expanduser().absolute()
def validate(value):
 if not isinstance(value,dict) or set(value)-FIELDS:raise ValueError("Invalid Senai configuration; rerun senai setup.")
 for key in ("project","installation"):
  if key in value and (not isinstance(value[key],str) or not Path(value[key]).is_absolute() or not Path(value[key]).is_dir()):
   raise ValueError("Saved configuration directory is missing; rerun senai setup.")
 if "skip_git_repo_check" in value and type(value["skip_git_repo_check"]) is not bool:raise ValueError("Invalid Senai configuration.")
 if "timezone" in value:
  from zoneinfo import ZoneInfo
  try:ZoneInfo(value["timezone"])
  except Exception:raise ValueError("Invalid configuration timezone.") from None
 return value
def load_defaults(*,environ=None):
 path=config_path(environ)
 if path.is_symlink():raise ValueError("Unsafe Senai configuration path.")
 try:
  with path.open() as stream:raw=stream.read(16385)
 except FileNotFoundError:return {}
 try:
  if len(raw)>16384:raise ValueError()
  return validate(json.loads(raw))
 except (ValueError,TypeError):raise ValueError("Invalid Senai configuration; rerun senai setup.") from None
def save_defaults(value,*,environ=None):
 value=validate(dict(value));path=config_path(environ)
 for parent in (path,*path.parents):
  if parent.is_symlink():raise ValueError("Unsafe Senai configuration path.")
 path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 descriptor,temporary=tempfile.mkstemp(prefix=".defaults-",dir=path.parent)
 try:
  os.fchmod(descriptor,0o600)
  with os.fdopen(descriptor,"w") as stream:
   json.dump(value,stream,indent=2);stream.write("\n");stream.flush();os.fsync(stream.fileno())
  os.replace(temporary,path)
 finally:Path(temporary).unlink(missing_ok=True)
 return path
def apply_defaults(argv,value):
 args=list(argv)
 if not args:return args
 first=args[0]
 if first=="telegram" and len(args)>1:
  aliases={"start":None,"configure":"--configure","voice-configure":"--voice-configure",
           "voice-check":"--voice-check","voice-remove":"--voice-remove"}
  if args[1] in aliases:
   action=args.pop(1)
   if aliases[action]:args.insert(1,aliases[action])
   if action=="start" and "--enable-cron" not in args:args.insert(1,"--enable-cron")
 groups={"cron","telegram","chat","review","codex","skill","skills"}
 special=first in groups
 prefix=args[:1] if special else []
 tail=args[1:] if special else args
 # Never interpret request text/native pass-through after -- as wrapper settings.
 boundary=tail.index("--") if "--" in tail else len(tail)
 options=tail[:boundary]
 has_project=any(v in ("--project","--cd","-C") or v.startswith(("--project=","--cd=")) for v in options)
 if first in ("memory","user","soul","setup"):return args
 extra=[]
 if value.get("project") and not has_project:extra+=["--project",value["project"]]
 if (not special or first == "chat") and value.get("installation") and not os.environ.get("SENAI_INSTALLATION_ROOT") and not any(v=="--installation" or v.startswith("--installation=") for v in options):
  extra+=["--installation",value["installation"]]
 if (first in ("telegram", "chat") or not special) and value.get("skip_git_repo_check") and not has_project and "--skip-git-repo-check" not in options:
  extra+=["--skip-git-repo-check"]
 return prefix+extra+tail
