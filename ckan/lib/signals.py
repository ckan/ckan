# -*- coding: utf-8 -*-
"""Contains ``ckan`` and ``ckanext`` namespaces for signals as well as a bunch
of predefined core-level signals.

Check :doc:`signals` for extra details.

"""

import flask.signals
import flask_login.signals
from blinker import Namespace

ckan = Namespace()
ckanext = Namespace()

request_started = ckan.signal(u"request_started")
"""This signal is sent when the request context is set up, before any
request processing happens.
"""
flask.signals.request_started.connect(request_started.send)

request_finished = ckan.signal(u"request_finished")
"""This signal is sent right before the response is sent to the
client.
"""
flask.signals.request_finished.connect(request_finished.send)

register_blueprint = ckan.signal(u"register_blueprint")
"""This signal is sent when a blueprint for dataset/resource/group/organization
is going to be registered inside the application.
"""

resource_download = ckan.signal(u"resource_download")
"""This signal is sent just before a file from an uploaded resource is sent
to the user.
"""

user_logged_in = ckan.signal(u"logged_in")
""" Sent when a user is logged in.
"""
flask_login.signals.user_logged_in.connect(user_logged_in.send)

user_logged_out = ckan.signal(u"logged_out")
"""Sent when a user is logged out
"""
flask_login.signals.user_logged_out.connect(user_logged_out.send)

failed_login = ckan.signal(u"failed_login")
"""This signal is sent after failed login attempt.
"""

user_created = ckan.signal(u"user_created")
"""This signal is sent when new user created.
"""

request_password_reset = ckan.signal(u"request_password_reset")
"""This signal is sent just after mail with password reset link sent
to user.
"""

perform_password_reset = ckan.signal(u"perform_password_reset")
"""This signal is sent when user submitted password reset form
providing new password.

"""

action_succeeded = ckan.signal(u"action_succeed")
"""This signal is sent when an action finished without an exception.
"""

datastore_upsert = ckanext.signal(u"datastore_upsert")
"""This signal is sent after datasetore records inserted/updated via
`datastore_upsert`.

"""

datastore_delete = ckanext.signal(u"datastore_delete")
"""This signal is sent after successful call to `datastore_delete`.

"""
