# encoding: utf-8

'''Tests for the ckan.lib.email_notifications module.

Note that email_notifications is used by an action function, so most of the
tests for the module are done by testing the action function in
ckan.test.functional.api. This test module contains some additional unit tests.

'''
import datetime

import nose.tools

import ckan.lib.email_notifications as email_notifications
import ckan.logic as logic


def test_string_to_time_delta():
    assert email_notifications.string_to_timedelta('1 day') == (
            datetime.timedelta(days=1))
    assert email_notifications.string_to_timedelta('1  day') == (
            datetime.timedelta(days=1))
    assert email_notifications.string_to_timedelta('2 days') == (
            datetime.timedelta(days=2))
    assert email_notifications.string_to_timedelta('2\tdays') == (
            datetime.timedelta(days=2))
    assert email_notifications.string_to_timedelta('14 days') == (
            datetime.timedelta(days=14))
    assert email_notifications.string_to_timedelta('4:35:00') == (
            datetime.timedelta(hours=4, minutes=35, seconds=00))
    assert email_notifications.string_to_timedelta('4:35:12.087465') == (
            datetime.timedelta(hours=4, minutes=35, seconds=12,
                milliseconds=87, microseconds=465))
    assert email_notifications.string_to_timedelta('1 day, 3:23:34') == (
            datetime.timedelta(days=1, hours=3, minutes=23, seconds=34))
    assert email_notifications.string_to_timedelta('1 day,   3:23:34') == (
            datetime.timedelta(days=1, hours=3, minutes=23, seconds=34))
    assert email_notifications.string_to_timedelta('7 days, 3:23:34') == (
            datetime.timedelta(days=7, hours=3, minutes=23, seconds=34))
    assert email_notifications.string_to_timedelta('7 days,\t3:23:34') == (
            datetime.timedelta(days=7, hours=3, minutes=23, seconds=34))
    assert email_notifications.string_to_timedelta(
            '7 days, 3:23:34.087465') == datetime.timedelta(days=7, hours=3,
                    minutes=23, seconds=34, milliseconds=87, microseconds=465)
    assert email_notifications.string_to_timedelta('.123456') == (
            datetime.timedelta(milliseconds=123, microseconds=456))
    nose.tools.assert_raises(logic.ValidationError,
        email_notifications.string_to_timedelta, 'foobar')
