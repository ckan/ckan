# -*- coding: utf-8 -*-

import flask.signals
from blinker import Namespace

ckan = Namespace()
ckanext = Namespace()


@flask.signals.request_finished.connect
def _request_finished_listener(*args, **kwargs):
    request_finished.send(*args, **kwargs)


@flask.signals.request_started.connect
def _request_started_listener(*args, **kwargs):
    request_started.send(*args, **kwargs)


request_started = ckan.signal(u'request_started')
"""This signal is sent when the request context is set up, before any
request processing happens.
"""


request_finished = ckan.signal(u'request_finished')
"""This signal is sent right before the response is sent to the
client.
"""


register_blueprint = ckan.signal(u'register_blueprint')
"""This signal is sent when a blueprint for dataset/resource/group/organization
is going to be registered inside the application.
"""


resource_download = ckan.signal(u'resource_download')
"""This signal is sent just before a file from an uploaded resource is sent
to the user.
"""
