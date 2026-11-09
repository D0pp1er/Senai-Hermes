import io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from senai.cli import main
from senai.defaults import save_defaults
from senai.skills import Registry,Check

class SkillCompositionTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.project=self.root/"project";self.project.mkdir()
  self.package=self.root/"sample";self.package.mkdir()
  (self.package/"SKILL.md").write_text("---\nname: sample\ndescription: sample workflow\nversion: 1.0\n---\nPreserve leading zeros.")
  env=patch.dict(os.environ,{"SENAI_CONFIG":str(self.root/"defaults.json"),"SENAI_INSTALLATION_ROOT":""})
  env.start();self.addCleanup(env.stop)
  save_defaults({"project":str(self.project),"skip_git_repo_check":True})
 def command(self,*args,stdin=None):
  out,err=io.StringIO(),io.StringIO()
  code=main(list(args),stdout=out,stderr=err,stdin=stdin or io.StringIO())
  self.assertEqual(code,0,err.getvalue());return out.getvalue()
 def import_sample(self):self.command("skill","import",str(self.package))
 def test_simple_import_list_use_and_normal_context_preserve_native_skill(self):
  self.import_sample()
  self.assertIn("sample",self.command("skill","list"))
  self.command("skill","use","sample")
  with patch("senai.cli.run_codex",return_value="I verified everything") as run:
   self.command("--skill","native-one","Preserve identifiers")
  prompt=run.call_args.args[0]
  self.assertIn("$native-one",prompt);self.assertIn("Preserve leading zeros",prompt)
  registry=Registry(self.project/"outputs/skills")
  outcome=registry.outcomes("sample")[0]
  self.assertEqual(outcome.skill_digest,registry.select(["sample"])[0].digest)
  self.assertEqual(outcome.status,"unverified")
 def test_export_prompts_once_and_list_show_report_saved_path(self):
  class Terminal(io.StringIO):
   def isatty(self):return True
  self.import_sample();vault=self.root/"vault"
  self.command("skill","export","obsidian",stdin=Terminal(str(vault)+"\n"))
  self.assertTrue((vault/"Generated/Index.md").is_file())
  self.assertIn(str(vault),self.command("skill","list"))
  self.assertIn(str(vault),self.command("skill","show","sample"))
  self.command("skill","export","obsidian")
 def test_missing_vault_noninteractive_is_actionable(self):
  self.import_sample();out,err=io.StringIO(),io.StringIO()
  self.assertEqual(main(["skill","export","obsidian"],stdout=out,stderr=err,stdin=io.StringIO()),2)
  self.assertIn("vault",err.getvalue().lower())
 def test_registry_selection_does_not_change_resume_options(self):
  self.import_sample();self.command("skill","use","sample")
  with patch("senai.cli.run_codex",return_value="done") as run:
   self.command("--resume","11111111-1111-4111-8111-111111111111","continue")
  self.assertEqual(run.call_args.kwargs["options"].resume,"11111111-1111-4111-8111-111111111111")
 def test_trusted_checker_outcome_hook(self):
  from senai.skill_context import SkillContext
  self.import_sample();registry=Registry(self.project/"outputs/skills")
  context=SkillContext(self.project,["sample"],"check")
  response=context.wrap(lambda *a,**k:"done",checker=lambda *a:[Check("observed",True,"actual fixture check")])("prompt",self.project/"outputs")
  self.assertEqual(response,"done")
  self.assertEqual(registry.outcomes("sample")[0].status,"passed")
 def test_plain_workflow_import_is_explicit_and_local(self):
  class Terminal(io.StringIO):
   def isatty(self):return True
  self.command("skill","import","Always check identifiers for leading zeros",
               stdin=Terminal("identifiers\nPreserve identifier strings\nyes\n"))
  self.assertIn("identifiers",self.command("skill","list"))

 def test_checker_failure_never_records_verified_success(self):
  from senai.skill_context import SkillContext
  self.import_sample()
  def broken(*args):raise RuntimeError("untrusted checker failure")
  with self.assertRaisesRegex(RuntimeError,"no verified"):
   SkillContext(self.project,["sample"],"request").wrap(lambda *a,**k:"success",checker=broken)(
      "prompt",self.project/"outputs")
  self.assertEqual(Registry(self.project/"outputs/skills").outcomes("sample")[0].status,"unverified")
 def test_export_destination_override_is_explicit_and_saved(self):
  self.import_sample()
  vault=self.root/"chosen-vault"
  self.command("skill","export","obsidian","--destination",str(vault))
  self.assertTrue((vault/"Generated/Index.md").exists())
  self.assertIn(str(vault),self.command("skill","show","sample"))

 def test_telegram_child_loads_registry_and_preserves_native_uuid(self):
  import sys
  from senai.telegram.runner import CommandRunner
  from senai.telegram.store import JobStore
  self.import_sample();self.command("skill","use","sample")
  state=self.project/"outputs/test-bot"
  store=JobStore(state/"state.sqlite3")
  sid="11111111-1111-4111-8111-111111111111"
  store.bind_shared_session(sid);store.set_user_status(7,True)
  binary=self.root/"bin";binary.mkdir()
  fake=binary/"codex"
  fake.write_text("#!"+sys.executable+"\n"+"""
import json,sys
from pathlib import Path
args=sys.argv[1:]
Path("skill-telegram-trace.json").write_text(json.dumps({"prompt":sys.stdin.read(),"args":args}))
Path(args[args.index("--output-last-message")+1]).write_text("done")
print(json.dumps({"type":"thread.started","thread_id":"11111111-1111-4111-8111-111111111111"}))
""")
  fake.chmod(0o700)
  runner=CommandRunner(self.project,state,store=store,installation="",skip_git_repo_check=True,
                       chat_style=True,skills=("native-one",))
  with patch.dict(os.environ,{"PATH":str(binary)+os.pathsep+os.environ["PATH"]}):
   self.assertEqual(runner({"id":1,"user_id":7,"chat_id":7,"prompt":"Preserve identifiers"}),("succeeded","done"))
  trace=json.loads((self.project/"outputs/skill-telegram-trace.json").read_text())
  self.assertIn("$native-one",trace["prompt"])
  self.assertIn("Preserve leading zeros",trace["prompt"])
  self.assertEqual(trace["args"][-3:],["resume",sid,"-"])
  self.assertEqual(store.shared_session(),sid)
  self.assertTrue(store.user_status(7))
  self.assertEqual(Registry(self.project/"outputs/skills").outcomes("sample")[0].status,"unverified")
