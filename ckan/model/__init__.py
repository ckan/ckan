# encoding: utf-8

import warnings
import logging
import re
from datetime import datetime
from time import sleep
import sys

from six import text_type
from sqlalchemy import MetaData, __version__ as sqav, Table
from sqlalchemy.util import OrderedDict

import meta
from meta import (
    Session,
    engine_is_sqlite,
    engine_is_pg,
)
from core import (
    System,
    State,
)
from package import (
    Package,
    PACKAGE_NAME_MIN_LENGTH,
    PACKAGE_NAME_MAX_LENGTH,
    PACKAGE_VERSION_MAX_LENGTH,
    package_table,
)
from tag import (
    Tag,
    PackageTag,
    MAX_TAG_LENGTH,
    MIN_TAG_LENGTH,
    tag_table,
    package_tag_table,
)
from user import (
    User,
    user_table,
)
from group import (
    Member,
    Group,
    group_table,
    member_table,
)
from group_extra import (
    GroupExtra,
    group_extra_table,
)
from package_extra import (
    PackageExtra,
    package_extra_table,
)
from resource import (
    Resource,
    DictProxy,
    resource_table,
)
from resource_view import (
    ResourceView,
    resource_view_table,
)
from tracking import (
    tracking_summary_table,
    TrackingSummary,
    tracking_raw_table
)
from rating import (
    Rating,
    MIN_RATING,
    MAX_RATING,
)
from package_relationship import (
    PackageRelationship,
    package_relationship_table,
)
from task_status import (
    TaskStatus,
    task_status_table,
)
from vocabulary import (
    Vocabulary,
    VOCABULARY_NAME_MAX_LENGTH,
    VOCABULARY_NAME_MIN_LENGTH,
)
from activity import (
    Activity,
    ActivityDetail,
    activity_table,
    activity_detail_table,
)
from term_translation import (
    term_translation_table,
)
from follower import (
    UserFollowingUser,
    UserFollowingDataset,
    UserFollowingGroup,
)
from system_info import (
    system_info_table,
    SystemInfo,
    get_system_info,
    set_system_info,
    delete_system_info,
)
from domain_object import (
    DomainObjectOperation,
    DomainObject,
)
from dashboard import (
    Dashboard,
)

import ckan.migration

log = logging.getLogger(__name__)


DB_CONNECT_RETRIES = 10

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
    for i in reversed(range(DB_CONNECT_RETRIES)):
        try:
            global version_table
            version_table = Table('migrate_version', meta.metadata, autoload=True)
            break
        except sqlalchemy.exc.NoSuchTableError:
            break
        except sqlalchemy.exc.OperationalError as e:
            if 'database system is starting up' in repr(e.orig) and i:
                sleep(DB_CONNECT_RETRIES - i)
                continue
            raise


class Repository():
    migrate_repository = ckan.migration.__path__[0]

    # note: tables_created value is not sustained between instantiations
    #       so only useful for tests. The alternative is to use
    #       are_tables_created().
    tables_created_and_initialised = False

    def __init__(self, metadata, session):
        self.metadata = metadata
        self.session = session
        self.commit = session.commit

    def commit_and_remove(self):
        self.session.commit()
        self.session.remove()

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
                self.tables_created_and_initialised = True
        log.info('Database initialised')

    def clean_db(self):
        self.commit_and_remove()
        meta.metadata = MetaData(self.metadata.bind)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', '.*(reflection|tsvector).*')
            meta.metadata.reflect()

        meta.metadata.drop_all()
        self.tables_created_and_initialised = False
        log.info('Database tables dropped')

    def create_db(self):
        '''Ensures tables, const data and some default config is created.
        i.e. the same as init_db APART from when running tests, when init_db
        has shortcuts.
        '''
        self.metadata.create_all(bind=self.metadata.bind)
        log.info('Database tables created')

    def latest_migration_version(self):
        import migrate.versioning.api as mig
        version = mig.version(self.migrate_repository)
        return version

    def rebuild_db(self):
        '''Clean and init the db'''
        if self.tables_created_and_initialised:
            # just delete data, leaving tables - this is faster
            self.delete_all()
        else:
            # delete tables and data
            self.clean_db()
        self.session.remove()
        self.init_db()
        self.session.flush()
        log.info('Database rebuilt')

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
            if table.name == 'migrate_version':
                continue
            connection.execute('delete from "%s"' % table.name)
        self.session.commit()
        log.info('Database table data deleted')

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
        # pre-upgrade checks
        assert meta.engine.name in ('postgres', 'postgresql'), \
            'Database migration - only Postgresql engine supported (not %s).' \
                % meta.engine.name
        import migrate.versioning.api as mig
        self.setup_migration_version_control()
        version_before = mig.db_version(self.metadata.bind, self.migrate_repository)
        from ckan.migration.migrate_package_activity import num_unmigrated
        # if still at version 0 there can't be any activities needing migrating
        if version_before > 0:
            num_unmigrated_dataset_activities = num_unmigrated(meta.engine)
            if num_unmigrated_dataset_activities:
                print('''
    !!! ERROR !!!
    You have {num_unmigrated} unmigrated package activities.

    You cannot do this db upgrade until you completed the package activity
    migration first. Full instructions for this situation are here:

    https://github.com/ckan/ckan/wiki/Migrate-package-activity#if-you-tried-to-upgrade-from-ckan-28-or-earlier-to-ckan-29-and-it-stopped-at-paster-db-upgrade
                '''.format(num_unmigrated=num_unmigrated_dataset_activities))
                sys.exit(1)

        mig.upgrade(self.metadata.bind, self.migrate_repository, version=version)
        version_after = mig.db_version(self.metadata.bind, self.migrate_repository)
        if version_after != version_before:
            log.info('CKAN database version upgraded: %s -> %s', version_before, version_after)
        else:
            log.info('CKAN database version remains as: %s', version_after)

        ##this prints the diffs in a readable format
        ##import pprint
        ##from migrate.versioning.schemadiff import getDiffOfModelAgainstDatabase
        ##pprint.pprint(getDiffOfModelAgainstDatabase(self.metadata, self.metadata.bind).colDiffs)

    def are_tables_created(self):
        meta.metadata = MetaData(self.metadata.bind)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', '.*(reflection|geometry).*')
            meta.metadata.reflect()
        return bool(meta.metadata.tables)


repo = Repository(meta.metadata, meta.Session)


def is_id(id_string):
    '''Tells the client if the string looks like a revision id or not'''
    reg_ex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(reg_ex, id_string))
