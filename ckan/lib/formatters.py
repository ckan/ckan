# encoding: utf-8

import datetime
import pytz
from typing import Optional

from flask_babel import (
    format_decimal,
    format_datetime,
    format_date,
    format_timedelta
)

from ckan.common import _


def localised_nice_date(datetime_: datetime.datetime,
                        show_date: bool = False,
                        with_hours: bool = False,
                        with_seconds: bool = False,
                        format: Optional[str] = None) -> str:
    ''' Returns a friendly localised unicode representation of a datetime.
    e.g. '31 minutes ago'
         '1 day ago'
         'April 24, 2013'  (show_date=True)
         'October 25, 2017, 16:03 (UTC)' (show_date=True, with_hours=True)
         'Apr 3, 2020, 4:00:31 PM' (
                 show_date=True, with_hours=True, format='medium')
         'April 03, 20' (show_date=True, format='MMMM dd, YY')

    :param datetime_: The date to format
    :type datetime_: datetime
    :param show_date: Show 'April 24, 2013' instead of '2 days ago'
    :type show_date: bool
    :param with_hours: should the `hours:mins` be shown for dates
    :type with_hours: bool
    :param with_seconds: should the `hours:mins:seconds` be shown for dates
    :type with_seconds: bool
    :param format: override format of datetime representation using babel
        date/time pattern syntax of predefined pattern.
    :type format: str


    :rtype: sting
    '''
    if datetime_.tzinfo is None:
        datetime_ = datetime_.replace(tzinfo=pytz.utc)
    if not show_date:
        now = datetime.datetime.now(pytz.utc)
        date_diff = datetime_ - now
        if abs(date_diff) < datetime.timedelta(seconds=1):
            return _('Just now')
        return format_timedelta(date_diff, add_direction=True)

    if with_seconds:
        return format_datetime(datetime_, format or 'long')
    elif with_hours:
        fmt_str = "MMMM d, YYYY, HH:mm (z)"
        return format_datetime(datetime_, format or fmt_str)
    else:
        return format_date(datetime_, format or 'long')


def localised_number(number: float) -> str:
    ''' Returns a localised unicode representation of number '''
    return format_decimal(number)


def localised_filesize(number: int) -> str:
    ''' Returns a localised unicode representation of a number in bytes, MiB
    etc '''
    def rnd(number: int, divisor: int):
        # round to 1 decimal place
        return localised_number(float(number * 10 // divisor) / 10)

    if number < 1024:
        return _('{bytes} bytes').format(bytes=localised_number(number))
    elif number < 1024 ** 2:
        return _('{kibibytes} KiB').format(kibibytes=rnd(number, 1024))
    elif number < 1024 ** 3:
        return _('{mebibytes} MiB').format(mebibytes=rnd(number, 1024 ** 2))
    elif number < 1024 ** 4:
        return _('{gibibytes} GiB').format(gibibytes=rnd(number, 1024 ** 3))
    else:
        return _('{tebibytes} TiB').format(tebibytes=rnd(number, 1024 ** 4))


def localised_SI_number(number: int) -> str:  # noqa
    ''' Returns a localised unicode representation of a number in SI format
    eg 14700 becomes 14.7k '''

    def rnd(number: int, divisor: int):
        # round to 1 decimal place
        return localised_number(float(number * 10 // divisor) / 10)

    if number < 1000:
        return _('{n}').format(n=localised_number(number))
    elif number < 1000 ** 2:
        return _('{k}k').format(k=rnd(number, 1000))
    elif number < 1000 ** 3:
        return _('{m}M').format(m=rnd(number, 1000 ** 2))
    elif number < 1000 ** 4:
        return _('{g}G').format(g=rnd(number, 1000 ** 3))
    elif number < 1000 ** 5:
        return _('{t}T').format(t=rnd(number, 1000 ** 4))
    elif number < 1000 ** 6:
        return _('{p}P').format(p=rnd(number, 1000 ** 5))
    elif number < 1000 ** 7:
        return _('{e}E').format(e=rnd(number, 1000 ** 6))
    elif number < 1000 ** 8:
        return _('{z}Z').format(z=rnd(number, 1000 ** 7))
    else:
        return _('{y}Y').format(y=rnd(number, 1000 ** 8))
