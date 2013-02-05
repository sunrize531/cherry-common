from cherrycommon.mathutils import random_id, unique_id

__author__ = 'sunrize'

import unittest

class RandomIDTest(unittest.TestCase):
    def test_unique_id(self):
        rid0 = unique_id()
        rid1 = unique_id()
        self.assertGreater(rid1, rid0)

if __name__ == '__main__':
    unittest.main()
