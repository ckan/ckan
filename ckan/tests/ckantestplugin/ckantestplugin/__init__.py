from ckan.plugins import SingletonPlugin, IMapperExtension, IRoutesExtension, implements

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

    def before_add(self, map):
        self.calls_made.append('before_add')
        return map

    def after_add(self, map):
        self.calls_made.append('after_add')
        return map
