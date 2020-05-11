Signals
=======

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


:mod:`ckan.lib.signals` provides two namespaces for signals: ``ckan``
and ``ckanext``. All core signals resides in ``ckan``, while signals
from extensions (``datastore``, ``datapusher``, third-party
extensions) are registered under ``ckanext``. It's only a
recommendation and nothing prevents developers from creating and using
their own namespaces.

Signal subscribers **MUST** always be defined as callable accepting
one mandatory argument `sender` and arbinary number of keyword
arguments::

    def subscriber(sender, **kwargs):
        ...

CKAN core doesn't make any guarantees as for concrete named arguments
that will be passed to subscriber. For particular CKAN version one can
use signlal-listing below as a reference, but in future versions
signature may change. In additon, any event can be fired by
third-party plugin, so it would be safer to check whether particular
argument is available inisde `kwargs`.

Even though it possible to register subscribers using decorators::

    @p.toolkit.signals.before_action.connect
    def action_subscriber(sender, **kwargs):
        pass

recommended approach is using
:class:`ckan.plugins.interfaces.ISignal`, in order to give CKAN more
control over subscriptions available depending on enabled plugins::

    class ExampleISignalPlugin(p.SingletonPlugin):
        p.implements(p.ISignal)

        def get_signal_subscriptions(self):
            return {
                p.toolkit.signals.before_action: [
                    # when subscribing to every signal of type
                    action_subscriber,

                    # when subscribing to signals from particular sender
                    {u'receiver': action_subscriber, u'sender': 'sender_name'}
                ]
            }

.. warning:: Arguments passed to subscribers in no case should be modified. Use them only for doing some extra work and don't ever try to change existing CKAN behavior using subscribers. If one need to alter CKAN behavior, :mod:`ckan.plugins.interfaces` must be used instead.

:py:mod:`ckan.lib.signals` contains a few core signals for
plugins to subscribe:

.. currentmodule:: ckan.lib.signals

.. autodata:: request_started
   :annotation: (app)
.. autodata:: request_finished
   :annotation: (app, response)
.. autodata:: before_action
   :annotation: (action_name, context, data_dict)
.. autodata:: after_action
   :annotation: (action_name, result)
.. autodata:: register_blueprint
   :annotation: (blueprint_type, blueprint)
.. autodata:: resource_download
   :annotation: (resource_id)
