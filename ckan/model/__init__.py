from core import *
from apikey import apikey_table, ApiKey
# from extras import Extra, extra_table

from licenses import LicenseList
license_names = LicenseList.all_formatted


class Repository(vdm.sqlalchemy.Repository):

    def init_db(self):
        super(Repository, self).init_db()
        for name in license_names:
            if not License.by_name(name):
                License(name=name)
        if Revision.query.count() == 0:
            rev = Revision()
            rev.author = 'system'
            rev.message = u'Initialising the Repository'
        self.commit_and_remove()

    def youngest_revision(self):
        return Revision.youngest()

repo = Repository(metadata, Session,
        versioned_objects=[Package, PackageTag]
        )


# Fix up Revision with a packages attribute
def _get_packages(self):
    changes = repo.list_changes(self)
    pkgrevs = changes[Package]
    return [ p.continuity for p in pkgrevs ]

Revision.packages = property(_get_packages)

