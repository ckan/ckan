from ckan.plugins import SingletonPlugin, implements
from ckan.plugins import IMapper, IRoutes, IPluginObserver, IActions, IAuthFunctions
from ckan.tests.mock_plugin import MockSingletonPlugin


class MapperPlugin(SingletonPlugin):
    implements(IMapper, inherit=True)

    def __init__(self):
        self.added = []
        self.deleted = []

    def before_insert(self, mapper, conn, instance):
        self.added.append(instance)

    def before_delete(self, mapper, conn, instance):
        self.deleted.append(instance)

class MapperPlugin2(MapperPlugin):
    implements(IMapper)

class RoutesPlugin(SingletonPlugin):
    implements(IRoutes, inherit=True)

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

class ActionPlugin(SingletonPlugin):
    implements(IActions)

    def get_actions(self):
        return {'status_show': lambda context, data_dict: {}}

class AuthPlugin(SingletonPlugin):
    implements(IAuthFunctions)

    def get_auth_functions(self):
        return {'package_list': lambda context, data_dict: {}}

