from cherrycommon.mathutils import random_id

__author__ = 'sunrize'

import unittest

class RandomIDTest(unittest.TestCase):
    def test_random_id(self):
        rid0 = random_id()
        rid1 = random_id()
        self.assertGreater(rid1, rid0)

if __name__ == '__main__':
    unittest.main()
