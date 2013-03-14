from datetime import timedelta, datetime, date
from time import strftime, gmtime, struct_time, time, mktime, localtime
from calendar import timegm


def _convert_utc_time(value=None):
    mcs = 0
    if value:
        if isinstance(value, struct_time):
            ttuple = gmtime(value)
        elif isinstance(value, datetime):
            if value.tzinfo and value.tzinfo.utcoffset(value):
                ttuple = value.utctimetuple()
            else:
                ttuple = value.timetuple()
            mcs = value.microsecond
        else:
            raise TypeError('Cannot convert {}'.format(value.__class__))
    else:
        now = datetime.utcnow()
        ttuple = now.timetuple()
        mcs = now.microsecond
    return timegm(ttuple) + float(mcs) / 1000000.0


def _convert_local_time(value=None):
    mcs = 0
    if value:
        if isinstance(value, struct_time):
            ttuple = localtime(value)
        elif isinstance(value, datetime):
            ttuple = value.timetuple()
            mcs = value.microsecond
        else:
            raise TypeError('Cannot convert {}'.format(value.__class__))
    else:
        return time()
    return mktime(ttuple) + float(mcs) / 1000000.0


def _convert_time(value=None, utc=True, **kwargs):
    if value and isinstance(value, timedelta):
        return float(value.total_seconds())
    elif not value and kwargs:
        return float(timedelta(**kwargs).total_seconds())

    if utc:
        return _convert_utc_time(value)
    else:
        return _convert_local_time(value)


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
    dt = gmtime(ts / 1000)
    return milliseconds(datetime(dt.tm_year, dt.tm_mon, dt.tm_mday))


def month(ts=None):
    """Floor provided timestamp to the start of the month.

    :param ts: timestamp in milliseconds.
    :return: timestamp in milliseconds which corresponds the time when the day for provided timestamp started.
    """
    ts = ts or milliseconds()
    dt = gmtime(ts / 1000)
    return milliseconds(datetime(dt.tm_year, dt.tm_mon, 1))


def next_month(ts=None):
    """Ceil provided timestamp to the end of the month.

    :param ts: timestamp in milliseconds.
    :return: timestamp in milliseconds which corresponds the time when the next month begins.
    """
    ts = ts or milliseconds()
    dt = gmtime(ts / 1000)
    try:
        return milliseconds(datetime(dt.tm_year, dt.tm_mon + 1, 1))
    except ValueError:
        return milliseconds(datetime(dt.tm_year + 1, 1, 1))


def format_ts(pattern, ts=None):
    ts = ts or milliseconds()
    return strftime(pattern, gmtime(ts / 1000))
