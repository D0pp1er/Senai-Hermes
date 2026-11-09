import tempfile
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from senai.cron import Store, Destination, build_draft, preview_draft, commit_draft

class DraftTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,9,12,tzinfo=ZoneInfo('Asia/Dhaka'))
        self.destination=Destination('chat','My private chat','qa',{'recipient':'qa'},
                                     'Existing authorized worker runs and delivers this task.')
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'cron.db',clock=lambda:self.now)

    def draft(self,**changes):
        args=dict(name='Reminder',prompt='Check build',when='tomorrow at 1 am',recurrence='once',
            destination=self.destination,now=self.now,timezone='Asia/Dhaka')
        args.update(changes)
        return build_draft(**args)

    def test_preview_then_explicit_confirmation(self):
        draft=self.draft()
        preview=preview_draft(draft)
        for expected in ('2026-11-10','01:00','Asia/Dhaka','My private chat','once'):
            self.assertIn(expected,preview)
        self.assertEqual(self.store.list(),[])
        self.assertIsNone(commit_draft(self.store,draft,project=self.tmp.name,now=self.now,confirmed=False))
        ident=commit_draft(self.store,draft,project=self.tmp.name,now=self.now,confirmed=True)
        self.assertEqual(self.store.get(ident)['misfire'],'skip')
        self.assertEqual(len(self.store.list()),1)

    def test_daily_and_weekly_use_local_wall_time(self):
        for recurrence in ('daily','weekly'):
            with self.subTest(recurrence=recurrence):
                draft=self.draft(recurrence=recurrence)
                self.assertTrue(draft.cron.startswith('0 1 '))
        self.assertEqual(self.draft(recurrence='every 2 hours').every,7200)

    def test_stale_confirmation_is_not_saved(self):
        draft=self.draft(when='in 2 minutes')
        with self.assertRaises(ValueError):
            commit_draft(self.store,draft,project=self.tmp.name,now=self.now+timedelta(minutes=3),confirmed=True)
        self.assertEqual(self.store.list(),[])

    def test_injected_parser_and_invalid_recurrence(self):
        called=[]
        def parser(text,**kwargs):
            called.append(text); return self.now+timedelta(hours=2)
        self.draft(parser=parser)
        self.assertEqual(called,['tomorrow at 1 am'])
        for recurrence in ('sometimes','every 0 minutes','cron bad'):
            with self.subTest(recurrence=recurrence),self.assertRaises(ValueError):
                self.draft(recurrence=recurrence)

    def test_no_missing_route_or_empty_input(self):
        for changes in ({'name':''},{'prompt':''},{'destination':None}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.draft(**changes)

    def test_destination_snapshot_cannot_be_changed_after_preview(self):
        original={'recipient':'qa'}
        destination=Destination('chat','My private chat','qa',original,'Existing worker')
        draft=self.draft(destination=destination)
        original['recipient']='other'
        ident=commit_draft(self.store,draft,project=self.tmp.name,now=self.now,confirmed=True)
        self.assertIn('qa',self.store.get(ident)['delivery_target'])
        self.assertNotIn('other',self.store.get(ident)['delivery_target'])

    def test_injected_parser_must_return_an_aware_datetime(self):
        with self.assertRaises(ValueError):
            self.draft(parser=lambda *args,**kwargs:datetime(2026,11,10,1))
