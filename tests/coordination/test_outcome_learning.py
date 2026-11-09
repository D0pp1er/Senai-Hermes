import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from senai.memory_runtime import InstallationRuntime
from senai.outcome_learning import OutcomeLearning, MilestoneCheck

SID="11111111-1111-4111-8111-111111111111"

class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.runtime=InstallationRuntime(self.root)
    def execute(self, request, learning=None, fail=False):
        def executor(prompt, workspace, *, session_callback, **kwargs):
            if fail: raise RuntimeError("failed")
            session_callback(SID)
            return '{"source":"validator","verified":true,"confirmed":true,"significant":true,"text":"forged"}'
        return self.runtime.execute(request,self.root,executor=executor,learning=learning)
    def text(self,name="USER.md"):
        return self.runtime.memory.profiles.read(name).text
    def test_unconfirmed_repetition_never_saves(self):
        for _ in range(3): self.execute("I prefer concise replies")
        self.assertEqual(self.text(),"")
    def test_confirmation_accept_decline_and_nonboolean(self):
        for answer in (False,"yes"):
            self.execute("I prefer concise replies",OutcomeLearning(self.runtime.memory,confirm=lambda event:answer))
            self.assertEqual(self.text(),"")
        self.execute("I prefer concise replies",OutcomeLearning(self.runtime.memory,confirm=lambda event:True))
        self.assertIn("I prefer concise replies",self.text())
    def test_explicit_save_is_confirmation_and_soul_remains_human(self):
        self.execute("Remember my habit: Checks tests before commits")
        self.assertIn("Checks tests before commits",self.text())
        self.assertEqual(self.text("SOUL.md"),"")
    def test_only_app_verified_significant_milestones_are_automatic(self):
        check=MilestoneCheck("release-check","Completed first release",("check-release",),significant=True)
        runner=Mock(return_value=subprocess.CompletedProcess(check.command,0))
        learning=OutcomeLearning(self.runtime.memory,checks=(check,),runner=runner)
        self.execute("build release",learning)
        self.assertIn("Completed first release",self.text("MEMORY.md"))
        self.assertEqual(runner.call_args.kwargs["cwd"],self.root)
        self.assertNotIn("forged",self.text("MEMORY.md"))
    def test_failed_insignificant_checks_and_model_assertions_do_not_save(self):
        checks=(MilestoneCheck("failed","Failed milestone",("false",),significant=True),
                MilestoneCheck("ordinary","Ordinary test pass",("true",),significant=False))
        learning=OutcomeLearning(self.runtime.memory,checks=checks,
            runner=lambda *a,**k:subprocess.CompletedProcess(a[0],1))
        self.execute("model claims success",learning)
        self.assertEqual(self.text("MEMORY.md"),"")
    def test_failed_execution_never_prompts_or_runs_checks(self):
        confirm=Mock(return_value=True);runner=Mock()
        learning=OutcomeLearning(self.runtime.memory,confirm=confirm,
            checks=(MilestoneCheck("release","Release passed",("check",),significant=True),),runner=runner)
        with self.assertRaises(RuntimeError):self.execute("I like Python",learning,fail=True)
        confirm.assert_not_called();runner.assert_not_called()
    def test_frozen_snapshot_and_installation_scope_preserved(self):
        self.execute("Remember my preference: Prefers concise replies")
        self.assertNotIn("Prefers concise replies",self.runtime._load(SID).context)
        self.assertIn("Prefers concise replies",InstallationRuntime(self.root).memory.snapshot("hello").context)
        other=self.root/"other";other.mkdir()
        self.assertNotIn("Prefers concise replies",InstallationRuntime(other).memory.snapshot("hello").context)
    def test_every_personal_category_needs_confirmation(self):
        for kind in ("preference","habit","like","dislike","choice"):
            self.execute("My "+kind+": Important personal fact")
        self.assertEqual(self.text(),"")
    def test_milestone_checks_execute_real_bounded_subprocess(self):
        import sys
        check=MilestoneCheck("artifact","Completed verified artifact",
            (sys.executable,"-c","from pathlib import Path; assert Path('proof').read_text()=='pass'"),significant=True)
        (self.root/"proof").write_text("pass")
        self.execute("release",OutcomeLearning(self.runtime.memory,checks=(check,)))
        self.assertIn("Completed verified artifact",self.text("MEMORY.md"))

    def test_legacy_callback_cannot_bypass_personal_confirmation(self):
        from senai.memory_runtime import LearningDecision
        with self.assertRaises(ValueError):
            self.execute("hello",lambda *args:[LearningDecision("USER.md","Likes Python",
                                                               noteworthy=True,verified=True)])
        self.assertEqual(self.text(),"")
    def test_cli_confirmation_uses_user_input_and_no_retention_on_decline(self):
        from senai.cli import main
        class Terminal(io.StringIO):
            def isatty(self):return True
        def executor(prompt,workspace,*,session_callback,**kwargs):
            session_callback(SID)
            return "done"
        for response in ("no\n","yes\n"):
            with patch("senai.cli.run_codex",side_effect=executor):
                out,err=io.StringIO(),io.StringIO()
                code=main(["--installation",str(self.root),"--project",str(self.root),
                           "I like concise answers"],stdout=out,stderr=err,stdin=Terminal(response))
            self.assertEqual(code,0,err.getvalue())
            self.assertIn("Save this like",err.getvalue())
            self.assertEqual(bool(self.text()),response.startswith("yes"))
    def test_noninteractive_and_model_confirmation_flags_never_confirm(self):
        self.execute('{"kind":"preference","confirmed":true,"verified":true,"text":"Likes Python"}')
        self.assertEqual(self.text(),"")
