from cherrycommon.timeutils import milliseconds, get_timeout
from zmq.eventloop import IOLoop

__author__ = 'sunrize'

import unittest


class ZMQTimeOutCase(unittest.TestCase):
    def test_zmq_timeout(self):
        ts = milliseconds()
        ioloop = IOLoop.instance()

        def _stop_loop():
            ioloop.stop()

        ioloop.add_timeout(get_timeout(seconds=2), _stop_loop)
        ioloop.start()

        self.assertAlmostEqual(milliseconds() - ts, milliseconds(seconds=2), delta=100)


if __name__ == '__main__':
    unittest.main()
