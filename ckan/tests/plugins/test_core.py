# encoding: utf-8

import pytest
from ckan.common import config

import ckan.logic as logic
import ckan.authz as authz
import ckan.plugins as plugins
from ckan.plugins.core import find_system_plugins
from ckan.tests import factories


def _make_calls(*args):
    out = []
    for arg in args:
        out.append(((arg,), {}))
    return out


def get_calls(mock_observer_func):
    """Given a mock IPluginObserver method, returns the plugins that caused its
    methods to be called, so basically a list of plugins that
    loaded/unloaded"""
    return [call_tuple[0][0].name for call_tuple in mock_observer_func.calls]


class IFoo(plugins.Interface):
    pass


class IBar(plugins.Interface):
    pass


class FooImpl(object):
    plugins.implements(IFoo)


class BarImpl(object):
    plugins.implements(IBar)


class FooBarImpl(object):
    plugins.implements(IFoo)
    plugins.implements(IBar)


@pytest.mark.usefixtures(u"with_plugins")
@pytest.mark.ckan_config(
    u"ckan.plugins",
    u"example_idatasetform_v1 example_idatasetform_v2 example_idatasetform_v3")
def test_plugins_order_in_pluginimplementations():

    assert (
        [plugin.name for plugin in plugins.PluginImplementations(plugins.IDatasetForm)] ==
        [
            u"example_idatasetform_v1",
            u"example_idatasetform_v2",
            u"example_idatasetform_v3"
        ]
    )


@pytest.mark.usefixtures(u"with_plugins")
@pytest.mark.ckan_config(
    u"ckan.plugins",
    u"example_idatasetform_v1 example_idatasetform_v3 example_idatasetform_v2")
def test_plugins_order_in_pluginimplementations_matches_config():

    assert (
        [plugin.name for plugin in plugins.PluginImplementations(plugins.IDatasetForm)] ==
        [
            u"example_idatasetform_v1",
            u"example_idatasetform_v3",
            u"example_idatasetform_v2"
        ]
    )


def test_implemented_by():
    assert IFoo.implemented_by(FooImpl)
    assert IFoo.implemented_by(FooBarImpl)
    assert not IFoo.implemented_by(BarImpl)


def test_implemented_by_raises_exception_on_instances():
    with pytest.raises(TypeError):
        IFoo.implemented_by(FooImpl())


def test_provided_by():
    assert IFoo.provided_by(FooImpl())
    assert IFoo.provided_by(FooBarImpl())
    assert not IFoo.provided_by(BarImpl())


@pytest.fixture
def observer():
    observer = plugins.load("test_observer_plugin")
    try:
        observer.reset_calls()
        yield observer
    finally:
        plugins.unload("test_observer_plugin")


def test_notified_on_load(observer):
    with plugins.use_plugin("action_plugin"):
        assert get_calls(observer.before_load) == ["action_plugin"]
        assert get_calls(observer.after_load) == ["action_plugin"]
        assert get_calls(observer.before_unload) == []
        assert get_calls(observer.after_unload) == []


def test_notified_on_unload(observer):
    with plugins.use_plugin("action_plugin") as action:
        observer.reset_calls()
    assert observer.before_load.calls == []
    assert observer.after_load.calls == []
    assert observer.before_unload.calls == _make_calls(action)
    assert observer.after_unload.calls == _make_calls(action)


@pytest.fixture(autouse=True)
def reset_observer():
    plugins.load("test_observer_plugin")
    plugins.unload("test_observer_plugin")


def test_plugins_load(monkeypatch):
    monkeypatch.setitem(config, "ckan.plugins", "mapper_plugin routes_plugin")
    plugins.load_all()
    # synchronous_search automatically gets loaded
    current_plugins = set(
        [
            plugins.get_plugin(p)
            for p in ["mapper_plugin", "routes_plugin", "synchronous_search"]
            + find_system_plugins()
        ]
    )
    assert set(plugins.core._PLUGINS_SERVICE.values()) == current_plugins


