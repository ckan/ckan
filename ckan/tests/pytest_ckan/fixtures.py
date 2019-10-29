# -*- coding: utf-8 -*-
import pytest
import ckan.tests.helpers as test_helpers
import ckan.plugins
import ckan.lib.search as search
from ckan.common import config


@pytest.fixture
def ckan_config(request, monkeypatch):
    """Configuration object used by application.

    Takes into account config patches introduced by `ckan_config`
    mark.
    """
    _original = config.copy()
    for mark in request.node.own_markers:
        if mark.name == u"ckan_config":
            monkeypatch.setitem(config, *mark.args)
    yield config
    config.clear()
    config.update(_original)


@pytest.fixture
def make_app(ckan_config):
    """Factory for client app.

    Prefer using `app` instead if you have no need in lazy instantiation.
    """
    return test_helpers._get_test_app


@pytest.fixture
def app(make_app):
    """Instance of client app.
    """
    return make_app()


@pytest.fixture(scope=u"session")
def reset_db():
    """Callable for setting DB into initial state.
    """
    return test_helpers.reset_db


@pytest.fixture(scope=u"session")
def reset_index():
    """Callable for cleaning search index.
    """
    return search.clear_all


@pytest.fixture
def clean_db(reset_db):
    """Start test with database in initial state.
    """
    reset_db()


@pytest.fixture
def clean_index(reset_index):
    """Start test with empty index.
    """
    reset_index()


@pytest.fixture
def with_plugins(ckan_config):
    plugins = ckan_config["ckan.plugins"].split()
    for plugin in plugins:
        if not ckan.plugins.plugin_loaded(plugin):
            ckan.plugins.load(plugin)
    # ckan.plugins.load_all()
    yield
    for plugin in plugins:
        if ckan.plugins.plugin_loaded(plugin):
            ckan.plugins.unload(plugin)
    # ckan.plugins.unload_all()
