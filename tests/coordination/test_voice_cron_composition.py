"""Coordinator merge regression: optional voice setup must preserve cron supervision."""

import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from senai.cli import main
from senai.telegram.voice_config import VoiceConfigError


class VoiceCronCompositionTests(unittest.TestCase):
    def test_optional_voice_and_bounded_independent_cron_hooks_survive_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            for configured in (True, False):
                with self.subTest(configured=configured):
                    speech = Mock()
                    out, err = io.StringIO(), io.StringIO()
                    with patch.dict(os.environ, {
                            "XDG_CONFIG_HOME": str(root / "config"),
                            "OPENAI_API_KEY": "native-auth-fixture", "SENAI_INSTALLATION_ROOT": str(root)}, clear=True), \
                         patch("senai.telegram.cli.load_credentials", return_value=("123:synthetic", frozenset({7}))), \
                         patch("senai.telegram.cli.BotAPI"), \
                         patch("senai.telegram.cli.identify_bot", return_value={"id":123,"username":"test_bot"}), \
                         patch("senai.telegram.cli.speech_from_configuration",
                               side_effect=None if configured else VoiceConfigError("invalid local config"),
                               return_value=speech) as load, \
                         patch("senai.telegram.cli.CommandRunner") as runner, \
                         patch("senai.telegram.cli.BotService") as service:
                        service.return_value.run_forever.return_value = 0
                        result = main(["telegram","--project",str(project),"--enable-cron",
                                       "--cron-execution-timeout","77"], stdout=out, stderr=err)
                        self.assertEqual(result,0,err.getvalue())
                        self.assertEqual(os.environ["OPENAI_API_KEY"],"native-auth-fixture")
                    load.assert_called_once_with(str(project))
                    self.assertEqual(runner.call_args_list[0].kwargs["execution_timeout"],77)
                    self.assertEqual(runner.call_args_list[0].kwargs["installation"],str(root))
                    self.assertEqual(runner.call_args_list[1].kwargs["installation"],str(root))
                    self.assertEqual(service.call_args.args[3].gate,
                                     service.call_args.args[2].router.session_guard.__self__)
                    self.assertIs(runner.call_args_list[1].kwargs["speech"],speech if configured else None)
                    args,kwargs = service.call_args
                    conversation = args[2].router
                    scheduler = conversation.advanced_handler.__self__
                    self.assertEqual(conversation.base.voice_enabled,configured)
                    self.assertEqual(kwargs["scheduled_work"],scheduler.worker.tick)
                    self.assertEqual(kwargs["idle_delivery"],scheduler.sender.tick)
                    self.assertIs(runner.call_args_list[0].kwargs["store"],
                                  runner.call_args_list[1].kwargs["store"])
