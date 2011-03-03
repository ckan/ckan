import warnings
from pylons import config
from sqlalchemy import MetaData, __version__ as sqav
from sqlalchemy.schema import Index
from paste.deploy.converters import asbool

import meta
from domain_object import DomainObjectOperation
from core import *
from package import *
from tag import *
from package_mapping import *
from user import user_table, User
from authorization_group import * 
from group import *
from group_extra import *
from search_index import *
from authz import *
from package_extra import *
from resource import *
from rating import *
from package_relationship import *
from changeset import Changeset, Change, Changemask
from harvesting import HarvestSource, HarvestingJob, HarvestedDocument
import ckan.migration

# set up in init_model after metadata is bound
version_table = None

def init_model(engine):
    '''Call me before using any of the tables or classes in the model'''
    meta.Session.configure(bind=engine)
    meta.engine = engine
    meta.metadata.bind = engine
    # sqlalchemy migrate version table
    import sqlalchemy.exceptions
    try:
        version_table = Table('migrate_version', metadata, autoload=True)
    except sqlalchemy.exceptions.NoSuchTableError:
        pass



class Repository(vdm.sqlalchemy.Repository):
    migrate_repository = ckan.migration.__path__[0]

    tables_created = False

    def init_db(self):
        '''Ensures tables, const data and some default config is created.
        This method MUST be run before using CKAN for the first time.
        Before this method is run, you can either have a clean db or tables
        that may have been setup with either upgrade_db or a previous run of
        init_db.
        '''
        self.session.rollback()
        self.session.remove()
        # sqlite database needs to be recreated each time as the
        # memory database is lost.
        if self.metadata.bind.name == 'sqlite':
            # this creates the tables, which isn't required inbetween tests
            # that have simply called rebuild_db.
            self.create_db()
        else:
            if not self.tables_created:
                self.upgrade_db()
                self.init_configuration_data()
                self.tables_created = True

    def clean_db(self):
        metadata = MetaData(self.metadata.bind)
        metadata.reflect()
        metadata.drop_all()
        self.tables_created = False

    def init_const_data(self):
        '''Creates 'constant' objects that should always be there in
        the database. If they are already there, this method does nothing.'''
        for username in (PSEUDO_USER__LOGGED_IN,
                         PSEUDO_USER__VISITOR):
            if not User.by_name(username):
                user = User(name=username)
                Session.add(user)
        Session.flush() # so that these objects can be used
                        # straight away
        init_authz_const_data()

    def init_configuration_data(self):
        '''Default configuration, for when CKAN is first used out of the box.
        This state may be subsequently configured by the user.'''
        init_authz_configuration_data()
        if Session.query(Revision).count() == 0:
            rev = Revision()
            rev.author = 'system'
            rev.message = u'Initialising the Repository'
            Session.add(rev)
        self.commit_and_remove()   

    def create_db(self):
        '''Ensures tables, const data and some default config is created.
        i.e. the same as init_db APART from when running tests, when init_db
        has shortcuts.
        '''
        self.metadata.create_all(bind=self.metadata.bind)    
        self.init_const_data()
        self.init_configuration_data()

    def latest_migration_version(self):
        import migrate.versioning.api as mig
        version = mig.version(self.migrate_repository)
        return version

    def rebuild_db(self):
        '''Clean and init the db'''
        if self.tables_created:
            # just delete data, leaving tables - this is faster
            self.delete_all()
        else:
            # delete tables and data
            self.clean_db()
        self.session.remove()
        self.init_db()
        self.session.flush()
        
    def delete_all(self):
        '''Delete all data from all tables.'''
        self.session.remove()
        ## use raw connection for performance
        connection = self.session.connection()
        if sqav.startswith("0.4"):
            tables = self.metadata.table_iterator()
        else:
            tables = reversed(metadata.sorted_tables)
        for table in tables:
            connection.execute('delete from "%s"' % table.name)
        self.session.commit()
        ##add default data
        self.init_const_data()
        self.init_configuration_data()
        self.session.commit()


    def setup_migration_version_control(self, version=None):
        import migrate.versioning.exceptions
        import migrate.versioning.api as mig
        # set up db version control (if not already)
        try:
            mig.version_control(self.metadata.bind,
                    self.migrate_repository, version)
        except migrate.versioning.exceptions.DatabaseAlreadyControlledError:
            pass

    def upgrade_db(self, version=None):
        '''Upgrade db using sqlalchemy migrations.

        @param version: version to upgrade to (if None upgrade to latest)
        '''
        assert meta.engine.name in ('postgres', 'postgresql'), \
            'Database migration - only Postgresql engine supported (not %s).' %\
            meta.engine.name
        import migrate.versioning.api as mig
        self.setup_migration_version_control()
        mig.upgrade(self.metadata.bind, self.migrate_repository, version=version)
        self.init_const_data()
        
        ##this prints the diffs in a readable format
        ##import pprint
        ##from migrate.versioning.schemadiff import getDiffOfModelAgainstDatabase
        ##pprint.pprint(getDiffOfModelAgainstDatabase(self.metadata, self.metadata.bind).colDiffs)

repo = Repository(metadata, Session,
        versioned_objects=[Package, PackageTag, Resource, ResourceGroup, PackageExtra, PackageGroup, Group]
        )


# Fix up Revision with project-specific attributes
def _get_packages(self):
    changes = repo.list_changes(self)
    pkgs = set()
    for pkg_rev in changes.pop(Package):
        pkgs.add(pkg_rev.continuity)
    for non_pkg_rev_list in changes.values():
        for non_pkg_rev in non_pkg_rev_list:
            if hasattr(non_pkg_rev.continuity, 'package'):
                pkgs.add(non_pkg_rev.continuity.package)
    return list(pkgs)

def _get_groups(self):
    changes = repo.list_changes(self)
    groups = set()
    for group_rev in changes.pop(Group):
        groups.add(group_rev.continuity)
    for non_group_rev_list in changes.values():
        for non_group_rev in non_group_rev_list:
            if hasattr(non_group_rev.continuity, 'group'):
                groups.add(non_group_rev.continuity.group)
    return list(groups)

# could set this up directly on the mapper?
def _get_revision_user(self):
    username = unicode(self.author)
    user = Session.query(User).filter_by(name=username).first()
    return user

Revision.packages = property(_get_packages)
Revision.groups = property(_get_groups)
Revision.user = property(_get_revision_user)

def strptimestamp(s):
    import datetime, re
    return datetime.datetime(*map(int, re.split('[^\d]', s)))

def strftimestamp(t):
    return t.isoformat()

