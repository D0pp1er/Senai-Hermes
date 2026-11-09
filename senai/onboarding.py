"""One-time local setup; secrets remain owned by the existing Telegram wizard."""
import argparse
from pathlib import Path
from .defaults import save_defaults,config_path

def setup_main(argv,stdout,stderr,stdin):
 parser=argparse.ArgumentParser(prog="senai setup")
 parser.add_argument("--root",type=Path,default=Path.cwd())
 args=parser.parse_args(argv)
 if not stdin.isatty():
  print("Run senai setup in an interactive terminal.",file=stderr);return 2
 def ask(text,default):
  print(text+" ["+default+"]: ",file=stdout,end="",flush=True)
  answer=stdin.readline()
  if not answer:raise ValueError("Setup cancelled: no input.")
  return answer.strip() or default
 try:
  root=args.root.expanduser().resolve()
  if not root.is_dir():raise ValueError("Setup root must exist.")
  project=Path(ask("Default project folder",str(root))).expanduser().resolve()
  if not project.is_dir():raise ValueError("Project folder must exist.")
  zone=ask("Timezone (example Asia/Dhaka)","Asia/Dhaka")
  values={"project":str(project),"installation":str(root),"timezone":zone,"skip_git_repo_check":True}
  path=save_defaults(values)
  from .memory import InstallationMemory
  memory=InstallationMemory(root)
  for name in ("SOUL.md","USER.md","MEMORY.md"):
   document=memory.profiles.read(name)
   if not document.path.exists():
    with document.path.open("x") as stream:stream.write("")
    document.path.chmod(0o600)
   print(name+": "+str(document.path),file=stdout)
  print("Saved local defaults: "+str(path),file=stdout)
  print("This project is trusted for non-Git requests. Existing profile contents were preserved.",file=stdout)
  if ask("Configure Telegram now? Y/n","Y").lower() in ("y","yes"):
   from .telegram.cli import telegram_main
   code=telegram_main(["--project",str(project),"--configure"],stdout,stderr)
   if code:return code
  print("Ready. Run senai telegram start or a quoted coding request.",file=stdout)
  return 0
 except (ValueError,OSError) as error:
  print("Setup: "+str(error),file=stderr);return 2
