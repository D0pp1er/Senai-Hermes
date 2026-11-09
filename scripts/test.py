"""Run offline tests with isolated saved defaults and the checkout's installed command."""
import os,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
python=root/".venv/bin/python"
if not python.is_file():raise SystemExit("Create this checkout's .venv and install -e . first.")
out=root/"outputs";out.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix="offline-config-",dir=out) as directory:
 env=dict(os.environ,SENAI_CONFIG=str(Path(directory)/"defaults.json"),
          PATH=str(python.parent)+os.pathsep+os.environ.get("PATH",""))
 env.pop("SENAI_INSTALLATION_ROOT",None)
 args=sys.argv[1:] or ["discover","-s","tests","-v"]
 raise SystemExit(subprocess.call([str(python),"-m","unittest",*args],cwd=root,env=env))
