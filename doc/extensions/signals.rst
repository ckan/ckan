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
one mandatory argument `sender` and arbitary number of keyword
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

.. warning:: Arguments passed to subscribers in no case should be
             modified. Use them only for doing some extra work and
             don't ever try to change existing CKAN behavior using
             subscribers. If one need to alter CKAN behavior,
             :mod:`ckan.plugins.interfaces` must be used instead.

There are a number of built-in signals in CKAN(listing available in
the end of the page). All of them are created inside one of the
available namespaces: ``ckan`` and ``ckanext``. For simplicity sake,
all built in signals have aliases inside ``ckan.lib.signals`` (or
``ckan.plugins.toolkit.signals``, or ``ckantoolkit.signals``), but you
always can get signals directly from corresponding namespace(though,
don't use this ability, unless you are familiar with ``blinker``
library)::

  from ckan.lib.signals import (
      ckan as ckan_namespace,
      register_blueprint, request_started
  )
  assert register_blueprint is ckan_namespace.signal('register_blueprint')
  assert request_started is ckan_namespace.signal('request_started')

This information may be quite handy, if you want to define custom
signals inside your extension. Just use ``ckanext`` namespace and call
its method ``signal`` in order to create new(or get existing)
signal. In order to avoid name collisions and unexpected behavior,
always use your plugin's name as prefix for the signal.::

  # ckanext-custom/ckanext/custom/signals.py
  import ckan.plugins.toolkit as tk

  # create signal and use it somewhere inside your extension
  custom_something_happened = tk.signals.ckanext.signal('custom_something_happened)

  # after this, you can notify subscribers using following code:
  custom_signal_happened.send(SENDER, ARG1=VALUE1, ARG2=VALUE2, ...)

Now, everyone, who are using your extension can subscirbe to your
signal from another extension::

  # ckanext-ext/ckanext/ext/plugin.py
  import ckan.plugins as p
  from ckanext.custom.signals import custom_something_happened
  from ckanext.ext import listeners # here you'll define listeners

  class ExtPlugin(p.SingletonPlugin):
      p.implements(p.ISignal)

      def get_signal_subscriptions(self):
          return {
              custom_something_happened: [
                  listeners.custom_listener
              ]
          }

There is a small problem in snippet above. If ``ckanext-custom`` is
not installed, you'll get ``ImportError``. This is perfectly fine if
you are sure that you are using ``ckanext-custom``, but may be a
problem for some general-use plugin. In order to avoid problem, either
use ``try/except`` block, or take signals from ``ckanext`` namespace
instead::

  # ckanext-ext/ckanext/ext/plugin.py
  import ckan.plugins as p
  from ckanext.ext import listeners # here you'll define listeners

  class ExtPlugin(p.SingletonPlugin):
      p.implements(p.ISignal)

      def get_signal_subscriptions(self):
          custom_something_happened = p.toolkit.signals.ckanext.signal(
              'custom_something_happened'
          )

          return {
              custom_something_happened: [
                  listeners.custom_listener
              ]
          }

All signals are singletons inside namespace and, if ``ckanext-custom``
is installed, you'll get existing signal, otherwise you'll create new
signal, that is never sent. I.e., your subscription will work only
when ``ckanext-custom`` available and do nothing(and don't consume
resources) otherwise.


:py:mod:`ckan.lib.signals` contains a few core signals for
plugins to subscribe:

.. currentmodule:: ckan.lib.signals

.. autodata:: request_started
   :annotation: (app)
.. autodata:: request_finished
   :annotation: (app, response)
.. autodata:: register_blueprint
   :annotation: (blueprint_type, blueprint)
.. autodata:: resource_download
   :annotation: (resource_id)
