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

import pytest
import ckan.tests.helpers as test_helpers
import ckan.plugins
import ckan.lib.search as search
from ckan.common import config


@pytest.fixture
def ckan_config(request, monkeypatch):
    """Configuration object used by application.

    Takes into account config patches introduced by `ckan_config`
    mark.  For using custom config in the whole test, apply
    `ckan_config` mark to it and inject `ckan_config` fixture:

    .. literalinclude:: /../ckan/tests/pytest_ckan/test_fixtures.py
       :start-after: # START-CONFIG-OVERRIDE
       :end-before: # END-CONFIG-OVERRIDE

    Otherwise, when change only need to be applied locally, use
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
    """Factory for client app.

    Prefer using ``app`` instead if you have no need in lazy instantiation.
    """
    return test_helpers._get_test_app


@pytest.fixture
def app(make_app):
    """Instance of client app.
    """
    return make_app()


@pytest.fixture(scope=u"session")
def reset_db():
    """Callable for setting DB into initial state. Prefer using
    ``clean_db``.

    """
    return test_helpers.reset_db


@pytest.fixture(scope=u"session")
def reset_index():
    """Callable for cleaning search index. Prefer using ``clean_index``.

    """
    return search.clear_all


@pytest.fixture
def clean_db(reset_db):
    """Start test with database in initial state.
    """
    reset_db()


@pytest.fixture
def clean_index(reset_index):
    """Start test with empty search index.
    """
    reset_index()


@pytest.fixture
def with_plugins(ckan_config):
    """Load all plugins specified by ``ckan.plugins`` config option in the
    beginning of the test. When test ends (event with fail) unload all
    those plugins in reverse order.

    .. literalinclude:: /../ckan/tests/test_factories.py
       :start-after: # START-CONFIG-OVERRIDE
       :end-before: # END-CONFIG-OVERRIDE

    """
    plugins = ckan_config["ckan.plugins"].split()
    for plugin in plugins:
        if not ckan.plugins.plugin_loaded(plugin):
            ckan.plugins.load(plugin)
    # ckan.plugins.load_all()
    yield
    for plugin in reversed(plugins):
        if ckan.plugins.plugin_loaded(plugin):
            ckan.plugins.unload(plugin)
    # ckan.plugins.unload_all()
