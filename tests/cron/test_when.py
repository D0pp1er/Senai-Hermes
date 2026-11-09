import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from senai.cron import parse_when, TimeClarification

class WhenTests(unittest.TestCase):
    now = datetime(2026,11,9,12,0,tzinfo=ZoneInfo('Asia/Dhaka'))
    def parse(self,text,**kwargs):
        return parse_when(text,now=kwargs.get('now',self.now),timezone=kwargs.get('timezone','Asia/Dhaka'))

    def test_required_examples(self):
        cases={'today at 10pm':(9,22,0),'tomorrow at 1 am':(10,1,0),
               '10 november 2pm':(10,14,0),'in 2 minutes':(9,12,2)}
        for text,expected in cases.items():
            with self.subTest(text=text):
                value=self.parse(text)
                self.assertEqual((value.day,value.hour,value.minute),expected)
                self.assertEqual(value.utcoffset(),timedelta(hours=6))

    def test_explicit_year_and_iso_offsets(self):
        self.assertEqual(self.parse('10 November 2027 2pm').year,2027)
        value=self.parse('2026-11-10T08:00:00Z')
        self.assertEqual((value.hour,value.minute),(14,0))
        self.assertEqual(self.parse('2026-11-10T14:00').hour,14)

    def test_clock_zone_controls_today(self):
        now=datetime(2026,11,9,20,tzinfo=timezone.utc)
        value=self.parse('today at 10pm',now=now)
        self.assertEqual((value.day,value.hour),(10,22))

    def test_relative_duration_uses_elapsed_time_across_dst(self):
        now=datetime(2026,3,8,1,30,tzinfo=ZoneInfo('America/New_York'))
        value=self.parse('in 2 hours',now=now,timezone='America/New_York')
        self.assertEqual(value.hour,4)
        self.assertEqual(value.timestamp()-now.timestamp(),7200)

    def test_past_ambiguous_invalid_and_year_rollover_clarify(self):
        for text in ('today at 1am','9 november 10am','1 january 2pm','10/11 2pm',
                     'tomorrow at 1','31 february 2027 2pm','in 0 minutes','2026-11-10',
                     'someday','', 'tomorrow at 25:00'):
            with self.subTest(text=text),self.assertRaises(TimeClarification):
                self.parse(text)

    def test_dst_gap_and_fold_require_clarification(self):
        for now,text in ((datetime(2026,3,7,12,tzinfo=timezone.utc),'tomorrow at 2:30am'),
                         (datetime(2026,10,31,12,tzinfo=timezone.utc),'tomorrow at 1:30am')):
            with self.subTest(text=text),self.assertRaises(TimeClarification):
                self.parse(text,now=now,timezone='America/New_York')
        value=self.parse('2026-11-01T01:30:00-05:00',
                         now=datetime(2026,10,31,tzinfo=timezone.utc),timezone='America/New_York')
        self.assertEqual(value.fold,1)

    def test_aware_clock_and_valid_zone_required(self):
        for now,zone in ((datetime(2026,11,9),'Asia/Dhaka'),(self.now,'Invalid/Zone')):
            with self.assertRaises(TimeClarification):
                self.parse('in 2 minutes',now=now,timezone=zone)

    def test_noon_midnight_and_leap_year_are_explicit(self):
        self.assertEqual(self.parse('tomorrow at 12am').hour,0)
        self.assertEqual(self.parse('tomorrow at 12pm').hour,12)
        with self.assertRaises(TimeClarification):
            self.parse('29 february 2pm')
        self.assertEqual(self.parse('29 february 2028 2pm').year,2028)
