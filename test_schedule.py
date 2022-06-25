import datetime
import unittest
from dateutil import parser, tz

from main import check_ndays_schedule, check_day_of_week
from update_reminders import parse_schedule


class ScheduleTestCase(unittest.TestCase):
    def test_every_days(self):
        start = parser.parse("Nov 4 2019").replace(tzinfo=tz.UTC)
        event_29_days_later = parser.parse("2019-12-03T04:23:50.830Z")
        self.assertTrue(check_ndays_schedule(start, event_29_days_later, 29))
        for i in range(1, 29):
            self.assertFalse(check_ndays_schedule(start, event_29_days_later + datetime.timedelta(days=i), 29))
        self.assertTrue(check_ndays_schedule(start, event_29_days_later + datetime.timedelta(days=29), 29))

    def test_day_of_week(self):
        event = parser.parse("Jun 25 2022").replace(tzinfo=tz.UTC)
        self.assertTrue(check_day_of_week(event, 6))
        self.assertFalse(check_day_of_week(event, 7))

    def test_schedule_parsing(self):
        self.assertEqual(parse_schedule("0 * * * *"), ("0 * * * *", {}, None))

        cron, schedule, day_of_week = parse_schedule("starting  Jan 1 2019 every 11  days at 13:00")
        self.assertEqual(cron, "0 13 * * *")
        self.assertEqual(schedule, {'start': '2019-01-01', 'frequency': 11, 'unit': 'day'})
        self.assertIsNone(day_of_week)

    def test_day_of_week_parsing(self):
        cron, schedule, day_of_week = parse_schedule("on 1st Weds in May at 13:00")
        self.assertEqual(cron, "0 13 1-7 5 *")
        self.assertEqual(schedule, {})
        self.assertEqual(day_of_week, 3)


if __name__ == '__main__':
    unittest.main()
