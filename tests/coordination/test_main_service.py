import io,unittest
from unittest.mock import Mock,patch
from senai.cli import main
from senai.telegram.service import BotService

class MainServiceTests(unittest.TestCase):
 def test_start_routes_to_existing_persistent_cron_enabled_service(self):
  with patch("senai.cli.run_codex",side_effect=RuntimeError("offline test: native execution prohibited")),patch("senai.defaults.load_defaults",return_value={}),patch("senai.telegram.cli.telegram_main",return_value=0) as start:
   self.assertEqual(main(["start"],stdout=io.StringIO(),stderr=io.StringIO()),0)
  self.assertIn("--enable-cron",start.call_args.args[0])
 def test_due_cron_has_priority_and_does_not_claim_foreground(self):
  jobs,router,runner,cron=Mock(),Mock(),Mock(),Mock(return_value={"id":"due"})
  service=BotService(Mock(),jobs,router,runner,scheduled_work=cron)
  self.assertTrue(service.run_one())
  jobs.claim_next.assert_not_called();runner.assert_not_called()
 def test_foreground_runs_when_no_cron_is_due(self):
  jobs,router,runner=Mock(),Mock(),Mock(return_value=("succeeded","done"))
  jobs.claim_next.return_value={"id":1,"user_id":7}
  service=BotService(Mock(),jobs,router,runner,scheduled_work=Mock(return_value=None))
  self.assertTrue(service.run_one())
  runner.assert_called_once()
  jobs.finish.assert_called_once_with(1,"succeeded","done")
