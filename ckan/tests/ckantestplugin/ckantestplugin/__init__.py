from ckan.plugins import SingletonPlugin, implements
from ckan.plugins import IMapperExtension, IRoutesExtension, IPluginObserver
from ckan.tests.mock_plugin import MockSingletonPlugin


class MapperPlugin(SingletonPlugin):
    implements(IMapperExtension, inherit=True)

    def __init__(self):
        self.added = []
        self.deleted = []

    def before_insert(self, mapper, conn, instance):
        self.added.append(instance)

    def before_delete(self, mapper, conn, instance):
        self.deleted.append(instance)

class MapperPlugin2(MapperPlugin):
    implements(IMapperExtension)

class RoutesPlugin(SingletonPlugin):
    implements(IRoutesExtension, inherit=True)

    def __init__(self):
        self.calls_made = []

    def before_map(self, map):
        self.calls_made.append('before_map')
        return map

    def after_map(self, map):
        self.calls_made.append('after_map')
        return map
    
class PluginObserverPlugin(MockSingletonPlugin):
    implements(IPluginObserver)
