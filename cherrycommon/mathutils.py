from bisect import insort_left
import struct
from threading import Lock
import os
from cherrycommon.timeutils import seconds, milliseconds


_inc_lock = Lock()
_inc = 0
_pid = int(os.getpid()) % 0xffff
def random_id():
    """
    Generate random id, based on timestamp, assumed to be unique for this process.
    """
    global _inc
    _inc_lock.acquire()
    ts = milliseconds()
    s = ts / 1000
    ds = ts / 100 - s * 10
    i = '{}{}{}{}'.format(
        struct.pack('>I', s),
        struct.pack('>B', ds),
        struct.pack('>H', _pid),
        struct.pack('>H', _inc)
    )
    _inc = (_inc + 1) % 0xffff
    _inc_lock.release()
    return i.encode('hex')


class Median(object):
    def __init__(self, *args):
        self.values = sorted(args)

    def __add__(self, other):
        insort_left(self.values, float(other))
        return self

    def clear(self):
        self.values = []

    @property
    def min(self):
        try:
            return self.values[0]
        except IndexError:
            return 0

    @property
    def max(self):
        try:
            return self.values[-1]
        except IndexError:
            return 0

    @property
    def len(self):
        return len(self.values)

    @property
    def avg(self):
        return self.sum / max(self.len, 1)

    @property
    def med(self):
        index = int(self.len / 2)
        try:
            return self.values[index]
        except IndexError:
            return 0

    @property
    def sum(self):
        return sum(self.values)

    def __repr__(self):
        return '(min: {:.1f}, max: {:.1f}, med: {:.1f}, avg: {:.2f})'.format(self.min, self.max, self.med, self.avg)

    def __str__(self):
        return self.__repr__()