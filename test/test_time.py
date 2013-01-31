from datetime import timedelta, date, datetime
from cherrycommon.timeutils import milliseconds, seconds, day, month, DAY, HOUR

__author__ = 'sunrize'

import unittest

class TimeTest(unittest.TestCase):
    def test_kwargs(self):
        self.assertEqual(milliseconds(timedelta(hours=1)), milliseconds(hours=1))
        self.assertEqual(seconds(timedelta(hours=1)), seconds(hours=1))

    def test_day(self):
        d = datetime(2013, 1, 1)
        day_start = milliseconds(d)
        ts = milliseconds(datetime(2013, 1, 1, 23))
        self.assertEqual(day_start, day(ts))

    def test_month(self):
        month_start = milliseconds(datetime(2013, 1, 1))
        ts = milliseconds(datetime(year=2013, month=1, day=2, hour=2))
        self.assertEqual(month_start, month(ts))


if __name__ == '__main__':
    unittest.main()
