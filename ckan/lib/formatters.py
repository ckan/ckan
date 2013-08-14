import datetime

from babel import numbers

import ckan.lib.i18n as i18n

from ckan.common import _, ungettext


##################################################
#                                                #
#              Month translations                #
#                                                #
##################################################

def _month_jan():
    return _('January')


def _month_feb():
    return _('February')


def _month_mar():
    return _('March')


def _month_apr():
    return _('April')


def _month_may():
    return _('May')


def _month_june():
    return _('June')


def _month_july():
    return _('July')


def _month_aug():
    return _('August')


def _month_sept():
    return _('September')


def _month_oct():
    return _('October')


def _month_nov():
    return _('November')


def _month_dec():
    return _('December')


# _MONTH_FUNCTIONS provides an easy way to get a localised month via
# _MONTH_FUNCTIONS[month]() where months are zero based ie jan = 0, dec = 11
_MONTH_FUNCTIONS = [_month_jan, _month_feb, _month_mar, _month_apr,
                   _month_may, _month_june, _month_july, _month_aug,
                   _month_sept, _month_oct, _month_nov, _month_dec]


def localised_nice_date(datetime_, show_date=False, with_hours=False):
    ''' Returns a friendly localised unicode representation of a datetime.

    :param datetime_: The date to format
    :type datetime_: datetime
    :param show_date: Show date not 2 days ago etc
    :type show_date: bool
    :param with_hours: should the `hours:mins` be shown for dates
    :type with_hours: bool

    :rtype: sting
    '''

    def months_between(date1, date2):
        if date1 > date2:
            date1, date2 = date2, date1
        m1 = date1.year * 12 + date1.month
        m2 = date2.year * 12 + date2.month
        months = m2 - m1
        if date1.day > date2.day:
            months -= 1
        elif date1.day == date2.day:
            seconds1 = date1.hour * 3600 + date1.minute + date1.second
            seconds2 = date2.hour * 3600 + date2.minute + date2.second
            if seconds1 > seconds2:
                months -= 1
        return months

    if not show_date:
        now = datetime.datetime.now()
        date_diff = now - datetime_
        days = date_diff.days
        if days < 1 and now > datetime_:
            # less than one day
            seconds = date_diff.seconds
            if seconds < 3600:
                # less than one hour
                if seconds < 60:
                    return _('Just now')
                else:
                    return ungettext('{mins} minute ago', '{mins} minutes ago',
                                     seconds / 60).format(mins=seconds / 60)
            else:
                return ungettext('{hours} hour ago', '{hours} hours ago',
                                 seconds / 3600).format(hours=seconds / 3600)
        # more than one day
        months = months_between(datetime_, now)

        if months < 1:
            return ungettext('{days} day ago', '{days} days ago',
                             days).format(days=days)
        if months < 13:
            return ungettext('{months} month ago', '{months} months ago',
                             months).format(months=months)
        return ungettext('over {years} year ago', 'over {years} years ago',
                         months / 12).format(years=months / 12)
    # actual date
    details = {
        'min': datetime_.minute,
        'hour': datetime_.hour,
        'day': datetime_.day,
        'year': datetime_.year,
        'month': _MONTH_FUNCTIONS[datetime_.month - 1](),
    }
    if with_hours:
        return (
            # NOTE: This is for translating dates like `April 24, 2013, 10:45`
            _('{month} {day}, {year}, {hour:02}:{min:02}').format(**details))
    else:
        return (
            # NOTE: This is for translating dates like `April 24, 2013`
            _('{month} {day}, {year}').format(**details))


def localised_number(number):
    ''' Returns a localised unicode representation of number '''
    return numbers.format_number(number, locale=i18n.get_lang())


def localised_filesize(number):
    ''' Returns a localised unicode representation of a number in bytes, MiB
    etc '''
    def rnd(number, divisor):
        # round to 1 decimal place
        return localised_number(float(number * 10 / divisor) / 10)

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


def localised_SI_number(number):
    ''' Returns a localised unicode representation of a number in SI format
    eg 14700 becomes 14.7k '''

    def rnd(number, divisor):
        # round to 1 decimal place
        return localised_number(float(number * 10 / divisor) / 10)

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
