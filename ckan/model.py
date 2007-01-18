import sqlobject
import ckan.config
cfg = ckan.config.Config()
connection = sqlobject.connectionForURI(cfg.db_uri)
sqlobject.sqlhub.processConnection = connection


class PdwException(Exception):
    pass

class EmptyRevisionException(PdwException):
    pass

class User(sqlobject.SQLObject):
    pass

class Revision(sqlobject.SQLObject):

    message = sqlobject.UnicodeCol(default=None)
    # this is kind of nasty in that revision has to know about every kind of
    # object (really would like it the dependency to flow other way round ...)
    # i guess I am saying this should be in the model but that doesn't really
    # work
    package_revisions = sqlobject.MultipleJoin('PackageRevision')

    def _get_object_revisions(self):
        return self.package_revisions

    def commit(self, message=''):
        changed = self._get_object_revisions()
        if len(changed) == 0:
            raise EmptyRevisionException()
        self.message = message
        for object in changed:
            # TODO: locks
            for revobj in changed: 
                self._commit_changes_to_base_object(revobj)
            # TODO: remove locks

    def _commit_changes_to_base_object(self, revobj):
        baseobj = revobj.base 
        for key in revobj.sqlmeta.columns:
            if key not in ['base', 'revision']:
                value = getattr(revobj, key)
                setattr(baseobj, key, value)

class BaseRegistry(object):

    # domain object to which this registry relates
    registry_object = None
    # ditto but for the revison of the object 
    registry_object_revision = None

    def create(self, revision, **kwargs):
        base = self.registry_object(**kwargs)
        kwargs['base'] = base 
        kwargs['revision'] = revision
        rev = self.registry_object_revision(**kwargs)
        return rev


# American spelling ...
class License(sqlobject.SQLObject):
    pass

class Package(sqlobject.SQLObject):

    title = sqlobject.UnicodeCol()
    url = sqlobject.UnicodeCol(default=None)
    notes = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)
    open = sqlobject.BoolCol(default=True)
    # state = 

class PackageRevision(Package):

    base = sqlobject.ForeignKey('Package')
    revision = sqlobject.ForeignKey('Revision')

class PackageRegistry(BaseRegistry):

    registry_object = Package
    registry_object_revision = PackageRevision



class DomainModel:

    # should be in order needed for creation
    classes = [ Revision, License, Package, PackageRevision ]

    packages = PackageRegistry()

    def begin_revision(self):
        return Revision()
    
    @classmethod
    def create_tables(self):
        for cls in self.classes:
            cls.createTable(ifNotExists=True)

    @classmethod
    def drop_tables(self):
        # cannot just use reversed as this operates in place
        size = len(self.classes)
        indices = range(size)
        indices.reverse()
        reversed = [ self.classes[xx] for xx in indices ]
        for cls in reversed:
            cls.dropTable(ifExists=True)
    
    @classmethod
    def rebuild(self):
        self.drop_tables()
        self.create_tables()
        self.init()

    @classmethod
    def init(self):
        pass


