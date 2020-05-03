# -*- coding: utf-8 -*-
"""
Starting v3.0, CKAN comes with built-in signal support, provided by
`blinker <https://pythonhosted.org/blinker/>`_.

The same library is used by `Flask
<https://flask.palletsprojects.com/en/1.1.x/signals/>`_ and anything
written in Flask docs also applies to CKAN. Probably, the most
important point:

.. note:: Flask comes with a couple of signals and other extensions
    might provide more. Also keep in mind that signals are intended to
    notify subscribers and should not encourage subscribers to modify
    data. You will notice that there are signals that appear to do the
    same thing like some of the builtin decorators do (eg:
    request_started is very similar to before_request()). However,
    there are differences in how they work. The core before_request()
    handler, for example, is executed in a specific order and is able
    to abort the request early by returning a response. In contrast
    all signal handlers are executed in undefined order and do not
    modify any data.


Example::

    class ExampleISignalPlugin(p.SingletonPlugin):
        p.implements(p.ISignal)

        def get_signal_subscriptions(self):
            return {
                p.toolkit.signals.before_action: [action_subscriber],
                p.toolkit.signals.ckanext.signal(u'custom_signal'): [
                    custom_subscriber,
                    {u'receiver': custom_subscriber_for_xxx, u'sender': 'xxx'}
                ]
            }


:py:mod:`ckan.lib.signals` contains a few core signals for
plugins to subscribe:

.. autodata:: before_action
   :annotation: (action_name, context, data_dict)
.. autodata:: after_action
   :annotation: (action_name, result)
.. autodata:: register_blueprint
   :annotation: (blueprint_type, blueprint)
.. autodata:: resource_download
   :annotation: (resource_id)
.. autodata:: login_fail
   :annotation: (remote_address)

"""
from blinker import Namespace

ckan = Namespace()
ckanext = Namespace()


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

login_fail = ckan.signal(u'login_fail')
"""Login failed because of incorrect credentials.
"""
