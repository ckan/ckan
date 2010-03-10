from core import *
from user import user_table, User
from group import group_table, Group, PackageGroup
from full_search import package_search_table
from authz import *
from extras import PackageExtra, package_extra_table, PackageExtraRevision
from resource import PackageResource, package_resource_table
from rating import *
from package_relationship import PackageRelationship

from pylons import config
import urllib2
import simplejson
class LicensesService(object):

    default_url = 'http://licenses.opendefinition.org/1.0/all_formatted'

    def get_names(self):
        url = config.get('licenses_service_url', self.default_url)
        print "Loading licenses from licenses service: %s" % url
        try:
            response = urllib2.urlopen(url)
            response_body = response.read()
        except Exception, inst:
            msg = "Couldn't connect to licenses service: %s" % inst
            raise Exception, msg
        try:
            license_names = simplejson.loads(response_body)
        except Exception, inst:
            msg = "Couldn't read response from licenses service: %s" % inst
            raise Exception, inst
        return [unicode(l) for l in license_names]

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
        try:
            licenses_service = LicensesService()
            license_names = licenses_service.get_names()
        except Exception, inst:
            msg = "Licenses service error: %s" % inst
            print msg
            print "Trying to import local licenses package..."
            try:
                from licenses import LicenseList
                license_names = LicenseList.all_formatted
            except Exception, inst:
                msg = "Couldn't load licenses package: %s" % inst
                raise Exception, msg
        print "Loaded %s licenses OK." % len(license_names)
        for name in license_names:
            if not License.by_name(name):
                l = License(name=name)
                Session.add(l)
        # assume if this exists everything else does too
        if not User.by_name(PSEUDO_USER__VISITOR):
            visitor = User(name=PSEUDO_USER__VISITOR)
            logged_in = User(name=PSEUDO_USER__LOGGED_IN)
            Session.add(visitor)
            Session.add(logged_in)
            # setup all role-actions
            # context is blank as not currently used
            # Note that Role.ADMIN can already do anything - hardcoded in.
            for role, action in default_role_actions:
                ra = RoleAction(role=role, context=u'',
                        action=action,)
                Session.add(ra)
        if Session.query(Revision).count() == 0:
            rev = Revision()
            rev.author = 'system'
            rev.message = u'Initialising the Repository'
            Session.add(rev)
        self.commit_and_remove()   

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
        versioned_objects=[Package, PackageTag, PackageResource]
        )


# Fix up Revision with project-specific attributes
def _get_packages(self):
    changes = repo.list_changes(self)
    pkgrevs = changes[Package]
    pkgtagrevs = changes[PackageTag]
    pkgresourcerevs = changes[PackageResource]
    pkgs  = [ p.continuity for p in pkgrevs ]
    pkgs += [ pkgtagrev.continuity.package for pkgtagrev in pkgtagrevs ]
    pkgs += [ pkgresourcerev.continuity.package for pkgresourcerev in
            pkgresourcerevs]
    # remove duplicates
    pkgs = list(set(pkgs))
    return pkgs

# could set this up directly on the mapper?
def _get_revision_user(self):
    username = unicode(self.author)
    user = Session.query(User).filter_by(name=username).first()
    return user

Revision.packages = property(_get_packages)
Revision.user = property(_get_revision_user)

def strptimestamp(s):
    import datetime, re
    return datetime.datetime(*map(int, re.split('[^\d]', s)))

def strftimestamp(t):
    return t.isoformat()

