# -*- coding: utf-8 -*-
"""This is a collection of pytest fixtures for use in tests.

All fixtures bellow available anywhere under the root of CKAN
repository. Any external CKAN extension should be able to include them
by adding next lines under root `conftest.py`

.. literalinclude:: /../conftest.py

There are three type of fixtures available in CKAN:

* Fixtures that have some side-effect. They don't return any useful
  value and generally should be injected via
  ``pytest.mark.usefixtures``. Ex.: `with_plugins`, `clean_db`,
  `clean_index`.

* Fixtures that provide value. Ex. `app`

* Fixtures that provide factory function. They are rarely needed, so
  prefer using 'side-effect' or 'value' fixtures. Main use-case when
  one may use function-fixture - late initialization or repeatable
  execution(ex.: cleaning database more than once in a single
  test). But presence of these fixtures in test usually signals that
  is's a good time to refactor this test.

Deeper expanation can be found in `official documentation
<https://docs.pytest.org/en/latest/fixture.html>`_

"""

import functools
import smtplib


import pytest
import six
import mock
import rq

import ckan.tests.helpers as test_helpers
import ckan.plugins
import ckan.cli
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


@pytest.fixture
def cli(ckan_config):
    """Provides object for invoking CLI commands from tests.

    This is subclass of `click.testing.CliRunner`, so all examples
    from `Click docs
    <https://click.palletsprojects.com/en/master/testing/>`_ are valid
    for it.

    """
    env = {
        u'CKAN_INI': ckan_config[u'__file__']
    }
    return test_helpers.CKANCliRunner(env=env)


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


@pytest.fixture
def mail_server(monkeypatch):
    """Catch all outcome mails.
    """
    bag = test_helpers.FakeSMTP()
    monkeypatch.setattr(smtplib, u"SMTP", bag)
    yield bag


@pytest.fixture
def with_test_worker(monkeypatch):
    """Worker that doesn't create forks.
    """
    if six.PY3:
        monkeypatch.setattr(
            rq.Worker, u"main_work_horse", rq.SimpleWorker.main_work_horse
        )
        monkeypatch.setattr(
            rq.Worker, u"execute_job", rq.SimpleWorker.execute_job
        )
    yield


@pytest.fixture
def with_extended_cli(ckan_config, monkeypatch):
    """Enables effects of IClick.

    Without this fixture, only CLI command that came from plugins
    specified in real config file are available. When this fixture
    enabled, changing `ckan.plugins` on test level allows to update
    list of available CLI command.

    """
    # Main `ckan` command is initialized from config file instead of
    # using global config object.  With this patch it becomes possible
    # to apply per-test config changes to it without creating real
    # config file.
    def fake_load_config(ini_path=None, setup_logging=True):
        return ckan_config
    monkeypatch.setattr(ckan.cli, u'load_config', fake_load_config)
