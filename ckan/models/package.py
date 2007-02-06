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
    pass


class Revision(sqlobject.SQLObject):

    author = sqlobject.UnicodeCol(default=None)
    log = sqlobject.UnicodeCol(default=None)
    date = sqlobject.DateTimeCol(default=datetime.now())

    packages = sqlobject.RelatedJoin('Package')


class Package(sqlobject.SQLObject):

    class sqlmeta:
        lazyUpdate = True

    name = sqlobject.UnicodeCol(alternateID=True)
    url = sqlobject.UnicodeCol(default=None)
    notes = sqlobject.UnicodeCol(default=None)
    license = sqlobject.ForeignKey('License', default=None)
    state = sqlobject.ForeignKey('State', default=None)

    revisions = sqlobject.RelatedJoin('Revision')

    def save(self, author=None, log=None):
        # TODO: wrap this in a transaction
        self.sync()
        rev = Revision(author=author, log=log)
        rev.addPackage(self)

class PackageRegistry(object):

    def get(self, name):
        return Package.byName(name)
    
    def create(self, revision_creator=None, log_message=None, **kwargs):
        """Create a new Package.

        @kwargs: standard name, value pairs for package attributes (as for
        Package(...)
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

