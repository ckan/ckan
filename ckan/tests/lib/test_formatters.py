# -*- coding: utf-8 -*-

import pytest
import pytz
from ckan.lib import formatters as f
from datetime import datetime


@pytest.mark.parametrize(
    "number,expected",
    [
        (1, "1"),
        (1e3, "1k"),
        (1e6, "1M"),
        (1e6 + 32e3, "1M"),
        (1e9, "1G"),
        (1e9 + 1, "1G"),
        (1e12, "1T"),
        (1e12 + 9e11, "1.9T"),
        (1e15, "1P"),
        (1e18, "1E"),
        (1e21, "1Z"),
        (1e25, "10Y"),
    ],
)
@pytest.mark.usefixtures("with_request_context")
def test_localized_SI_number(number, expected):
    assert f.localised_SI_number(number) == expected


@pytest.mark.parametrize(
    "size,expected",
    [
        (1, "1 bytes"),
        (1024, "1 KiB"),
        (1024 ** 2, "1 MiB"),
        (1024 ** 2 + 1024 * 31, "1 MiB"),
        (1024 ** 3, "1 GiB"),
        (1024 ** 3 + 1, "1 GiB"),
        (1024 ** 4, "1 TiB"),
        (1024 ** 4 + 1024 ** 3 * 900, "1.8 TiB"),
    ],
)
@pytest.mark.usefixtures("with_request_context")
def test_localized_filesize(size, expected):
    assert f.localised_filesize(size) == expected


_now = datetime(2017, 10, 23, 16, 3, 52, tzinfo=pytz.UTC)


@pytest.mark.freeze_time(_now)
@pytest.mark.usefixtures("with_request_context")
class TestLocalizedNiceDate(object):
    @pytest.mark.parametrize(
        "dt,date,hours,seconds,expected",
        [
            (_now, False, False, False, "Just now"),
            (_now, True, False, False, "October 23, 2017"),
            (_now, True, True, False, "October 23, 2017, 16:03 (UTC)"),
            (_now, True, True, True, "October 23, 2017 at 4:03:52 PM UTC"),
            (_now, False, True, True, "Just now"),
            (_now, False, False, True, "Just now"),
            (_now, False, True, False, "Just now"),
        ],
    )
    def test_params(self, dt, date, hours, seconds, expected):
        assert f.localised_nice_date(dt, date, hours, seconds) == expected

    @pytest.mark.parametrize(
        "dt,expected",
        [
            (_now, "Just now"),
            (_now.replace(second=_now.second - 30), "30 seconds ago"),
            (_now.replace(minute=_now.minute - 2), "2 minutes ago"),
            (_now.replace(hour=_now.hour - 4), "4 hours ago"),
            (_now.replace(day=_now.day - 5), "5 days ago"),
            (_now.replace(day=_now.day - 8), "1 week ago"),
            (_now.replace(month=_now.month - 4), "4 months ago"),
            (_now.replace(year=_now.year - 5), "5 years ago"),
            (_now.replace(second=_now.second + 5), "in 5 seconds"),
            (_now.replace(minute=_now.minute + 2), "in 2 minutes"),
            (_now.replace(hour=_now.hour + 4), "in 4 hours"),
            (_now.replace(day=_now.day + 5), "in 5 days"),
            (_now.replace(day=_now.day + 8), "in 1 week"),
            (_now.replace(month=_now.month + 1), "in 1 month"),
            (_now.replace(year=_now.year + 5), "in 5 years"),
        ],
    )
    def test_relative_dates(self, dt, expected):
        assert f.localised_nice_date(dt) == expected

    @pytest.mark.parametrize(
        "dt,hours,seconds,fmt,expected",
        [
            (_now, False, False, None, "October 23, 2017"),
            (_now, False, False, "MMM, YY", "Oct, 17"),
            (_now, True, False, None, "October 23, 2017, 16:03 (UTC)"),
            (_now, True, False, "EEE, HH:mm", "Mon, 16:03"),
            (_now, True, True, None, "October 23, 2017 at 4:03:52 PM UTC"),
            (
                _now,
                True,
                False,
                "MMM dd, yy. EEEE 'at' hh:mm:ss [z]",
                "Oct 23, 17. Monday at 04:03:52 [UTC]",
            ),
        ],
    )
    def test_with_dates(self, dt, hours, seconds, fmt, expected):
        assert f.localised_nice_date(dt, True, hours, seconds, fmt) == expected