@pytest.mark.ckan_config("ckan.plugins", "mapper_plugin")
@pytest.mark.usefixtures("with_plugins")
def test_only_configured_plugins_loaded():
    plugin = plugins.get_plugin("mapper_plugin")
    # MapperPlugin should be loaded as it is listed in
    assert plugin in plugins.PluginImplementations(plugins.IMapper)
    # MapperPlugin2 and RoutesPlugin should NOT be loaded
    assert len(plugins.PluginImplementations(plugins.IMapper)) == 1


@pytest.mark.ckan_config("ckan.plugins", "mapper_plugin")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_mapper_plugin_fired_on_insert():
    plugin = plugins.get_plugin("mapper_plugin")
    factories.Dataset(name="testpkg")
    assert plugin.calls == [
        ("before_insert", "testpkg"),
        ("after_insert", "testpkg"),
    ]


@pytest.mark.ckan_config("ckan.plugins", "mapper_plugin")
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
def test_mapper_plugin_fired_on_delete():
    plugin = plugins.get_plugin("mapper_plugin")
    factories.Dataset(name="testpkg")
    plugin.calls = []
    # remove this data
    user = factories.User()
    context = {"user": user["name"]}
    logic.get_action("package_delete")(context, {"id": "testpkg"})
    # state=deleted doesn't trigger before_delete()
    assert plugin.calls == []
    from ckan import model

    # purging the package does trigger before_delete()
    model.Package.get("testpkg").purge()
    model.Session.commit()
    model.Session.remove()
    assert plugin.calls == [
        ("before_delete", "testpkg"),
        ("after_delete", "testpkg"),
    ]


def test_action_plugin_override():
    status_show_original = logic.get_action("status_show")(None, {})
    with plugins.use_plugin("action_plugin"):
        assert (
            logic.get_action("status_show")(None, {}) != status_show_original
        )
    assert logic.get_action("status_show")(None, {}) == status_show_original


def test_auth_plugin_override():
    package_list_original = authz.is_authorized("package_list", {})
    with plugins.use_plugin("auth_plugin"):
        assert authz.is_authorized("package_list", {}) != package_list_original
    assert authz.is_authorized("package_list", {}) == package_list_original


def test_inexistent_plugin_loading():
    with pytest.raises(plugins.PluginNotFoundException):
        plugins.load("inexistent-plugin")


class TestPlugins:
    def teardown_method(self):
        plugins.unload_all()

    def test_plugin_loading_order(self):
        """
        Check that plugins are loaded in the order specified in the config
        """
        config_plugins = config["ckan.plugins"]
        config[
            "ckan.plugins"
        ] = "test_observer_plugin mapper_plugin mapper_plugin2"
        plugins.load_all()

        observerplugin = plugins.get_plugin("test_observer_plugin")

        expected_order = _make_calls(
            plugins.get_plugin("mapper_plugin"),
            plugins.get_plugin("mapper_plugin2"),
        )

        assert observerplugin.before_load.calls[:2] == expected_order
        expected_order = _make_calls(
            plugins.get_plugin("test_observer_plugin"),
            plugins.get_plugin("mapper_plugin"),
            plugins.get_plugin("mapper_plugin2"),
        )
        assert observerplugin.after_load.calls[:3] == expected_order

        config[
            "ckan.plugins"
        ] = "test_observer_plugin mapper_plugin2 mapper_plugin"
        plugins.load_all()

        expected_order = _make_calls(
            plugins.get_plugin("mapper_plugin2"),
            plugins.get_plugin("mapper_plugin"),
        )
        assert observerplugin.before_load.calls[:2] == expected_order
        expected_order = _make_calls(
            plugins.get_plugin("test_observer_plugin"),
            plugins.get_plugin("mapper_plugin2"),
            plugins.get_plugin("mapper_plugin"),
        )
        assert observerplugin.after_load.calls[:3] == expected_order
        # cleanup
        config["ckan.plugins"] = config_plugins
        plugins.load_all()
