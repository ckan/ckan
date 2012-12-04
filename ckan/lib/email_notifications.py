'''
Code for generating email notifications for users (e.g. email notifications for
new activities in your dashboard activity stream) and emailing them to the
users.

'''
import datetime

import ckan.model as model
import ckan.logic as logic


def _notifications_for_activities(activities):
    '''Return one or more email notifications covering the given activities.

    This function handles grouping multiple activities into a single digest
    email.

    :param activities: the activities to consider
    :type activities: list of activity dicts like those returned by
        ckan.logic.action.get.dashboard_activity_list()

    :returns: a list of email notifications
    :rtype: list of dicts each with keys 'subject' and 'body'

    '''
    if not activities:
        return []

    # We just group all activities into a single "new activity" email that
    # doesn't say anything about _what_ new activities they are.
    # TODO: Here we could generate some smarter content for the emails e.g.
    # say something about the contents of the activities, or single out
    # certain types of activity to be sent in their own individual emails,
    # etc.
    notifications = [{
        'subject': "You have new activity",
        'body': "You have new activity"
        }]

    return notifications


def _notifications_from_dashboard_activity_list(user_id, since):
    '''Return any email notifications from user_id's dashboard activity list
    since `since`.

    '''
    # Get the user's dashboard activity stream.
    context = {'model': model, 'session': model.Session, 'user': user_id}
    activity_list = logic.get_action('dashboard_activity_list')(context, {})

    # Filter out the user's own activities., so they don't get an email every
    # time they themselves do something (we are not Trac).
    activity_list = [activity for activity in activity_list
            if activity['user_id'] != user_id]

    # Filter out the old activities.
    strptime = datetime.datetime.strptime
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    activity_list = [activity for activity in activity_list
            if strptime(activity['timestamp'], fmt) > since]

    return _notifications_for_activities(activity_list)


# A list of functions that provide email notifications for users from different
# sources. Add to this list if you want to implement a new source of email
# notifications.
_notifications_functions = [
    _notifications_from_dashboard_activity_list,
    ]


def get_notifications(user_id, since):
    '''Return any email notifications for `user_id` since `since`.

    For example email notifications about activity streams will be returned for
    any activities the occurred since `since`.

    :param user_id: id of the user to return notifications for
    :type user_id: string

    :param since: datetime after which to return notifications from
    :rtype since: datetime.datetime

    :returns: a list of email notifications
    :rtype: list of dicts with keys 'subject' and 'body'

    '''
    notifications = []
    for function in _notifications_functions:
        notifications.extend(function(user_id, since))
    return notifications


def send_notification(user, email_dict):
    '''Email `email_dict` to `user`.'''
    import ckan.lib.mailer

    if not user.get('email'):
        # FIXME: Raise an exception.
        return

    try:
        ckan.lib.mailer.mail_recipient(user['display_name'], user['email'],
                email_dict['subject'], email_dict['body'])
    except ckan.lib.mailer.MailerException:
        raise


def get_and_send_notifications_for_user(user):

    if user['email_notifications']:

        # FIXME: We are accessing model from lib here but I'm not sure what
        # else to do unless we add a get_email_last_sent() logic function which
        # would only be needed by this lib.
        email_last_sent = model.Dashboard.get(user['id']).email_last_sent
        activity_stream_last_viewed = (
                model.Dashboard.get(user['id']).activity_stream_last_viewed)
        since = max(email_last_sent, activity_stream_last_viewed)

        notifications = get_notifications(user['id'], since)

        # TODO: Handle failures from send_email_notification.
        for notification in notifications:
            send_notification(user, notification)

    # Whether the user had har 'email_notifications' preference turned on or
    # not, we still update her email_last_sent time. This prevents users from
    # getting emails about old activities when they turn on email
    # notifications.
    # FIXME: We are accessing model from lib here but I'm not sure what
    # else to do unless we add a update_email_last_sent()
    # logic function which would only be needed by this lib.
    dash = model.Dashboard.get(user['id'])
    dash.email_last_sent = datetime.datetime.now()
    model.repo.commit()


def get_and_send_notifications_for_all_users():
    context = {'model': model, 'session': model.Session, 'ignore_auth': True,
            'keep_sensitive_data': True}
    users = logic.get_action('user_list')(context, {})
    for user in users:
        get_and_send_notifications_for_user(user)
