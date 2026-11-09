import io
import tempfile
import unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
from senai.cron import Destination, Store
from senai.cron.__main__ import main

class TTY(io.StringIO):
    def isatty(self): return True

class WizardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.project=Path(self.tmp.name)
        self.path=self.project/'outputs/cron.db'
        self.now=datetime(2026,11,9,12,tzinfo=ZoneInfo('Asia/Dhaka'))
        self.output,self.errors=io.StringIO(),io.StringIO()
        self.destination=Destination('chat','My private chat','qa',{'recipient':'qa'},
            'Existing authorized worker executes and delivers here; worker must be running.')
        self.factories=[]
        def factory(project):
            self.factories.append(project)
            return Store(self.path,clock=lambda:self.now)
        self.factory=factory

    def run_cli(self,text,*,destinations=None,tty=True,extra=None):
        return main(['--project',str(self.project),'create']+(extra or []),
            stdin=(TTY(text) if tty else io.StringIO(text)),stdout=self.output,stderr=self.errors,
            clock=lambda:self.now,timezone='Asia/Dhaka',store_factory=self.factory,
            destinations=[self.destination] if destinations is None else destinations)

    def test_sequential_creation_preview_and_yes(self):
        code=self.run_cli('Build reminder\nCheck the build\ntomorrow at 1 am\ndaily\n1\nyes\n')
        self.assertEqual(code,0)
        rows=Store(self.path).list()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['cron'],'0 1 * * *')
        for text in ('Name','Task','First run','Repeat','Destination','2026-11-10','01:00','Asia/Dhaka','My private chat','Confirm'):
            self.assertIn(text,self.output.getvalue())
        self.assertEqual(Store(self.path).runs(),[])

    def test_cancel_eof_and_no_write_until_confirmation(self):
        for text in ('/cancel\n','Name\n','Name\nTask\nin 2 minutes\nonce\n1\nno\n'):
            with self.subTest(text=text):
                self.assertEqual(self.run_cli(text),0)
                self.assertFalse(self.path.exists())
                self.assertEqual(self.factories,[])

    def test_non_tty_and_missing_at_fail_without_reading(self):
        class NoRead(io.StringIO):
            def readline(self,*args): raise AssertionError('must not prompt')
        code=main(['--project',str(self.project),'create','--name','x','--prompt','task','--scope','qa','--every','60'],
            stdin=NoRead(),stdout=self.output,stderr=self.errors)
        self.assertEqual(code,2)
        self.assertIn('first run',self.errors.getvalue().lower())
        self.assertIn('--when',self.errors.getvalue())
        self.assertFalse(self.path.exists())

    def test_no_destination_hook_refuses_unsendable_schedule(self):
        self.assertEqual(self.run_cli('',destinations=[]),2)
        self.assertIn('destination',self.errors.getvalue().lower())
        self.assertEqual(self.factories,[])

    def test_invalid_time_recurrence_destination_and_confirmation_retry(self):
        self.assertEqual(self.run_cli('Name\nTask\ntoday at 1am\nin 2 minutes\nwrong\nonce\n99\n1\nmaybe\nyes\n'),0)
        self.assertIn('passed',self.output.getvalue())
        self.assertEqual(len(Store(self.path).list()),1)

    def test_relative_interval_still_asks_first_run(self):
        self.assertEqual(self.run_cli('Name\nTask\nin 2 minutes\n1\nyes\n',extra=['--every','3600']),0)
        row=Store(self.path).list()[0]
        self.assertEqual(row['every'],3600)
        self.assertEqual(row['next_due'],self.now.timestamp()+120)
        self.assertIn('First run',self.output.getvalue())

    def test_saved_timezone_used_when_not_injected(self):
        with patch('senai.defaults.load_defaults',return_value={'timezone':'UTC'}):
            code=main(['--project',str(self.project),'create'],stdin=TTY('Name\nTask\ntomorrow at 1 am\nonce\n1\nyes\n'),
                stdout=self.output,stderr=self.errors,clock=lambda:self.now,
                destinations=[self.destination],store_factory=self.factory)
        self.assertEqual(code,0)
        self.assertEqual(Store(self.path).list()[0]['timezone'],'UTC')

    def test_confirmation_rechecks_first_run_without_reinterpreting_relative_input(self):
        times=iter([self.now,self.now.replace(hour=13)])
        code=main(['--project',str(self.project),'create'],stdin=TTY('Name\nTask\nin 2 minutes\nonce\n1\nyes\n'),
            stdout=self.output,stderr=self.errors,clock=lambda:next(times),timezone='Asia/Dhaka',
            destinations=[self.destination],store_factory=self.factory)
        self.assertEqual(code,2)
        self.assertEqual(self.factories,[])

    def test_full_friendly_flags_preserve_advanced_noninteractive_path(self):
        code=self.run_cli('',tty=False,extra=['--name','flag-reminder','--prompt','Task',
            '--scope','qa','--when','in 2 minutes','--every','3600'])
        self.assertEqual(code,0)
        row=Store(self.path).list()[0]
        self.assertEqual(row['next_due'],self.now.timestamp()+120)
        self.assertEqual(row['every'],3600)

    def test_partial_custom_advanced_policy_is_not_silently_ignored(self):
        code=self.run_cli('',extra=['--misfire','coalesce'])
        self.assertEqual(code,2)
        self.assertFalse(self.path.exists())
