# encoding: utf-8

"""
Code for generating email notifications for users (e.g. email notifications for
new activities in your dashboard activity stream) and emailing them to the
users.

"""
from __future__ import annotations

import datetime
import re
from typing import Any, cast
from jinja2 import Environment

import ckan.model as model
import ckan.logic as logic
import ckan.lib.jinja_extensions as jinja_extensions

from ckan.common import ungettext, ugettext, config
from ckan.types import Context


def string_to_timedelta(s: str) -> datetime.timedelta:
    """Parse a string s and return a standard datetime.timedelta object.

    Handles days, hours, minutes, seconds, and microseconds.

    Accepts strings in these formats:

    2 days
    14 days
    4:35:00 (hours, minutes and seconds)
    4:35:12.087465 (hours, minutes, seconds and microseconds)
    7 days, 3:23:34
    7 days, 3:23:34.087465
    .087465 (microseconds only)

    :raises ckan.logic.ValidationError: if the given string does not match any
        of the recognised formats

    """
    patterns = []
    days_only_pattern = r"(?P<days>\d+)\s+day(s)?"
    patterns.append(days_only_pattern)
    hms_only_pattern = r"(?P<hours>\d?\d):(?P<minutes>\d\d):(?P<seconds>\d\d)"
    patterns.append(hms_only_pattern)
    ms_only_pattern = r".(?P<milliseconds>\d\d\d)(?P<microseconds>\d\d\d)"
    patterns.append(ms_only_pattern)
    hms_and_ms_pattern = hms_only_pattern + ms_only_pattern
    patterns.append(hms_and_ms_pattern)
    days_and_hms_pattern = r"{0},\s+{1}".format(
        days_only_pattern, hms_only_pattern
    )
    patterns.append(days_and_hms_pattern)
    days_and_hms_and_ms_pattern = days_and_hms_pattern + ms_only_pattern
    patterns.append(days_and_hms_and_ms_pattern)

    match = None
    for pattern in patterns:
        match = re.match("^{0}$".format(pattern), s)
        if match:
            break

    if not match:
        raise logic.ValidationError(
            {"message": "Not a valid time: {0}".format(s)}
        )

    gd = match.groupdict()
    days = int(gd.get("days", "0"))
    hours = int(gd.get("hours", "0"))
    minutes = int(gd.get("minutes", "0"))
    seconds = int(gd.get("seconds", "0"))
    milliseconds = int(gd.get("milliseconds", "0"))
    microseconds = int(gd.get("microseconds", "0"))
    delta = datetime.timedelta(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        milliseconds=milliseconds,
        microseconds=microseconds,
    )
    return delta


def render_activity_email(activities: list[dict[str, Any]]) -> str:
    globals = {"site_title": config.get("ckan.site_title")}
    template_name = "activity_streams/activity_stream_email_notifications.text"

    env = Environment(**jinja_extensions.get_jinja_env_options())
    # Install the given gettext, ngettext callables into the environment
    env.install_gettext_callables(ugettext, ungettext)  # type: ignore

    template = env.get_template(template_name, globals=globals)
    return template.render({"activities": activities})


def _notifications_for_activities(
    activities: list[dict[str, Any]], user_dict: dict[str, Any]
) -> list[dict[str, str]]:
    """Return one or more email notifications covering the given activities.

    This function handles grouping multiple activities into a single digest
    email.

    :param activities: the activities to consider
    :type activities: list of activity dicts like those returned by
        ckan.logic.action.get.dashboard_activity_list()

    :returns: a list of email notifications
    :rtype: list of dicts each with keys 'subject' and 'body'

    """
    if not activities:
        return []

    if not user_dict.get("activity_streams_email_notifications"):
        return []

    # We just group all activities into a single "new activity" email that
    # doesn't say anything about _what_ new activities they are.
    # TODO: Here we could generate some smarter content for the emails e.g.
    # say something about the contents of the activities, or single out
    # certain types of activity to be sent in their own individual emails,
    # etc.

    subject = ungettext(
        "{n} new activity from {site_title}",
        "{n} new activities from {site_title}",
        len(activities),
    ).format(site_title=config.get("ckan.site_title"), n=len(activities))

    body = render_activity_email(activities)
    notifications = [{"subject": subject, "body": body}]

    return notifications


