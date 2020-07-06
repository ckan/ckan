# encoding: utf-8

import warnings
import logging
import os
import re
from time import sleep
from os.path import splitext

from sqlalchemy import MetaData, __version__ as sqav, Table
from sqlalchemy.exc import ProgrammingError

from alembic.command import (
    upgrade as alembic_upgrade,
    downgrade as alembic_downgrade,
    current as alembic_current
)
from alembic.config import Config as AlembicConfig

from ckan.model import meta

from ckan.model.meta import (
    Session,
    engine_is_sqlite,
    engine_is_pg,
)
from ckan.model.core import (
    State,
)
from ckan.model.system import (
    System,
)
from ckan.model.package import (
    Package,
    PackageMember,
    PACKAGE_NAME_MIN_LENGTH,
    PACKAGE_NAME_MAX_LENGTH,
    PACKAGE_VERSION_MAX_LENGTH,
    package_table,
    package_member_table,
)
from ckan.model.tag import (
    Tag,
    PackageTag,
    MAX_TAG_LENGTH,
    MIN_TAG_LENGTH,
    tag_table,
    package_tag_table,
)
from ckan.model.user import (
    User,
    user_table,
)
from ckan.model.group import (
    Member,
    Group,
    group_table,
    member_table,
)
from ckan.model.group_extra import (
    GroupExtra,
    group_extra_table,
)
from ckan.model.package_extra import (
    PackageExtra,
    package_extra_table,
)
from ckan.model.resource import (
    Resource,
    DictProxy,
    resource_table,
)
from ckan.model.resource_view import (
    ResourceView,
    resource_view_table,
)
from ckan.model.tracking import (
    tracking_summary_table,
    TrackingSummary,
    tracking_raw_table
)
from ckan.model.rating import (
    Rating,
    MIN_RATING,
    MAX_RATING,
)
from ckan.model.package_relationship import (
    PackageRelationship,
    package_relationship_table,
)
from ckan.model.task_status import (
    TaskStatus,
    task_status_table,
)
from ckan.model.vocabulary import (
    Vocabulary,
    VOCABULARY_NAME_MAX_LENGTH,
    VOCABULARY_NAME_MIN_LENGTH,
)
from ckan.model.activity import (
    Activity,
    ActivityDetail,
    activity_table,
    activity_detail_table,
)
from ckan.model.term_translation import (
    term_translation_table,
)
from ckan.model.follower import (
    UserFollowingUser,
    UserFollowingDataset,
    UserFollowingGroup,
)
from ckan.model.system_info import (
    system_info_table,
    SystemInfo,
    get_system_info,
    set_system_info,
    delete_system_info,
)
from ckan.model.domain_object import (
    DomainObjectOperation,
    DomainObject,
)
from ckan.model.dashboard import (
    Dashboard,
)
from ckan.model.api_token import (
    ApiToken,
)

import ckan.migration
from ckan.common import config


log = logging.getLogger(__name__)

DB_CONNECT_RETRIES = 10


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
            Table('alembic_version', meta.metadata, autoload=True)
            break
        except sqlalchemy.exc.NoSuchTableError:
            break
        except sqlalchemy.exc.OperationalError as e:
            if 'database system is starting up' in repr(e.orig) and i:
                sleep(DB_CONNECT_RETRIES - i)
                continue
            raise


class Repository():
    _alembic_ini = os.path.join(
        os.path.dirname(ckan.migration.__file__),
        u"alembic.ini"
    )

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

        if self.metadata.bind.engine.url.drivername == 'sqlite':
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
            if table.name == 'alembic_version':
                continue
            connection.execute('delete from "%s"' % table.name)
        self.session.commit()
        log.info('Database table data deleted')

    def reset_alembic_output(self):
        self._alembic_output = []

    def add_alembic_output(self, *args):
        self._alembic_output.append(args)

    def take_alembic_output(self, with_reset=True):
        output = self._alembic_output
        self._alembic_config = []
        return output

    def setup_migration_version_control(self):
        self.reset_alembic_output()
        alembic_config = AlembicConfig(self._alembic_ini)
        alembic_config.set_main_option(
            "sqlalchemy.url", str(self.metadata.bind.url)
        )
        try:
            sqlalchemy_migrate_version = self.metadata.bind.execute(
                u'select version from migrate_version'
            ).scalar()
        except ProgrammingError:
            sqlalchemy_migrate_version = 0

        # this value is used for graceful upgrade from
        # sqlalchemy-migrate to alembic
        alembic_config.set_main_option(
            "sqlalchemy_migrate_version", str(sqlalchemy_migrate_version)
        )
        # This is an interceptor for alembic output. Otherwise,
        # everything will be printed to stdout
        alembic_config.print_stdout = self.add_alembic_output

        self.alembic_config = alembic_config

    def current_version(self):
        try:
            alembic_current(self.alembic_config)
            return self.take_alembic_output()[0][0]
        except (TypeError, IndexError):
            # alembic is not initialized yet
            return 'base'

    def downgrade_db(self, version='base'):
        self.setup_migration_version_control()
        alembic_downgrade(self.alembic_config, version)
        log.info(u'CKAN database version set to: %s', version)

    def upgrade_db(self, version='head'):
        '''Upgrade db using sqlalchemy migrations.

        @param version: version to upgrade to (if None upgrade to latest)
        '''
        _assert_engine_msg = (
            u'Database migration - only Postgresql engine supported (not %s).'
        ) % meta.engine.name
        assert meta.engine.name in (
            u'postgres', u'postgresql'
        ), _assert_engine_msg
        self.setup_migration_version_control()
        version_before = self.current_version()
        alembic_upgrade(self.alembic_config, version)
        version_after = self.current_version()

        if version_after != version_before:
            log.info(
                u'CKAN database version upgraded: %s -> %s',
                version_before,
                version_after
            )
        else:
            log.info(u'CKAN database version remains as: %s', version_after)

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


def parse_db_config(config_key=u'sqlalchemy.url'):
    u''' Takes a config key for a database connection url and parses it into
    a dictionary. Expects a url like:

    'postgres://tester:pass@localhost/ckantest3'

    Returns None if the url could not be parsed.
    '''
    url = config[config_key]
    regex = [
        u'^\\s*(?P<db_type>\\w*)', u'://', u'(?P<db_user>[^:]*)', u':?',
        u'(?P<db_pass>[^@]*)', u'@', u'(?P<db_host>[^/:]*)', u':?',
        u'(?P<db_port>[^/]*)', u'/', u'(?P<db_name>[\\w.-]*)'
    ]
    db_details_match = re.match(u''.join(regex), url)
    if not db_details_match:
        return
    return db_details_match.groupdict()
