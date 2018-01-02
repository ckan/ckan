==============================
Migration from Pylons to Flask
==============================

On CKAN 2.6, work started to migrate from the Pylons web framework to a more
modern alternative, `Flask <http://flask.pocoo.org/>`_. This will be a gradual
process spanning multiple CKAN versions, where both the Pylons app and the
Flask app will live side by side with their own controllers or blueprints
which handle the incoming requests. The idea is that any other lower level code,
like templates, logic actions and authorization are shared between them as much
as possible. You can learn more about the approach followed and the work
already done on this page in the CKAN wiki:

https://github.com/ckan/ckan/wiki/Migration-from-Pylons-to-Flask

This page lists changes and deprecations that both core and extensions
developers should be aware of going forward, as well as common exceptions and
how to fix them.

-----------------------------------------------------------------------
Always import methods and objects from the plugins toolkit if available
-----------------------------------------------------------------------

This is a :ref:`good practice in general <use the plugins toolkit>` when
writing extensions but in the context of the Flask migration it becomes
specially important with these methods and objects::

    from ckan.plugins.toolkit import url_for, redirect_to, request, config

    url_for()
    redirect_to()
    request
    config

The reason is that these are actually wrappers provided by CKAN that will proxy
the call to the relevant Pylons or Flask underlying object or method depending
on who is handling the request. For instance in the ``config`` case, if you use
``pylons.config`` directly from your extension changes in configuration will
only be applied to the Pylons application, and the Flask application will be
misconfigured.

.. note:: ``config`` was added to the plugins toolkit on CKAN 2.6. If your
    extension needs to target CKAN versions lower and greater than CKAN 2.6 you
    can use `ckantoolkit <https://github.com/ckan/ckantoolkit>`, a separate
    package that provides wrappers for cross-version CKAN compatibility::

        from ckantoolkit import config