def _notifications_from_dashboard_activity_list(
    user_dict: dict[str, Any], since: datetime.datetime
) -> list[dict[str, str]]:
    """Return any email notifications from the given user's dashboard activity
    list since `since`.

    """
    # Get the user's dashboard activity stream.
    context = cast(
        Context,
        {"model": model, "session": model.Session, "user": user_dict["id"]},
    )
    activity_list = logic.get_action("dashboard_activity_list")(context, {})

    # Filter out the user's own activities., so they don't get an email every
    # time they themselves do something (we are not Trac).
    activity_list = [
        activity
        for activity in activity_list
        if activity["user_id"] != user_dict["id"]
    ]

    # Filter out the old activities.
    strptime = datetime.datetime.strptime
    fmt = "%Y-%m-%dT%H:%M:%S.%f"
    activity_list = [
        activity
        for activity in activity_list
        if strptime(activity["timestamp"], fmt) > since
    ]

    return _notifications_for_activities(activity_list, user_dict)


# A list of functions that provide email notifications for users from different
# sources. Add to this list if you want to implement a new source of email
# notifications.
_notifications_functions = [
    _notifications_from_dashboard_activity_list,
]


def get_notifications(
    user_dict: dict[str, Any], since: datetime.datetime
) -> list[dict[str, Any]]:
    """Return any email notifications for the given user since `since`.

    For example email notifications about activity streams will be returned for
    any activities the occurred since `since`.

    :param user_dict: a dictionary representing the user, should contain 'id'
        and 'name'
    :type user_dict: dictionary

    :param since: datetime after which to return notifications from
    :rtype since: datetime.datetime

    :returns: a list of email notifications
    :rtype: list of dicts with keys 'subject' and 'body'

    """
    notifications = []
    for function in _notifications_functions:
        notifications.extend(function(user_dict, since))
    return notifications


def send_notification(
    user: dict[str, Any], email_dict: dict[str, Any]
) -> None:
    """Email `email_dict` to `user`."""
    import ckan.lib.mailer

    if not user.get("email"):
        # FIXME: Raise an exception.
        return

    try:
        ckan.lib.mailer.mail_recipient(
            user["display_name"],
            user["email"],
            email_dict["subject"],
            email_dict["body"],
        )
    except ckan.lib.mailer.MailerException:
        raise


def get_and_send_notifications_for_user(user: dict[str, Any]) -> None:

    # Parse the email_notifications_since config setting, email notifications
    # from longer ago than this time will not be sent.
    email_notifications_since = config.get(
        "ckan.email_notifications_since"
    )
    email_notifications_since = string_to_timedelta(email_notifications_since)
    email_notifications_since = (
        datetime.datetime.utcnow() - email_notifications_since
    )

    # FIXME: We are accessing model from lib here but I'm not sure what
    # else to do unless we add a get_email_last_sent() logic function which
    # would only be needed by this lib.
    dashboard = model.Dashboard.get(user["id"])
    if dashboard:
        email_last_sent = dashboard.email_last_sent
        activity_stream_last_viewed = dashboard.activity_stream_last_viewed
        since = max(
            email_notifications_since,
            email_last_sent,
            activity_stream_last_viewed,
        )

        notifications = get_notifications(user, since)
        # TODO: Handle failures from send_email_notification.
        for notification in notifications:
            send_notification(user, notification)

        # FIXME: We are accessing model from lib here but I'm not sure what
        # else to do unless we add a update_email_last_sent()
        # logic function which would only be needed by this lib.
        dashboard.email_last_sent = datetime.datetime.utcnow()
        model.repo.commit()


def get_and_send_notifications_for_all_users() -> None:
    context = cast(
        Context,
        {
            "model": model,
            "session": model.Session,
            "ignore_auth": True,
            "keep_email": True,
        },
    )
    users = logic.get_action("user_list")(context, {})
    for user in users:
        get_and_send_notifications_for_user(user)
