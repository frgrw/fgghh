import datetime
import unittest
from dateutil import parser, tz

from main import check_schedule
from util import parse_schedule


class ScheduleTestCase(unittest.TestCase):
    def test_every_days(self):
        start = parser.parse("Nov 4 2019").replace(tzinfo=tz.UTC)
        event_29_days_later = parser.parse("2019-12-03T04:23:50.830Z")
        self.assertTrue(check_schedule(start, event_29_days_later, 29))
        for i in range(1, 29):
            self.assertFalse(check_schedule(start, event_29_days_later + datetime.timedelta(days=i), 29))
        self.assertTrue(check_schedule(start, event_29_days_later + datetime.timedelta(days=29), 29))

    def schedule_parsing(self):
        self.assertEqual(parse_schedule("0 * * * *", "UTC"), ("0 * * * *", {}))

        cron, schedule = parse_schedule("starting  Jan 1 2019 every 11  days at 13:00", "America/Los_Angeles")
        self.assertEqual(cron, "0 13 * * *")
        start = parser.parse("Jan 1 2019").replace(tzinfo=tz.gettz("America/Los_Angeles"))
        self.assertEqual(schedule, {'start': start, 'frequency': 11, 'unit': 'day'})


if __name__ == '__main__':
    unittest.main()
