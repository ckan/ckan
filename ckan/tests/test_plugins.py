"""
Tests for plugin loading via PCA
"""
from nose.tools import raises
from unittest import TestCase
from pyutilib.component.core import PluginGlobals
from pylons import config

import ckan.logic as logic
import ckan.new_authz as new_authz
import ckan.plugins as plugins
from ckan.plugins.core import find_system_plugins
from ckan.lib.create_test_data import CreateTestData


def _make_calls(*args):
    out = []
    for arg in args:
        out.append(((arg,), {}))
    return out


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

class TestInterface(TestCase):

    def test_implemented_by(self):
        assert IFoo.implemented_by(FooImpl)
        assert IFoo.implemented_by(FooBarImpl)
        assert not IFoo.implemented_by(BarImpl)

    @raises(TypeError)
    def test_implemented_by_raises_exception_on_instances(self):
        assert not IFoo.implemented_by(FooImpl())

    def test_provided_by(self):
        assert IFoo.provided_by(FooImpl())
        assert IFoo.provided_by(FooBarImpl())
        assert not IFoo.provided_by(BarImpl())

class TestIPluginObserverPlugin(object):


    @classmethod
    def setup(cls):
        cls.observer = plugins.load('test_observer_plugin')

    @classmethod
    def teardown(cls):
        plugins.unload('test_observer_plugin')

    def test_notified_on_load(self):

        observer = self.observer
        observer.reset_calls()
        with plugins.use_plugin('action_plugin') as action:
            assert observer.before_load.calls == _make_calls(action), observer.before_load.calls
            assert observer.after_load.calls == _make_calls(action), observer.after_load.calls
            assert observer.before_unload.calls == []
            assert observer.after_unload.calls == []

    def test_notified_on_unload(self):

        with plugins.use_plugin('action_plugin') as action:
            observer = self.observer
            observer.reset_calls()
        assert observer.before_load.calls == []
        assert observer.after_load.calls == []
        assert observer.before_unload.calls == _make_calls(action)
        assert observer.after_unload.calls == _make_calls(action)

class TestPlugins(object):


    def test_plugins_load(self):

        config_plugins = config['ckan.plugins']
        config['ckan.plugins'] = 'mapper_plugin routes_plugin'
        plugins.load_all(config)

        # synchronous_search automatically gets loaded
        current_plugins = set([plugins.get_plugin(p) for p in ['mapper_plugin', 'routes_plugin', 'synchronous_search'] + find_system_plugins()])
        assert PluginGlobals.env().services == current_plugins
        # cleanup
        config['ckan.plugins'] = config_plugins
        plugins.load_all(config)

    def test_only_configured_plugins_loaded(self):
        with plugins.use_plugin('mapper_plugin') as p:
            # MapperPlugin should be loaded as it is listed in
            assert p in plugins.PluginImplementations(plugins.IMapper)
            # MapperPlugin2 and RoutesPlugin should NOT be loaded
            assert len(plugins.PluginImplementations(plugins.IMapper)) == 1

    def test_plugin_loading_order(self):
        """
        Check that plugins are loaded in the order specified in the config
        """
        config_plugins = config['ckan.plugins']
        config['ckan.plugins'] = 'test_observer_plugin mapper_plugin mapper_plugin2'
        plugins.load_all(config)

        observerplugin = plugins.get_plugin('test_observer_plugin')

        expected_order = _make_calls(plugins.get_plugin('mapper_plugin'),
                                     plugins.get_plugin('mapper_plugin2'))
        assert observerplugin.before_load.calls[:-2] == expected_order
        expected_order = _make_calls(plugins.get_plugin('test_observer_plugin'),
                                     plugins.get_plugin('mapper_plugin'),
                                     plugins.get_plugin('mapper_plugin2'))
        assert observerplugin.after_load.calls[:-2] == expected_order

        config['ckan.plugins'] = 'test_observer_plugin mapper_plugin2 mapper_plugin'
        plugins.load_all(config)

        expected_order = _make_calls(plugins.get_plugin('mapper_plugin2'),
                                     plugins.get_plugin('mapper_plugin'))
        assert observerplugin.before_load.calls[:-2] == expected_order
        expected_order = _make_calls(plugins.get_plugin('test_observer_plugin'),
                                     plugins.get_plugin('mapper_plugin2'),
                                     plugins.get_plugin('mapper_plugin'))
        assert observerplugin.after_load.calls[:-2] == expected_order
        # cleanup
        config['ckan.plugins'] = config_plugins
        plugins.load_all(config)

    def test_mapper_plugin_fired(self):
        with plugins.use_plugin('mapper_plugin') as mapper_plugin:
            CreateTestData.create_arbitrary([{'name':u'testpkg'}])
            # remove this data
            CreateTestData.delete()
            assert len(mapper_plugin.added) == 2 # resource group table added automatically
            assert mapper_plugin.added[0].name == 'testpkg'

    def test_routes_plugin_fired(self):
        with plugins.use_plugin('routes_plugin'):
            routes_plugin = PluginGlobals.env_registry['pca'].plugin_registry['RoutesPlugin'].__instance__
            assert routes_plugin.calls_made == ['before_map', 'after_map'], \
                   routes_plugin.calls_made


    def test_action_plugin_override(self):
        status_show_original = logic.get_action('status_show')(None, {})
        with plugins.use_plugin('action_plugin'):
            assert logic.get_action('status_show')(None, {}) != status_show_original
        assert logic.get_action('status_show')(None, {}) == status_show_original

    def test_auth_plugin_override(self):
        package_list_original = new_authz.is_authorized('package_list', {})
        with plugins.use_plugin('auth_plugin'):
            assert new_authz.is_authorized('package_list', {}) != package_list_original
        assert new_authz.is_authorized('package_list', {}) == package_list_original

    @raises(plugins.PluginNotFoundException)
    def test_inexistent_plugin_loading(self):
        plugins.load('inexistent-plugin')
