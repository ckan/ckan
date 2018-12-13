import time
import calendar
from datetime import datetime, date, timedelta, tzinfo
from rfc822 import parsedate_tz, mktime_tz, formatdate

__all__ = [
    'UTC', 'timedelta_to_seconds',
    'year', 'month', 'week', 'day', 'hour', 'minute', 'second',
    'parse_date', 'serialize_date',
    'parse_date_delta', 'serialize_date_delta',
]

_now = datetime.now # hook point for unit tests

class _UTC(tzinfo):
    def dst(self, dt):
        return timedelta(0)
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return 'UTC'
    def __repr__(self):
        return 'UTC'

UTC = _UTC()



def timedelta_to_seconds(td):
    """
    Converts a timedelta instance to seconds.
    """
    return td.seconds + (td.days*24*60*60)

day = timedelta(days=1)
week = timedelta(weeks=1)
hour = timedelta(hours=1)
minute = timedelta(minutes=1)
second = timedelta(seconds=1)
# Estimate, I know; good enough for expirations
month = timedelta(days=30)
year = timedelta(days=365)


def parse_date(value):
    if not value:
        return None
    try:
        value = str(value)
    except:
        return None
    t = parsedate_tz(value)
    if t is None:
        # Could not parse
        return None
    if t[-1] is None:
        # No timezone given.  None would mean local time, but we'll force UTC
        t = t[:9] + (0,)
    t = mktime_tz(t)
    return datetime.fromtimestamp(t, UTC)

def serialize_date(dt):
    if isinstance(dt, unicode):
        dt = dt.encode('ascii')
    if isinstance(dt, str):
        return dt
    if isinstance(dt, timedelta):
        dt = _now() + dt
    if isinstance(dt, (datetime, date)):
        dt = dt.timetuple()
    if isinstance(dt, (tuple, time.struct_time)):
        dt = calendar.timegm(dt)
    if not isinstance(dt, (float, int, long)):
        raise ValueError(
            "You must pass in a datetime, date, time tuple, or integer object, not %r" % dt)
    return formatdate(dt)



def parse_date_delta(value):
    """
    like parse_date, but also handle delta seconds
    """
    if not value:
        return None
    try:
        value = int(value)
    except ValueError:
        return parse_date(value)
    else:
        return _now() + timedelta(seconds=value)


def serialize_date_delta(value):
    if isinstance(value, (float, int)):
        return str(int(value))
    else:
        return serialize_date(value)

