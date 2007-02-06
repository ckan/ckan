import sqlobject
from sqlobject import *
from pylons.database import PackageHub
hub = PackageHub('ckan')
__connection__ = hub

from ckan.exceptions import *
from base import *


class Revision(sqlobject.SQLObject):

    author = sqlobject.UnicodeCol(default=None)
    log = sqlobject.UnicodeCol(default=None)
    date = sqlobject.DateTimeCol(default=None)
    # this is kind of nasty in that revision has to know about every kind of
    # object (really would like it the dependency to flow other way round ...)
    # i guess I am saying this should be in the model but that doesn't really
    # work
    package_revisions = sqlobject.MultipleJoin('PackageRevision')

    def _get_object_revisions(self):
        return self.package_revisions

    def commit(self, log=''):
        changed = self._get_object_revisions()
        if len(changed) == 0:
            raise EmptyRevisionException()
        self.log = log
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


class State(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)


# American spelling ...
class License(sqlobject.SQLObject):
    pass


class _Package(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)
    url = sqlobject.UnicodeCol(default=None)
    notes = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)
    open = sqlobject.BoolCol(default=True)
    state = sqlobject.ForeignKey('State', default=None)


class Package(_Package):

    revisions = sqlobject.MultipleJoin('PackageRevision',
        joinColumn='base_id')

    @classmethod
    def purge(self, id):
        pkg = Package.get(id)
        for rev in pkg.revisions:
            PackageRevision.delete(rev.id)
        Package.delete(id)


class PackageRevision(_Package):

    base = sqlobject.ForeignKey('Package')
    revision = sqlobject.ForeignKey('Revision')


class PackageRegistry(BaseRegistry):

    registry_object = Package
    registry_object_revision = PackageRevision

    def get(self, name, revision=None):
        """Get a package.

        TODO: ambiguity of meaning for revision argument. Does it mean get a
        package as it was at 'revision' OR make a new revision of this package
        using this revision (current usage)
        """
        base = self.registry_object.byName(name)
        if revision is None:
            return base
        else: # want to edit it
            kwargs = {}
            for key in base.sqlmeta.columns:
                value = getattr(base, key)
                kwargs[key] = value
            kwargs['base'] = base
            kwargs['revision'] = revision
            rev = self.registry_object_revision(**kwargs)
            return rev

