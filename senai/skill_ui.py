"""Basic project-local skill commands; advanced feature CLI remains available."""
import argparse,json,os,tempfile,uuid
from pathlib import Path
from .skills import Registry,export_vault
from .workspace import prepare_workspace

def settings(project):
 path=Path(project)/"outputs/.skill-settings.json"
 if path.is_symlink():raise ValueError("Unsafe skill settings.")
 if not path.exists():return {}
 with path.open() as stream:raw=stream.read(16385)
 if len(raw)>16384:raise ValueError("Skill settings exceed size limit.")
 data=json.loads(raw)
 if not isinstance(data,dict) or set(data)-{"selected","obsidian"}:raise ValueError("Invalid skill settings.")
 if not isinstance(data.get("selected",[]),list) or not all(isinstance(v,str) for v in data.get("selected",[])):
  raise ValueError("Invalid skill selection.")
 if "obsidian" in data and not isinstance(data["obsidian"],str):raise ValueError("Invalid vault path.")
 return data
def save(project,value):
 workspace=prepare_workspace(project);path=workspace/".skill-settings.json"
 if path.is_symlink():raise ValueError("Unsafe skill settings.")
 fd,tmp=tempfile.mkstemp(dir=workspace,prefix=".skills-")
 try:
  os.fchmod(fd,0o600)
  with os.fdopen(fd,"w") as stream:json.dump(value,stream)
  os.replace(tmp,path)
 finally:Path(tmp).unlink(missing_ok=True)
def selected_names(project):
 return tuple(settings(project).get("selected",()))
def main(argv,*,defaults,stdin,stdout,stderr):
 parser=argparse.ArgumentParser(prog="senai skill",add_help=False)
 parser.add_argument("--project",default=defaults.get("project","."))
 args,tail=parser.parse_known_args(argv)
 try:
  project=Path(args.project).expanduser().resolve()
  if not project.is_dir():raise ValueError("Project directory must exist; run senai setup.")
  state=settings(project)
  action=tail[0] if tail else "help"
  if action in ("help","--help","-h"):
   print("senai skill list | use NAME (or none) | import PATH_OR_WORKFLOW | show NAME | export obsidian\nAdvanced lifecycle: senai skills --help",file=stdout);return 0
  def ask(label):
   if not stdin.isatty():raise ValueError(label+" Run in a terminal or provide the required value.")
   print(label,file=stdout,flush=True)
   line=stdin.readline(16385)
   if not line:raise ValueError("Cancelled; no input.")
   return line.strip()
  root=project/"outputs/skills"
  if action=="list" and not root.exists():
   print("No saved skills. Use senai skill import PATH_OR_WORKFLOW.",file=stdout)
   if state.get("obsidian"):print("Obsidian: "+state["obsidian"],file=stdout)
   return 0
  if action not in ("import","list") and not root.is_dir():raise ValueError("Import a skill first.")
  registry=Registry(root)
  if action=="import":
   source=" ".join(tail[1:]) or ask("Local package folder, SKILL.md file, or workflow text?")
   path=Path(source).expanduser()
   if path.exists():
    if path.is_file():path=path.parent
    skill=registry.import_local(path)
   else:
    if source.startswith(("https://","http://","github:")):
     raise ValueError("For public GitHub imports use senai skills import-github owner/repo --commit FULL_SHA --path PACKAGE.")
    name=ask("Skill name (example csv-identifiers):")
    description=ask("Short description:")
    if ask("Import this user-authored workflow as an active local package? yes/no").lower() not in ("yes","y"):
     print("Cancelled.",file=stdout);return 0
    import re,yaml
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",name):raise ValueError("Use lowercase words separated by hyphens.")
    parent=prepare_workspace(project)/"skill-authored"
    if parent.is_symlink():raise ValueError("Unsafe workflow directory.")
    package=parent/uuid.uuid4().hex;package.mkdir(parents=True)
    (package/"SKILL.md").write_text("---\n"+yaml.safe_dump(dict(name=name,description=description,version="1.0"),sort_keys=False)+"---\n"+source+"\n")
    skill=registry.import_local(package)
   print("Imported "+skill.name+" ("+skill.digest+"). Review instructions before use.",file=stdout)
  elif action=="list":
   for skill in registry.list():
    print(skill.name+" | "+skill.version+" | "+registry.origin(skill.name).kind+
          (" | selected" if skill.name in state.get("selected",[]) else ""),file=stdout)
   print("Registry: "+str(root),file=stdout)
  elif action=="use":
   name=tail[1] if len(tail)>1 else ask("Which saved skill? (or none)")
   if name=="none":state["selected"]=[]
   else:registry.select([name]);state["selected"]=[name]
   save(project,state)
   print("Selected: "+name+". Applies to subsequent requests in this project; native --skill remains separate.",file=stdout)
  elif action=="show":
   name=tail[1] if len(tail)>1 else ask("Skill name?")
   skill=registry.select([name])[0]
   print(skill.instructions+"\nPackage: "+str(skill.path),file=stdout)
  elif action=="export" and tail[1:2]==["obsidian"]:
   export_parser=argparse.ArgumentParser(prog="senai skill export obsidian")
   export_parser.add_argument("--destination")
   export_args=export_parser.parse_args(tail[2:])
   destination=export_args.destination or state.get("obsidian") or ask("Obsidian vault folder (example /home/me/SkillsVault or C:/Users/me/SkillsVault):")
   if not destination:raise ValueError("Enter an Obsidian vault folder.")
   # Persist only after successful export; native exporter validates ownership and paths.
   result=export_vault(registry,project=project,destination=destination)
   state["obsidian"]=destination;save(project,state)
   print("Obsidian: "+result.vault_path+"\nIndex: "+result.index_path,file=stdout)
  else:
   from .skills.cli import main as advanced
   return advanced(["--project",str(project),*tail],stdout=stdout,stderr=stderr)
  if state.get("obsidian"):print("Configured Obsidian vault: "+state["obsidian"],file=stdout)
  return 0
 except (ValueError,OSError) as error:
  print("skill: "+str(error),file=stderr);return 2
