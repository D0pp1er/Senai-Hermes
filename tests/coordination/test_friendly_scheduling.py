import io,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from datetime import timedelta
from unittest.mock import patch
from tests.coordination import test_cron_runtime as fixture
from senai.cli import main
from senai.telegram.store import JobStore

class FriendlyTests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.CronRuntimeTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
 def send(self,text,user=7):
  return self.f.manager.handle(self.f.message(text,user=user))
 def draft(self):
  for text in ("/cron create","friendly","Reply hello","in 2 minutes","once"):
   reply=self.send(text)
  return reply
 def test_chat_preview_confirm_and_duplicate_only_save_once(self):
  self.assertIn("First run:",self.draft()[0][1])
  self.assertEqual(self.f.manager.store.list(),[])
  event=self.f.message("yes")
  self.assertIn("Saved",self.f.manager.handle(event)[0][1])
  self.assertEqual(self.f.manager.handle(event),[])
  schedule=self.f.manager.store.list()[0]
  self.assertEqual(schedule["scope"],"telegram-shared")
  self.assertEqual(json.loads(schedule["delivery_target"])["chat_id"],7)
  self.assertEqual(self.f.manager.store.runs(),[])
 def test_cancel_timeout_and_revocation_write_nothing(self):
  self.send("/cron create");self.assertIn("Cancelled",self.send("/cancel")[0][1])
  self.draft()
  self.f.manager.store.clock=lambda:fixture.NOW+timedelta(minutes=11)
  self.assertIn("expired",self.send("yes")[0][1])
  self.f.manager.store.clock=lambda:fixture.NOW
  self.draft();self.f.jobs.set_user_status(7,False)
  self.assertEqual(self.send("yes"),[])
  self.assertEqual(self.f.manager.store.list(),[])
 def test_time_errors_and_per_user_drafts(self):
  self.send("/cron create");self.send("a");self.send("task")
  self.assertIn("Try",self.send("gibberish")[0][1])
  self.send("/cron create",8)
  self.assertIn("Task",self.send("b",8)[0][1])
  self.assertIn("Repeat",self.send("tomorrow at 1 am")[0][1])
  self.assertEqual(self.f.manager.store.list(),[])
 def test_cli_authorized_destination_matches_account_store(self):
  class Terminal(io.StringIO):
   def isatty(self):return True
  root=self.f.root
  jobs=JobStore(root/"outputs/.senai-telegram/123/state.sqlite3")
  jobs.set_user_status(7,True)
  out,err=io.StringIO(),io.StringIO()
  code=main(["cron","--project",str(root),"--telegram-account","123","create"],
            stdin=Terminal("cli-test\nReply hello\nin 2 minutes\nonce\n1\nyes\n"),stdout=out,stderr=err)
  self.assertEqual(code,0,err.getvalue())
  schedule=self.f.manager.store.list()[0]
  self.assertEqual(json.loads(schedule["delivery_target"])["chat_id"],7)
  self.assertEqual(schedule["scope"],"telegram-shared")
  self.assertFalse((root/"outputs/.senai-cron/cron.db").exists())
 def test_cli_revocation_during_confirmation_cannot_save(self):
  from senai.cron_routing import authorized_store
  root=self.f.root
  jobs=JobStore(root/"outputs/.senai-telegram/123/state.sqlite3");jobs.set_user_status(7,True)
  store=authorized_store(root,"123")
  jobs.set_user_status(7,False)
  with self.assertRaises(PermissionError):
   store.create(name="blocked",prompt="never",project=root,scope="telegram-shared",
                at=fixture.NOW,delivery_target=self.f.manager.target(7))

 def test_explicit_advanced_local_create_is_not_rerouted(self):
  root=self.f.root
  jobs=JobStore(root/"outputs/.senai-telegram/123/state.sqlite3");jobs.set_user_status(7,True)
  out,err=io.StringIO(),io.StringIO()
  code=main(["cron","--project",str(root),"create","--name","legacy-local","--prompt","test",
             "--scope","local","--at",fixture.NOW.isoformat()],stdout=out,stderr=err)
  self.assertEqual(code,0,err.getvalue())
  self.assertTrue((root/"outputs/.senai-cron/cron.db").is_file())
  self.assertEqual(self.f.manager.store.list(),[])
 def test_authorization_changes_at_commit_drop_chat_draft(self):
  self.draft()
  with patch.object(self.f.manager,"authorize",side_effect=PermissionError("revoked")):
   self.assertIn("Nothing was saved",self.send("yes")[0][1])
  self.assertEqual(self.f.manager.store.list(),[])
 def test_saved_timezone_is_applied_to_preview(self):
  with patch("senai.defaults.load_defaults",return_value={"timezone":"UTC"}):
   self.f.manager=self.f.make_manager()
  self.assertIn("(UTC)",self.draft()[0][1])
