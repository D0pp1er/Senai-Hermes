import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from senai.defaults import load_defaults,save_defaults,apply_defaults

class DefaultTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.project=self.root/"project";self.project.mkdir()
  self.env={"SENAI_CONFIG":str(self.root/"config.json")}
 def test_saved_paths_work_independent_of_cwd(self):
  value={"project":str(self.project),"installation":str(self.project),"timezone":"Asia/Dhaka","skip_git_repo_check":True}
  save_defaults(value,environ=self.env)
  self.assertEqual(load_defaults(environ=self.env),value)
  self.assertEqual((self.root/"config.json").stat().st_mode&0o777,0o600)
 def test_explicit_project_does_not_inherit_saved_trust(self):
  value={"project":str(self.project),"installation":str(self.project),"skip_git_repo_check":True}
  args=apply_defaults(["--project",str(self.root),"hello"],value)
  self.assertNotIn("--skip-git-repo-check",args)
  self.assertIn("--skip-git-repo-check",apply_defaults(["hello"],value))
 def test_telegram_short_aliases_and_cron_project(self):
  value={"project":str(self.project)}
  self.assertIn("--enable-cron",apply_defaults(["telegram","start"],value))
  self.assertIn("--voice-configure",apply_defaults(["telegram","voice-configure"],value))
  self.assertEqual(apply_defaults(["cron","list"],value),["cron","--project",str(self.project),"list"])
 def test_unconfigured_legacy_arguments_unchanged(self):
  self.assertEqual(apply_defaults(["hello"],{}),["hello"])
 def test_corrupt_config_is_rejected_without_echo(self):
  (self.root/"config.json").write_text('{"secret":"do-not-print"}')
  with self.assertRaisesRegex(ValueError,"configuration"):
   load_defaults(environ=self.env)

 def test_onboarding_creates_profiles_and_preserves_existing_human_soul(self):
  from senai.onboarding import setup_main
  class Terminal(io.StringIO):
   def isatty(self):return True
  with patch.dict(os.environ,self.env):
   for _ in range(2):
    out,err=io.StringIO(),io.StringIO()
    code=setup_main(["--root",str(self.project)],out,err,Terminal("\n\nn\n"))
    self.assertEqual(code,0,err.getvalue())
    soul=self.project/"outputs/.senai-memory/SOUL.md"
    if not soul.read_text():soul.write_text("Human identity")
    self.assertEqual(soul.read_text(),"Human identity")
    self.assertIn(str(soul),out.getvalue())
