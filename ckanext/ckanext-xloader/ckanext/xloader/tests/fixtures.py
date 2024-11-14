# -*- coding: utf-8 -*-
from sqlalchemy import orm
import os

from ckanext.datastore.tests import helpers as datastore_helpers
from ckanext.xloader.loader import get_write_engine

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__))
)

try:
    from ckan.tests.pytest_ckan.fixtures import *  # noqa
except ImportError:
    import pytest

    from ckan.tests import helpers as test_helpers
    import ckan.plugins
    import ckan.lib.search as search

    from ckan.common import config

    @pytest.fixture
    def ckan_config(request, monkeypatch):
        """Allows to override the configuration object used by tests

        Takes into account config patches introduced by the ``ckan_config``
        mark.

        If you just want to set one or more configuration options for the
        scope of a test (or a test class), use the ``ckan_config`` mark::

            @pytest.mark.ckan_config('ckan.auth.create_unowned_dataset', True)
            def test_auth_create_unowned_dataset():

                # ...

        To use the custom config inside a test, apply the
        ``ckan_config`` mark to it and inject the ``ckan_config`` fixture:

        .. literalinclude:: /../ckan/tests/pytest_ckan/test_fixtures.py
           :start-after: # START-CONFIG-OVERRIDE
           :end-before: # END-CONFIG-OVERRIDE

        If the change only needs to be applied locally, use the
        ``monkeypatch`` fixture

        .. literalinclude:: /../ckan/tests/test_common.py
           :start-after: # START-CONFIG-OVERRIDE
           :end-before: # END-CONFIG-OVERRIDE

        """
        _original = config.copy()
        for mark in request.node.iter_markers(u"ckan_config"):
            monkeypatch.setitem(config, *mark.args)
        yield config
        config.clear()
        config.update(_original)

    @pytest.fixture
    def make_app(ckan_config):
        """Factory for client app instances.

        Unless you need to create app instances lazily for some reason,
        use the ``app`` fixture instead.
        """
        return test_helpers._get_test_app

    @pytest.fixture
    def app(make_app):
        """Returns a client app instance to use in functional tests

        To use it, just add the ``app`` parameter to your test function signature::

            def test_dataset_search(self, app):

                url = h.url_for('dataset.search')

                response = app.get(url)


        """
        return make_app()

    @pytest.fixture(scope=u"session")
    def reset_db():
        """Callable for resetting the database to the initial state.

        If possible use the ``clean_db`` fixture instead.

        """
        return test_helpers.reset_db

    @pytest.fixture(scope=u"session")
    def reset_index():
        """Callable for cleaning search index.

        If possible use the ``clean_index`` fixture instead.
        """
        return search.clear_all

    @pytest.fixture
    def clean_db(reset_db):
        """Resets the database to the initial state.

        This can be used either for all tests in a class::

            @pytest.mark.usefixtures("clean_db")
            class TestExample(object):

                def test_example(self):

        or for a single test::

            class TestExample(object):

                @pytest.mark.usefixtures("clean_db")
                def test_example(self):

        """
        reset_db()

    @pytest.fixture
    def clean_index(reset_index):
        """Clear search index before starting the test.
        """
        reset_index()

    @pytest.fixture
    def with_plugins(ckan_config):
        """Load all plugins specified by the ``ckan.plugins`` config option
        at the beginning of the test. When the test ends (even it fails), it will
        unload all the plugins in the reverse order.

        .. literalinclude:: /../ckan/tests/test_factories.py
           :start-after: # START-CONFIG-OVERRIDE
           :end-before: # END-CONFIG-OVERRIDE

        """
        plugins = ckan_config["ckan.plugins"].split()
        for plugin in plugins:
            if not ckan.plugins.plugin_loaded(plugin):
                ckan.plugins.load(plugin)
        yield
        for plugin in reversed(plugins):
            if ckan.plugins.plugin_loaded(plugin):
                ckan.plugins.unload(plugin)

    @pytest.fixture
    def test_request_context(app):
        """Provide function for creating Flask request context.
        """
        return app.flask_app.test_request_context

    @pytest.fixture
    def with_request_context(test_request_context):
        """Execute test inside requests context
        """
        with test_request_context():
            yield


def reset_datastore_db():
    engine = get_write_engine()
    Session = orm.scoped_session(orm.sessionmaker(bind=engine))
    datastore_helpers.clear_db(Session)


@pytest.fixture()
def full_reset(reset_db):
    reset_db()
    reset_datastore_db()
