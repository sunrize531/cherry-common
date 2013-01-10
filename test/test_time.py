from datetime import timedelta
from cherrycommon.timeutils import milliseconds, seconds

__author__ = 'sunrize'

import unittest

class TimeTest(unittest.TestCase):
    def test_kwargs(self):
        self.assertEqual(milliseconds(timedelta(hours=1)), milliseconds(hours=1))
        self.assertEqual(seconds(timedelta(hours=1)), seconds(hours=1))

if __name__ == '__main__':
    unittest.main()
