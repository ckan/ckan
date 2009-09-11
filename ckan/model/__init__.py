from core import *
from user import user_table, User
from group import group_table, Group
from authz import *
from extras import PackageExtra, package_extra_table

from licenses import LicenseList
license_names = LicenseList.all_formatted

import ckan.migration

# sqlalchemy migrate version table
import sqlalchemy.exceptions
try:
    version_table = Table('migrate_version', metadata, autoload=True)
except sqlalchemy.exceptions.NoSuchTableError:
    pass

class Repository(vdm.sqlalchemy.Repository):
    migrate_repository = ckan.migration.__path__[0]

    def init_db(self):
        super(Repository, self).init_db()
        for name in license_names:
            if not License.by_name(name):
                License(name=name)
        setup_default_role_actions()
        if Revision.query.count() == 0:
            rev = Revision()
            rev.author = 'system'
            rev.message = u'Initialising the Repository'
        self.commit_and_remove()   

    def youngest_revision(self):
        return Revision.youngest()

    def create_db(self):
        self.metadata.create_all(bind=self.metadata.bind)    
        # creation this way worked fine for normal use but failed on test with
        # OperationalError: (OperationalError) no such table: xxx
        # 2009-09-11 interesting all the tests will work if you run them after
        # doing paster db clean && paster db upgrade !
        # self.upgrade_db()
        self.setup_migration_version_control(self.latest_migration_version())

    def latest_migration_version(self):
        import migrate.versioning.api as mig
        version = mig.version(self.migrate_repository)
        return version

    def setup_migration_version_control(self, version=None):
        import migrate.versioning.exceptions
        import migrate.versioning.api as mig
        # set up db version control (if not already)
        try:
            mig.version_control(self.metadata.bind.url,
                    self.migrate_repository, version)
        except migrate.versioning.exceptions.DatabaseAlreadyControlledError:
            pass

    def upgrade_db(self, version=None):
        '''Upgrade db using sqlalchemy migrations.

        @param version: version to upgrade to (if None upgrade to latest)
        '''
        import migrate.versioning.api as mig
        self.setup_migration_version_control()
        mig.upgrade(self.metadata.bind.url, self.migrate_repository,
                version=version)



repo = Repository(metadata, Session,
        versioned_objects=[Package, PackageTag]
        )


# Fix up Revision with a packages attribute
def _get_packages(self):
    changes = repo.list_changes(self)
    pkgrevs = changes[Package]
    return [ p.continuity for p in pkgrevs ]

Revision.packages = property(_get_packages)

