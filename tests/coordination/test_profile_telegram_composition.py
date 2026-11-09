import io,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.coordination import test_cron_runtime as fixture
from senai.cli import main
from senai.defaults import save_defaults
from senai.memory import setup_profiles
from senai.telegram_composition import compose_router,parse_schedule

class CompositionTests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.CronRuntimeTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
 def test_root_profiles_and_advanced_sqlite_remain_distinct(self):
  root=self.f.root;setup_profiles(root)
  with patch.dict(os.environ,{"SENAI_CONFIG":str(root/"defaults.json"),"SENAI_INSTALLATION_ROOT":""}):
   save_defaults({"project":str(root),"installation":str(root)})
   for kind,file in (("memory","MEMORY.md"),("user","USER.md"),("soul","SOUL.md")):
    out,err=io.StringIO(),io.StringIO()
    self.assertEqual(main([kind,"add","human note"],stdout=out,stderr=err),0,err.getvalue())
    self.assertEqual(main([kind,"show"],stdout=out,stderr=err),0)
    self.assertIn("human note",out.getvalue())
    path=io.StringIO();self.assertEqual(main([kind,"path"],stdout=path,stderr=err),0)
    self.assertIn(file,path.getvalue())
   out=io.StringIO()
   self.assertEqual(main(["memory","--installation",str(root),"add","SQLite note","--provenance","human"],stdout=out,stderr=io.StringIO()),0)
   self.assertIn('"id"',out.getvalue())
 def compose(self,operators=()):
  return compose_router(self.f.router,self.f.manager,project=self.f.root,account="123",
                        operators=operators,timezone="Asia/Dhaka",clock=lambda:fixture.NOW)
 def send(self,router,text,user=7):
  return router.handle(self.f.message(text,user))
 def test_confirmed_new_archives_uuid_and_preserves_profiles_and_jobs(self):
  root=self.f.root;setup_profiles(root)
  (root/"outputs/.senai-memory/USER.md").write_text("Updated preference")
  sid="11111111-1111-4111-8111-111111111111"
  self.f.jobs.bind_shared_session(sid)
  router,gate=self.compose((7,))
  self.assertIn("Confirm",self.send(router,"/new")[0][1])
  self.assertIn("Fresh",self.send(router,"Confirm")[0][1])
  self.assertIsNone(self.f.jobs.shared_session())
  self.assertTrue(self.f.jobs.session_history())
  self.assertEqual((root/"outputs/.senai-memory/USER.md").read_text(),"Updated preference")
  self.assertEqual(self.f.jobs.recent(7),[])
 def test_pairing_does_not_grant_new_and_shared_gate_blocks_reset(self):
  self.f.jobs.bind_shared_session("11111111-1111-4111-8111-111111111111")
  router,gate=self.compose()
  self.assertIn("operator",self.send(router,"/new")[0][1])
  router,gate=self.compose((7,))
  self.send(router,"/new")
  self.f.create()
  self.f.manager.worker.tick()
  self.assertIn("busy",self.send(router,"Confirm")[0][1].lower())
  self.assertIsNotNone(self.f.jobs.shared_session())
 def test_conversation_uses_cron_parser_and_persists_one_schedule(self):
  router,gate=self.compose()
  for text in ("/cron create","friendly","Reply hello","tomorrow at 1 am","once"):
   response=self.send(router,text)
  self.assertIn("Confirm",response[0][1])
  self.assertEqual(self.f.manager.store.list(),[])
  self.assertIn("created",self.send(router,"Confirm")[0][1].lower())
  self.assertEqual(len(self.f.manager.store.list()),1)
 def test_claim_cannot_race_idle_gate(self):
  router,gate=self.compose((7,))
  with gate.idle() as idle:
   self.assertTrue(idle)
   import threading
   done=threading.Event()
   thread=threading.Thread(target=lambda:(self.f.manager.worker.store.claim(),done.set()))
   thread.start()
   self.assertFalse(done.wait(.05))
  thread.join(1);self.assertTrue(done.is_set())

 def test_new_real_child_loads_updated_profiles_without_reusing_old_snapshot(self):
  import json,sys
  from senai.memory_runtime import InstallationRuntime
  from senai.telegram.runner import CommandRunner
  root=self.f.root;setup_profiles(root)
  profile=root/"outputs/.senai-memory/USER.md";profile.write_text("Original preference")
  memory=InstallationRuntime(root)
  old="11111111-1111-4111-8111-111111111111"
  new="22222222-2222-4222-8222-222222222222"
  def seed(prompt,workspace,*,session_callback,**kwargs):
   session_callback(old);return "old"
  memory.execute("seed",root/"outputs",executor=seed)
  self.f.jobs.bind_shared_session(old)
  profile.write_text("Updated preference")
  router,gate=self.compose((7,))
  self.send(router,"/new");self.send(router,"Confirm")
  binary=root/"bin";binary.mkdir()
  fake=binary/"codex"
  fake.write_text("#!"+sys.executable+"\n"+"""
import json,sys
from pathlib import Path
args=sys.argv[1:]
Path("refresh-trace.json").write_text(json.dumps({"prompt":sys.stdin.read(),"args":args}))
Path(args[args.index("--output-last-message")+1]).write_text("fresh reply")
print(json.dumps({"type":"thread.started","thread_id":"22222222-2222-4222-8222-222222222222"}))
""")
  fake.chmod(0o700)
  runner=gate.wrap(CommandRunner(root,self.f.jobs.path.parent,store=self.f.jobs,
                    installation=root,skip_git_repo_check=True,chat_style=True))
  with patch.dict(os.environ,{"PATH":str(binary)+os.pathsep+os.environ["PATH"],
                             "SENAI_INSTALLATION_ROOT":"/must-not-retarget"}):
   self.assertEqual(runner({"id":1,"user_id":7,"chat_id":7,"prompt":"What is my preference?"})[0],"succeeded")
  trace=json.loads((root/"outputs/refresh-trace.json").read_text())
  self.assertIn("Updated preference",trace["prompt"])
  self.assertNotIn("resume",trace["args"])
  self.assertEqual(self.f.jobs.shared_session(),new)
  self.assertIn("Original preference",memory._load(old).context)
  self.assertNotIn("Updated preference",memory._load(old).context)
  self.assertIn("Updated preference",memory._load(new).context)
