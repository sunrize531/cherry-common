from time import time
from datetime import timedelta, datetime
from cherrycommon.timeutils import milliseconds, seconds, day, month, DAY, HOUR, next_month, format_ts, get_timeout

__author__ = 'sunrize'

import unittest


class TimeTest(unittest.TestCase):
    def test_kwargs(self):
        self.assertEqual(milliseconds(timedelta(hours=1)), milliseconds(hours=1))
        self.assertEqual(seconds(timedelta(hours=1)), seconds(hours=1))

    def test_datetime(self):
        dt = datetime(year=2013, month=1, day=1, hour=23)
        ts = milliseconds(dt)
        self.assertEqual(ts % DAY, HOUR * 23)

    def test_timeout(self):
        now = seconds(utc=False)
        timeout = get_timeout(seconds=5)
        print timeout - now
        self.assertAlmostEquals(now + 5, timeout, delta=1)

    def test_day(self):
        ts = milliseconds(datetime(2013, 1, 1, 23))
        day_start = milliseconds(datetime(2013, 1, 1))
        self.assertEqual(day_start % DAY, 0)
        self.assertEqual(day(ts) % DAY, 0)

        self.assertEqual(day_start, day(ts))
        self.assertEqual(day_start, day(day_start))

    def test_month(self):
        ts = milliseconds(datetime(year=2013, month=1, day=2, hour=2))
        month_start = milliseconds(datetime(year=2013, month=1, day=1))
        self.assertEqual(month_start, month(ts))
        self.assertEqual(month_start, month(month_start))

    def test_next_month(self):
        ts = milliseconds(datetime(year=2013, month=1, day=2, hour=2))
        next_month_start = milliseconds(datetime(2013, 2, 1))
        self.assertEqual(next_month_start, next_month(ts))

    def test_format_ts(self):
        print format_ts('%d.%m.%Y %H:%M %Z')
        dt = datetime(year=2013, month=1, day=2, hour=2)
        ms = milliseconds(dt)

        print format_ts('%d.%m.%Y %H:%M %Z', ms)
        self.assertEqual(format_ts('%d.%m.%Y', ms), '02.01.2013')

        da = day(ms)
        print format_ts('%d.%m.%Y %H:%M %Z', da)
        self.assertEqual(format_ts('%d.%m', da), '02.01')
        self.assertEqual(format_ts('%d.%m %H:%M', da), '02.01 00:00')

        mo = month(ms)
        print format_ts('%d.%m.%Y %H:%M %Z', mo)
        self.assertEqual(format_ts('%d.%m', mo), '01.01')
        self.assertEqual(format_ts('%d.%m %H:%M', mo), '01.01 00:00')

    def test_local_time(self):
        self.assertAlmostEqual(seconds(utc=False), time(), delta=100)


if __name__ == '__main__':
    unittest.main()
