# -*- coding: utf-8 -*-

import six
import pytest
import pytz
from ckan.lib import formatters as f
from datetime import datetime


@pytest.mark.parametrize(
    u"number,expected",
    [
        (1, u"1"),
        (1e3, u"1k"),
        (1e6, u"1M"),
        (1e6 + 32e3, u"1M"),
        (1e9, u"1G"),
        (1e9 + 1, u"1G"),
        (1e12, u"1T"),
        (1e12 + 9e11, u"1.9T"),
        (1e15, u"1P"),
        (1e18, u"1E"),
        (1e21, u"1Z"),
        (1e25, u"10Y"),
    ],
)
@pytest.mark.usefixtures(u"with_request_context")
def test_localized_SI_number(number, expected):
    assert f.localised_SI_number(number) == expected


@pytest.mark.parametrize(
    u"size,expected",
    [
        (1, u"1 bytes"),
        (1024, u"1 KiB"),
        (1024 ** 2, u"1 MiB"),
        (1024 ** 2 + 1024 * 31, u"1 MiB"),
        (1024 ** 3, u"1 GiB"),
        (1024 ** 3 + 1, u"1 GiB"),
        (1024 ** 4, u"1 TiB"),
        (1024 ** 4 + 1024 ** 3 * 900, u"1.8 TiB"),
    ],
)
@pytest.mark.usefixtures(u"with_request_context")
def test_localized_filesize(size, expected):
    assert f.localised_filesize(size) == expected


_now = datetime(2017, 10, 23, 16, 3, 52, tzinfo=pytz.UTC)


@pytest.mark.freeze_time(_now)
@pytest.mark.usefixtures(u"with_request_context")
class TestLocalizedNiceDate(object):
    @pytest.mark.parametrize(
        u"dt,date,hours,seconds,expected",
        [
            (_now, False, False, False, u"Just now"),
            (_now, True, False, False, u"October 23, 2017"),
            (_now, True, True, False, u"October 23, 2017, 16:03 (UTC)"),
            (_now, True, True, True, u"October 23, 2017 at 4:03:52 PM UTC"),
            (_now, False, True, True, u"Just now"),
            (_now, False, False, True, u"Just now"),
            (_now, False, True, False, u"Just now"),
        ],
    )
    def test_params(self, dt, date, hours, seconds, expected):
        assert f.localised_nice_date(dt, date, hours, seconds) == expected

    @pytest.mark.parametrize(
        u"dt,expected",
        [
            (_now, u"Just now"),
            (_now.replace(second=_now.second - 30), u"30 seconds ago"),
            (_now.replace(minute=_now.minute - 2), u"2 minutes ago"),
            (_now.replace(hour=_now.hour - 4), u"4 hours ago"),
            (_now.replace(day=_now.day - 5), u"5 days ago"),
            (_now.replace(day=_now.day - 8), u"1 week ago"),
            (_now.replace(month=_now.month - 4), u"4 months ago"),
            (_now.replace(year=_now.year - 5), u"5 years ago"),
            (_now.replace(second=_now.second + 5), u"in 5 seconds"),
            (_now.replace(minute=_now.minute + 2), u"in 2 minutes"),
            (_now.replace(hour=_now.hour + 4), u"in 4 hours"),
            (_now.replace(day=_now.day + 5), u"in 5 days"),
            (_now.replace(day=_now.day + 8), u"in 1 week"),
            (_now.replace(month=_now.month + 1), u"in 1 month"),
            (_now.replace(year=_now.year + 5), u"in 5 years"),
        ],
    )
    def test_relative_dates(self, dt, expected):
        assert f.localised_nice_date(dt) == expected

    @pytest.mark.parametrize(
        u"dt,hours,seconds,fmt,expected",
        [
            (_now, False, False, None, u"October 23, 2017"),
            (_now, False, False, u"MMM, YY", u"Oct, 17"),
            (_now, True, False, None, u"October 23, 2017, 16:03 (UTC)"),
            (_now, True, False, u"EEE, HH:mm", u"Mon, 16:03"),
            (_now, True, True, None, u"October 23, 2017 at 4:03:52 PM UTC"),
            (
                _now,
                True,
                False,
                u"MMM dd, yy. EEEE 'at' hh:mm:ss [z]",
                u"Oct 23, 17. Monday at 04:03:52 [UTC]",
            ),
        ],
    )
    def test_with_dates(self, dt, hours, seconds, fmt, expected):
        assert f.localised_nice_date(dt, True, hours, seconds, fmt) == expected
