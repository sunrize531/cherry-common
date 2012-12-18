from datetime import timedelta, datetime
from time import mktime, struct_time

def _convert_time(value=None, utc=True, **kwargs):
    if isinstance(value, timedelta):
        return float(value.total_seconds())
    if isinstance(value, struct_time):
        return mktime(value)

    if isinstance(value, datetime):
        dt = value
    elif value is None:
        if kwargs:
            return float(timedelta(**kwargs).total_seconds())
        if utc:
            dt = datetime.utcnow()
        else:
            dt = datetime.now()
    else:
        raise TypeError('Cannot convert {}'.format(value.__class__))

    if utc and dt.tzinfo:
        ttuple = dt.utctimetuple()
    else:
        ttuple = dt.timetuple()
    return mktime(ttuple) + float(dt.microsecond) / 1000000.0

def milliseconds(value=None, utc=True, **kwargs):
    """
    Converts value to milliseconds. If value is timedelta or struc_time, it will be just converted to milliseconds.
    If value is datetime instance it will be converted to milliseconds since epoch (UTC). If value is number,
    it's assumed that it's in seconds, so it will be just multiplied to 1000.
    """
    return long(_convert_time(value, utc) * 1000.0)

def seconds(value=None, utc=True, **kwargs):
    """
    Converts value to seconds. If value is timedelta or struc_time, it will be just converted to seconds.
    If value is datetime instance it will be converted to milliseconds since epoch (UTC). If value is number,
    it's assumed that it's in milliseconds, so it will be just divided by 1000.
    """
    if isinstance(value, (int, long, float)):
        return long(float(value) / 1000.0)
    else:
        return _convert_time(value, utc)

def get_timeout(value=None, utc=False):
    """
    Return local timestamp in seconds, for the time that come in value seconds.
    Value will be converted to seconds using seconds() function.
    """
    if not isinstance(value, (int, long, float,)):
        value = seconds(value)
    else:
        value = long(value)
    value += seconds(utc=utc)
    return value


