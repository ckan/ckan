"""
Tests for plugin loading via PCA
"""
import os
from nose.tools import raises
from unittest import TestCase
from paste.deploy import appconfig, loadapp
from pyutilib.component.core import PluginGlobals
from pylons import config
from pkg_resources import working_set, Distribution, PathMetadata
from ckan import plugins
from ckan.config.middleware import make_app
from ckan.tests import conf_dir
from ckan.tests.mock_plugin import MockSingletonPlugin
from ckan.plugins.core import find_system_plugins
from ckan.plugins import Interface, implements
from ckan.lib.create_test_data import CreateTestData


def install_ckantestplugin():
    # Create the ckantestplugin setuptools distribution
    mydir = os.path.dirname(__file__)
    egg_info = os.path.join(mydir, 'ckantestplugin', 'ckantestplugin.egg-info')
    base_dir = os.path.dirname(egg_info)
    metadata = PathMetadata(base_dir, egg_info)
    dist_name = os.path.splitext(os.path.basename(egg_info))[0]
    ckantestplugin_dist = Distribution(
        base_dir, project_name=dist_name, metadata=metadata)
    working_set.add(ckantestplugin_dist)


class IFoo(Interface):
    pass

class IBar(Interface):
    pass

class FooImpl(object):
    implements(IFoo)

class BarImpl(object):
    implements(IBar)

class FooBarImpl(object):
    implements(IFoo)
    implements(IBar)

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

class TestIPluginObserverPlugin(TestCase):

    class PluginObserverPlugin(MockSingletonPlugin):
        from ckan.plugins import IPluginObserver
        implements(IPluginObserver)

    class OtherPlugin(MockSingletonPlugin):
        implements(IFoo)

    def setUp(self):
        plugins.unload_all()
        plugins.load(self.PluginObserverPlugin)
        self.PluginObserverPlugin().reset_calls()

    def test_notified_on_load(self):

        observer = self.PluginObserverPlugin()
        plugins.load(self.OtherPlugin)
        assert observer.before_load.calls == [((self.OtherPlugin,), {})]
        assert observer.after_load.calls == [((self.OtherPlugin(),), {})]
        assert observer.before_unload.calls == []
        assert observer.after_unload.calls == []

    def test_notified_on_unload(self):

        plugins.load(self.OtherPlugin)
        observer = self.PluginObserverPlugin()
        observer.reset_calls()

        plugins.unload(self.OtherPlugin)

        assert observer.before_load.calls == []
        assert observer.after_load.calls == []
        assert observer.before_unload.calls == [((self.OtherPlugin(),), {})], observer.before_unload.calls
        assert observer.after_unload.calls == [((self.OtherPlugin(),), {})]

class TestPlugins(TestCase):

    def setUp(self):
        self._saved_plugins_config = config.get('ckan.plugins', '')
        config['ckan.plugins'] = ''
        plugins.reset()
        install_ckantestplugin()

    def tearDown(self):
        # Ideally this would remove the ckantestplugin_dist from the working
        # set, but I can't find a way to do that in setuptools.
        plugins.unload_all()
        config['ckan.plugins'] = self._saved_plugins_config
        plugins.load_all(config)

    def test_plugins_load(self):

        config['ckan.plugins'] = 'mapper_plugin routes_plugin'
        plugins.load_all(config)

        # Imported after call to plugins.load_all to ensure that we test the
        # plugin loader starting from a blank slate.
        from ckantestplugin import MapperPlugin, MapperPlugin2, RoutesPlugin

        system_plugins = set(plugin() for plugin in find_system_plugins())
        assert PluginGlobals.env().services == set([MapperPlugin(), RoutesPlugin()]) | system_plugins

    def test_only_configured_plugins_loaded(self):

        config['ckan.plugins'] = 'mapper_plugin'
        plugins.load_all(config)

        from ckantestplugin import MapperPlugin, MapperPlugin2, RoutesPlugin
        from ckan.model.extension import PluginMapperExtension
        from ckan.config.routing import routing_plugins


        # MapperPlugin should be loaded as it is listed in config['ckan.plugins']
        assert MapperPlugin() in iter(PluginMapperExtension.observers)

        # MapperPlugin2 and RoutesPlugin should NOT be loaded
        assert MapperPlugin2() not in iter(PluginMapperExtension.observers)
        assert RoutesPlugin() not in routing_plugins

    def test_plugin_loading_order(self):
        """
        Check that plugins are loaded in the order specified in the config
        """
        from ckantestplugin import MapperPlugin, MapperPlugin2, PluginObserverPlugin

        observerplugin = PluginObserverPlugin()

        config['ckan.plugins'] = 'test_observer_plugin mapper_plugin mapper_plugin2'
        expected_order = MapperPlugin, MapperPlugin2

        plugins.load_all(config)
        assert observerplugin.before_load.calls == [((p,), {}) for p in expected_order]
        assert observerplugin.after_load.calls == [((p.__instance__,), {}) for p in (observerplugin,) + expected_order]

        config['ckan.plugins'] = 'test_observer_plugin mapper_plugin2 mapper_plugin'
        expected_order = MapperPlugin2, MapperPlugin
        observerplugin.reset_calls()

        plugins.load_all(config)
        assert observerplugin.before_load.calls == [((p,), {}) for p in expected_order]
        assert observerplugin.after_load.calls == [((p.__instance__,), {}) for p in (observerplugin,) + expected_order]

    def test_mapper_plugin_fired(self):
        config['ckan.plugins'] = 'mapper_plugin'
        plugins.load_all(config)
        CreateTestData.create_arbitrary([{'name':u'testpkg'}])
        mapper_plugin = PluginGlobals.plugin_registry['MapperPlugin'].__instance__
        assert len(mapper_plugin.added) == 2 # resource group table added automatically
        assert mapper_plugin.added[0].name == 'testpkg'

    def test_routes_plugin_fired(self):
        local_config = appconfig('config:%s' % config['__file__'], relative_to=conf_dir)
        local_config.local_conf['ckan.plugins'] = 'routes_plugin'
        app = make_app(local_config.global_conf, **local_config.local_conf)
        routes_plugin = PluginGlobals.plugin_registry['RoutesPlugin'].__instance__
        assert routes_plugin.calls_made == ['before_map', 'after_map'], \
               routes_plugin.calls_made

