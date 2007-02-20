import sqlobject
from sqlobject import *
from pylons.database import PackageHub
hub = PackageHub('ckan')
__connection__ = hub

from ckan.exceptions import *
from datetime import datetime

class State(sqlobject.SQLObject):

    name = sqlobject.UnicodeCol(alternateID=True)


# American spelling ...
class License(sqlobject.SQLObject):

    class sqlmeta:
        _defaultOrder = 'name'

    name = sqlobject.UnicodeCol(alternateID=True)

    packages = sqlobject.RelatedJoin('Package',
            createRelatedTable=False,
            intermediateTable='package_license'
            )


class Revision(sqlobject.SQLObject):

    author = sqlobject.UnicodeCol(default=None)
    log = sqlobject.UnicodeCol(default=None)
    date = sqlobject.DateTimeCol(default=datetime.now())

    packages = sqlobject.RelatedJoin('Package')


class Tag(sqlobject.SQLObject):

    class sqlmeta:
        _defaultOrder = 'name'

    name = sqlobject.UnicodeCol(alternateID=True)
    created = sqlobject.DateTimeCol(default=datetime.now())

    packages = sqlobject.RelatedJoin('Package',
            createRelatedTable=False,
            intermediateTable='package_tag'
            )

class Package(sqlobject.SQLObject):

    class sqlmeta:
        lazyUpdate = True
        _defaultOrder = 'name'

    name = sqlobject.UnicodeCol(alternateID=True)
    url = sqlobject.UnicodeCol(default=None)
    notes = sqlobject.UnicodeCol(default=None)
    state = sqlobject.ForeignKey('State', default=None)

    revisions = sqlobject.RelatedJoin('Revision')
    licenses = sqlobject.RelatedJoin('License',
            createRelatedTable=False,
            intermediateTable='package_license'
            )
    tags = sqlobject.RelatedJoin('Tag',
            createRelatedTable=False,
            intermediateTable='package_tag'
            )

    def add_tag_by_name(self, tag_name):
        try:
            tag = Tag.byName(tag_name)
        except sqlobject.SQLObjectNotFound:
            tag = Tag(name=tag_name)
        self.addTag(tag)

    def save(self, author=None, log=None):
        # TODO: ? check sqlmeta.dirty to see if anything needs to be done
        # TODO: wrap this in a transaction
        self.syncUpdate()
        rev = Revision(author=author, log=log)
        rev.addPackage(self)


# cannot use simple RelatedJoin because SQLObject does not cascade
class PackageLicense(sqlobject.SQLObject):

    package = sqlobject.ForeignKey('Package', cascade=True)
    license = sqlobject.ForeignKey('License', cascade=True)


# cannot use simple RelatedJoin because SQLObject does not cascade
class PackageTag(sqlobject.SQLObject):

    package = sqlobject.ForeignKey('Package', cascade=True)
    tag = sqlobject.ForeignKey('Tag', cascade=True)


class PackageRegistry(object):

    def get(self, name):
        return Package.byName(name)
    
    def create(self, revision_creator=None, log_message=None, **kwargs):
        """Create a new Package.

        @kwargs: standard name, value pairs for package attributes (as for
        Package(...)
        TODO: add create_revision option
        """
        rev = Revision(author=revision_creator,
                log=log_message)
        pkg = Package(**kwargs)
        rev.addPackage(pkg)
        return pkg

    def purge(self, name):
        pkg = Package.byName(name)
        for rev in pkg.revisions:
            pkg.removeRevision(rev)
            Revision.delete(rev.id)
        Package.delete(pkg.id)

