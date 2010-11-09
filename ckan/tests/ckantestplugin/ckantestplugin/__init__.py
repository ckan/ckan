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

    def before_add(self, map):
        return map

