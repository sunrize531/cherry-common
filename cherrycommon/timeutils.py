from datetime import timedelta, datetime, date
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

    if utc and (dt.tzinfo and dt.tzinfo.utcoffset(dt)):
        ttuple = dt.utctimetuple()
    else:
        ttuple = dt.timetuple()
    return mktime(ttuple) + float(dt.microsecond) / 1000000.0

def milliseconds(value=None, utc=True, **kwargs):
    """Converts value to milliseconds. If value is timedelta or struc_time, it will be just converted to milliseconds.
    If value is datetime instance it will be converted to milliseconds since epoch (UTC). If value is number,
    it's assumed that it's in seconds, so it will be just multiplied to 1000. You can also provide named arguments,
    same as for timedelta function.
    """
    return long(_convert_time(value, utc, **kwargs) * 1000.0)

def seconds(value=None, utc=True, **kwargs):
    """
    Converts value to seconds. If value is timedelta or struc_time, it will be just converted to seconds.
    If value is datetime instance it will be converted to milliseconds since epoch (UTC). If value is number,
    it's assumed that it's in milliseconds, so it will be just divided by 1000. You can also provide named arguments,
    same as for timedelta function.
    """
    if isinstance(value, (int, long, float)):
        return long(float(value) / 1000.0)
    else:
        return _convert_time(value, utc, **kwargs)

def get_timeout(value=None, utc=False, **kwargs):
    """
    Return local timestamp in seconds, for the time that come in value seconds.
    Value will be converted to seconds using seconds() function.
    """
    if value is None:
        value = seconds(**kwargs)
    elif not isinstance(value, (int, long, float,)):
        value = seconds(value)
    else:
        value = long(value)
    value += seconds(utc=utc)
    return value

DAY = milliseconds(days=1)
HOUR = milliseconds(hours=1)

def day(ts=None):
    """Floor provided timestamp (in milliseconds) to the start of the day.

    :param ts: timestamp in milliseconds.
    :return: timestamp in milliseconds which corresponds the time when the day for provided timestamp started.
    """
    ts = ts or milliseconds()
    dt = datetime.utcfromtimestamp(ts / 1000)
    return milliseconds(datetime(dt.year, dt.month, dt.day))

def month(ts=None):
    """Floor provided timestamp to the start of the month.

    :param ts: timestamp in milliseconds.
    :return: timestamp in milliseconds which corresponds the time when the day for provided timestamp started.
    """
    ts = ts or milliseconds()
    dt = datetime.utcfromtimestamp(ts / 1000)
    return milliseconds(datetime(dt.year, dt.month, 1))

def next_month(ts=None):
    """Ceil provided timestamp to the end of the month.

    :param ts: timestamp in milliseconds.
    :return: timestamp in milliseconds which corresponds the time when the next month begins.
    """
    ts = ts or milliseconds()
    dt = datetime.utcfromtimestamp(ts / 1000)
    try:
        return milliseconds(datetime(dt.year, dt.month+1, 1))
    except ValueError:
        return milliseconds(datetime(dt.year + 1, 1, 1))


