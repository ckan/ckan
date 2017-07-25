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


------------------------------------------------------------------------------
Wrap ``url_for`` calls in tests with a test request context (``RuntimeError``)
------------------------------------------------------------------------------

Starting from CKAN 2.8 you might get the following exception when running the
tests::

    RuntimeError: Attempted to generate a URL without the application context being
    pushed. This has to be executed when application context is available.

Users familiar with Flask may recognize this exception. Basically the Flask
router (called internally by ``ckan.lib.helpers.url_for``) requires you to be
in the context on a web request when calling it (You can learn more about this
in the `Flask documentation <http://flask.pocoo.org/docs/testing/>`_). What this
means is that a test like this will raise the above exception::

    from ckan.plugins.toolkit import url_for    
    from ckan.tests.helpers import FunctionalTestBase

    class TestSearch(FunctionalTestBase):

        def test_search_page_works(self):

            app = self._get_test_app()
            url = url_for(controller='package', action='search')              
            res = app.get(url)

To fix it, we need to wrap the ``url_for`` call with a test request context::

    from ckan.plugins.toolkit import url_for    
    from ckan.tests.helpers import FunctionalTestBase

    class TestSearch(FunctionalTestBase):

        def test_search_page_works(self):

            app = self._get_test_app()
            with app.flask_app.test_request_context():
                url = url_for(controller='package', action='search')              
            res = app.get(url)

If you are not extending ``FunctionalTestBase`` you can get an instance of the
test app client in order to create the test request context::

    from ckan.plugins.toolkit import url_for
    from ckan.tests.helpers import _get_test_app

    class TestSearch(object):
        def test_search_page_works(self):

            app = _get_test_app()
            with app.flask_app.test_request_context():
                url = url_for(controller='package', action='search')              
            res = app.get(url)

Note that the call to ``url_for`` might not be explicitly done in the test
itself but rather internally. For instance consider the following example::


    from ckan.tests.helpers import FunctionalTestBase

    class TestDatastore(FunctionalTestBase):

        def test_create_datastore_only_view(self):
            # ...
            # datastore_create will call ``url_for`` internally (or trigger
            # something that calls it) so we need a Flask test context
            with self.app.flask_app.test_request_context():
                result = helpers.call_action('datastore_create', **data)

Or this one::

    import ckan.lib.dictization.model_dictize as model_dictize
    from ckan.tests.helpers import _get_test_app

    class TestDictize(object):

        def test_resource_dictize(self):
            # Internally resource_dictize calls ``url_for`` so we need a test context
            app = helpers._get_test_app()
            with app.flask_app.test_request_context():
                resource_dict = model_dictize.resource_dictize(...)
