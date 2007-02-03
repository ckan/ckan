from sqlobject import *
from pylons.database import PackageHub
hub = PackageHub('ckan')
__connection__ = hub

from package import *

class DomainModel(object):

    # should be in order needed for creation
    classes = [ User, Revision, State, License, Package, PackageRevision ]

    packages = PackageRegistry()

    def begin_revision(self):
        return Revision()
    
    def create_tables(self):
        for cls in self.classes:
            cls.createTable(ifNotExists=True)

    def drop_tables(self):
        # cannot just use reversed as this operates in place
        size = len(self.classes)
        indices = range(size)
        indices.reverse()
        reversed = [ self.classes[xx] for xx in indices ]
        for cls in reversed:
            cls.dropTable(ifExists=True)
    
    def rebuild(self):
        self.drop_tables()
        self.create_tables()
        self.init()

    def init(self):
        State(name='active')
        State(name='deleted')

dm = DomainModel()
