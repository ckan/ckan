# -*- coding: utf-8 -*-
"""Contains ``ckan`` and ``ckanext`` namespaces for signals as well as a bunch
of predefined core-level signals.

Check :doc:`signals` for extra detais.

"""

from typing import Any
import flask.signals
from blinker import Namespace

ckan = Namespace()
ckanext = Namespace()


def _request_finished_listener(*args: Any, **kwargs: Any):
    request_finished.send(*args, **kwargs)


flask.signals.request_finished.connect(_request_finished_listener)


def _request_started_listener(*args: Any, **kwargs: Any):
    request_started.send(*args, **kwargs)


flask.signals.request_started.connect(_request_started_listener)


request_started = ckan.signal(u"request_started")
"""This signal is sent when the request context is set up, before any
request processing happens.
"""


request_finished = ckan.signal(u"request_finished")
"""This signal is sent right before the response is sent to the
client.
"""


register_blueprint = ckan.signal(u"register_blueprint")
"""This signal is sent when a blueprint for dataset/resource/group/organization
is going to be registered inside the application.
"""


resource_download = ckan.signal(u"resource_download")
"""This signal is sent just before a file from an uploaded resource is sent
to the user.
"""

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
