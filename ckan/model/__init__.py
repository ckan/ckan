from __future__ import with_statement # necessary for python 2.5 support
import warnings
import logging

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
from authz import *
from package_extra import *
from resource import *
from rating import *
from package_relationship import *
from task_status import *
from activity import *
import ckan.migration
from ckan.lib.helpers import OrderedDict, datetime_to_date_str
from vdm.sqlalchemy.base import SQLAlchemySession

log = logging.getLogger(__name__)

# set up in init_model after metadata is bound
version_table = None

def init_model(engine):
    '''Call me before using any of the tables or classes in the model'''
    meta.Session.remove()
    meta.Session.configure(bind=engine)
    meta.create_local_session.configure(bind=engine)
    meta.engine = engine
    meta.metadata.bind = engine
    # sqlalchemy migrate version table
    import sqlalchemy.exc
    try:
        version_table = Table('migrate_version', metadata, autoload=True)
    except sqlalchemy.exc.NoSuchTableError:
        pass

    

class Repository(vdm.sqlalchemy.Repository):
    migrate_repository = ckan.migration.__path__[0]

    # note: tables_created value is not sustained between instantiations so
    #       only useful for tests. The alternative is to use are_tables_created().
    tables_created_and_initialised = False 

    def init_db(self):
        '''Ensures tables, const data and some default config is created.
        This method MUST be run before using CKAN for the first time.
        Before this method is run, you can either have a clean db or tables
        that may have been setup with either upgrade_db or a previous run of
        init_db.
        '''
        warnings.filterwarnings('ignore', 'SAWarning')
        self.session.rollback()
        self.session.remove()
        # sqlite database needs to be recreated each time as the
        # memory database is lost.
        if self.metadata.bind.name == 'sqlite':
            # this creates the tables, which isn't required inbetween tests
            # that have simply called rebuild_db.
            self.create_db()
        else:
            if not self.tables_created_and_initialised:
                self.upgrade_db()
                self.init_configuration_data()
                self.tables_created_and_initialised = True

    def clean_db(self):
        metadata = MetaData(self.metadata.bind)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', '.*(reflection|tsvector).*')
            metadata.reflect()

        metadata.drop_all()
        self.tables_created_and_initialised = False

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
        if self.tables_created_and_initialised:
            # just delete data, leaving tables - this is faster
            self.delete_all()
            # re-add default data
            self.init_const_data()
            self.init_configuration_data()
            self.session.commit()
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
            tables = reversed(self.metadata.sorted_tables)
        for table in tables:
            connection.execute('delete from "%s"' % table.name)
        self.session.commit()


    def setup_migration_version_control(self, version=None):
        import migrate.exceptions
        import migrate.versioning.api as mig
        # set up db version control (if not already)
        try:
            mig.version_control(self.metadata.bind,
                    self.migrate_repository, version)
        except migrate.exceptions.DatabaseAlreadyControlledError:
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

    def are_tables_created(self):
        metadata = MetaData(self.metadata.bind)
        metadata.reflect()
        return bool(metadata.tables)

    def purge_revision(self, revision, leave_record=False):
        '''Purge all changes associated with a revision.

        @param leave_record: if True leave revision in existence but change message
            to "PURGED: {date-time-of-purge}". If false delete revision object as
            well.

        Summary of the Algorithm
        ------------------------

        1. list all RevisionObjects affected by this revision
        2. check continuity objects and cascade on everything else ?
            1. crudely get all object revisions associated with this
            2. then check whether this is the only revision and delete the
            continuity object

            3. ALTERNATIVELY delete all associated object revisions then do a
            select on continutity to check which have zero associated revisions
            (should only be these ...)
        '''
        to_purge = []
        SQLAlchemySession.setattr(self.session, 'revisioning_disabled', True)
        self.session.autoflush = False
        for o in self.versioned_objects:
            revobj = o.__revision_class__
            items = self.session.query(revobj).filter_by(revision=revision).all()
            for item in items:
                continuity = item.continuity

                if continuity.revision == revision: # need to change continuity
                    trevobjs = self.session.query(revobj).join('revision').  filter(
                            revobj.continuity==continuity
                            ).order_by(Revision.timestamp.desc()).all()
                    if len(trevobjs) == 0:
                        raise Exception('Should have at least one revision.')
                    if len(trevobjs) == 1:
                        to_purge.append(continuity)
                    else:
                        self.revert(continuity, trevobjs[1])
                        for num, obj in enumerate(trevobjs):
                            if num == 0:
                                continue
                            if 'pending' not in obj.state:
                                obj.current = True
                                import datetime
                                obj.expired_timestamp = datetime.datetime(9999, 12, 31)
                                self.session.add(obj)
                                break
                # now delete revision object
                self.session.delete(item)
            for cont in to_purge:
                self.session.delete(cont)
        if leave_record:
            import datetime
            revision.message = u'PURGED: %s' % datetime.datetime.now()
        else:
            self.session.delete(revision)
        self.commit_and_remove()


repo = Repository(metadata, Session,
        versioned_objects=[Package, PackageTag, Resource, ResourceGroup, PackageExtra, Member, Group]
        )


# Fix up Revision with project-specific attributes
def _get_packages(self):
    changes = repo.list_changes(self)
    pkgs = set()
    for revision_list in changes.values():
        for revision in revision_list:
            obj = revision.continuity
            if hasattr(obj, 'related_packages'):
                pkgs.update(obj.related_packages())

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

def revision_as_dict(revision, include_packages=True, include_groups=True,ref_package_by='name'):
    revision_dict = OrderedDict((
        ('id', revision.id),
        ('timestamp', datetime_to_date_str(revision.timestamp)),
        ('message', revision.message),
        ('author', revision.author),
        ('approved_timestamp',
         datetime_to_date_str(revision.approved_timestamp) \
         if revision.approved_timestamp else None),
        ))
    if include_packages:
        revision_dict['packages'] = [getattr(pkg, ref_package_by) \
                                     for pkg in revision.packages if pkg]
    if include_groups:
        revision_dict['groups'] = [getattr(grp, ref_package_by) \
                                     for grp in revision.groups if grp]
       
    return revision_dict

def is_id(id_string):
    '''Tells the client if the string looks like a revision id or not'''
    import re
    return bool(re.match('^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', id_string))
