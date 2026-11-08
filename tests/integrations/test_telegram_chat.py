import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from senai.telegram.chat import ACKNOWLEDGEMENTS, acknowledgement, chat_request
from senai.telegram.router import Router, result_text
from senai.telegram.runner import CommandRunner
from senai.telegram.service import BotService
from senai.telegram.store import JobStore


def update(identifier=1, text="Hello", user=7):
    return {"update_id": identifier, "message": {"from": {"id": user},
            "chat": {"id": user, "type": "private"}, "text": text}}


class TelegramChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = JobStore(self.root / "outputs/state/state.sqlite3")
        self.choose = Mock(return_value="Got it, I’m on it.")
        self.router = Router(self.store, {7}, "test_bot", acknowledge=self.choose)

    def test_approved_options_are_selected_randomly(self):
        expected = ("Got it, I’m on it.", "Let me check that.", "Okay, give me a moment.",
                    "I’ll take a look.", "Working on it.")
        self.assertEqual(ACKNOWLEDGEMENTS, expected)
        with patch("senai.telegram.chat.random.choice", side_effect=lambda options: options[-1]) as choose:
            self.assertEqual(acknowledgement(), expected[-1])
            choose.assert_called_once_with(expected)

    def test_acknowledgement_is_sent_before_final_result(self):
        api = Mock()
        api.redact.side_effect = lambda text: text
        api.get_updates.return_value = [update()]
        service = BotService(api, self.store, self.router, Mock(return_value=("succeeded", "Hello!")))
        service.poll_once()
        self.assertEqual(api.send_message.call_args.args, (7, "Got it, I’m on it."))
        service.run_one()
        service.deliver_results()
        self.assertEqual([call.args[1] for call in api.send_message.call_args_list],
                         ["Got it, I’m on it.", "Hello!"])

    def test_duplicate_unauthorized_commands_and_busy_do_not_get_fake_ack(self):
        self.router.max_pending = 1
        self.router.handle(update())
        self.assertEqual(self.router.handle(update()), [])
        self.assertEqual(self.router.handle(update(2, user=9)), [])
        self.assertIn("busy", self.router.handle(update(3))[0][1])
        self.router.handle(update(4, "/status"))
        self.choose.assert_called_once_with()

    def test_success_is_conversational_and_failure_remains_visible(self):
        self.assertEqual(result_text({"id": 1, "status": "succeeded", "result": "Done."}), "Done.")
        self.assertIn("failed", result_text({"id": 1, "status": "failed", "result": "Could not run."}))

    def test_each_turn_requests_short_plain_text_without_altering_saved_request(self):
        sid = "11111111-1111-4111-8111-111111111111"
        commands = []
        def execute(command, **kwargs):
            commands.append(command)
            kwargs["stdout"].write(json.dumps({"type": "thread.started", "thread_id": sid}))
            Path(command[command.index("--output-last-message") + 1]).write_text("Hello!")
            return subprocess.CompletedProcess(command, 0)
        with patch("senai.telegram.runner.subprocess.run", side_effect=execute):
            runner = CommandRunner(self.root, self.store.path.parent, store=self.store, chat_style=True)
            for identifier in (1, 2):
                self.router.handle(update(identifier, "Explain x*y and `code`"))
                job = self.store.claim_next()
                self.assertEqual(job["prompt"], "Explain x*y and `code`")
                self.assertEqual(runner(job), ("succeeded", "Hello!"))
                self.store.finish(identifier, "succeeded", "Hello!")
        for command in commands:
            prompt = command[-1]
            self.assertIn("plain text", prompt)
            self.assertIn("1-3 short sentences", prompt)
            self.assertIn("Markdown", prompt)
            self.assertTrue(prompt.endswith("Explain x*y and `code`"))
        self.assertEqual(commands[1][commands[1].index("--resume") + 1], sid)


class TelegramViewerContextTests(unittest.TestCase):
    def test_every_turn_describes_the_remote_telegram_viewer_and_actual_delivery(self):
        prompt = chat_request("Show me the result")
        self.assertIn("reading your reply in Telegram", prompt)
        self.assertIn("cannot open files on the bot's computer or server", prompt)
        self.assertIn("Do not present local filesystem paths", prompt)
        self.assertIn("paste the useful content", prompt)
        self.assertIn("Do not claim an image, file or voice note was sent", prompt)
        self.assertIn("text-only", prompt)
        self.assertTrue(prompt.endswith("Show me the result"))

    def test_telegram_fallbacks_do_not_advertise_inaccessible_log_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = JobStore(root / "outputs/state/state.sqlite3")
            store.bind_shared_session("11111111-1111-4111-8111-111111111111")
            runner = CommandRunner(root, store.path.parent, store=store, chat_style=True)
            def execute(command, **kwargs):
                Path(command[command.index("--output-last-message") + 1]).write_text("x" * 60001)
                return subprocess.CompletedProcess(command, 0)
            with patch("senai.telegram.runner.subprocess.run", side_effect=execute):
                status, text = runner({"id": 1, "prompt": "Long answer"})
            self.assertEqual(status, "succeeded")
            self.assertNotIn(str(root), text)
            self.assertIn("shortened", text)
            self.assertTrue((store.path.parent / "jobs/1/response.txt").exists())
