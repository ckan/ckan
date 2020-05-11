# -*- coding: utf-8 -*-

import flask.signals
from blinker import Namespace

ckan = Namespace()
ckanext = Namespace()


request_started = flask.signals.request_started
"""This signal is sent when the request context is set up, before any
request processing happens.
"""


request_finished = flask.signals.request_finished
"""This signal is sent right before the response is sent to the
client.

"""

before_action = ckan.signal(u'before_action')
"""Action is about to be called.
"""

after_action = ckan.signal(u'after_action')
"""Action was successfully completed.
"""

register_blueprint = ckan.signal(u'register_blueprint')
"""Blueprint for dataset/resoruce/group/organization is going to be
registered inside application.
"""

resource_download = ckan.signal(u'resource_download')
"""File from uploaded resource will be sent to user.
"""
