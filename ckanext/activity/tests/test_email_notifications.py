# encoding: utf-8

import datetime

import pytest

import ckanext.activity.email_notifications as email_notifications
import ckan.logic as logic


@pytest.mark.parametrize(
    "text,delta",
    [
        ("1 day", datetime.timedelta(days=1)),
        ("1  day", datetime.timedelta(days=1)),
        ("2 days", datetime.timedelta(days=2)),
        ("2\tdays", datetime.timedelta(days=2)),
        ("14 days", datetime.timedelta(days=14)),
        ("4:35:00", datetime.timedelta(hours=4, minutes=35, seconds=00)),
        (
            "4:35:12.087465",
            datetime.timedelta(
                hours=4,
                minutes=35,
                seconds=12,
                milliseconds=87,
                microseconds=465,
            ),
        ),
        (
            "1 day, 3:23:34",
            datetime.timedelta(days=1, hours=3, minutes=23, seconds=34),
        ),
        (
            "1 day,   3:23:34",
            datetime.timedelta(days=1, hours=3, minutes=23, seconds=34),
        ),
        (
            "7 days, 3:23:34",
            datetime.timedelta(days=7, hours=3, minutes=23, seconds=34),
        ),
        (
            "7 days,\t3:23:34",
            datetime.timedelta(days=7, hours=3, minutes=23, seconds=34),
        ),
        (
            "7 days, 3:23:34.087465",
            datetime.timedelta(
                days=7,
                hours=3,
                minutes=23,
                seconds=34,
                milliseconds=87,
                microseconds=465,
            ),
        ),
        (".123456", datetime.timedelta(milliseconds=123, microseconds=456)),
    ],
)
def test_valid_string_to_time_delta(text, delta):
    assert email_notifications.string_to_timedelta(text) == delta


def test_invalid_string_to_time_delta():
    with pytest.raises(logic.ValidationError):
        email_notifications.string_to_timedelta("foobar")
