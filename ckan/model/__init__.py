# encoding: utf-8

import warnings
import logging
import re
from datetime import datetime
from time import sleep
from os.path import splitext

from six import text_type
import vdm.sqlalchemy
from vdm.sqlalchemy.base import SQLAlchemySession
from sqlalchemy import MetaData, __version__ as sqav, Table
from sqlalchemy.util import OrderedDict
from sqlalchemy.exc import ProgrammingError

from alembic.command import (
    upgrade as alembic_upgrade,
    downgrade as alembic_downgrade,
    current as alembic_current
)
from alembic.config import Config as AlembicConfig

import meta
from meta import (
    Session,
    engine_is_sqlite,
    engine_is_pg,
)
from core import (
    System,
    Revision,
    State,
    revision_table,
)
from package import (
    Package,
    PACKAGE_NAME_MIN_LENGTH,
    PACKAGE_NAME_MAX_LENGTH,
    PACKAGE_VERSION_MAX_LENGTH,
    package_table,
    package_revision_table,
    PackageTagRevision,
    PackageRevision,
)
from tag import (
    Tag,
    PackageTag,
    MAX_TAG_LENGTH,
    MIN_TAG_LENGTH,
    tag_table,
    package_tag_table,
    package_tag_revision_table,
)
from user import (
    User,
    user_table,
)
from group import (
    Member,
    Group,
    member_revision_table,
    group_revision_table,
    group_table,
    GroupRevision,
    MemberRevision,
    member_table,
)
from group_extra import (
    GroupExtra,
    group_extra_table,
    group_extra_revision_table,
)
from package_extra import (
    PackageExtra,
    package_extra_table,
    extra_revision_table,
)
from resource import (
    Resource,
    ResourceRevision,
    DictProxy,
    resource_table,
    resource_revision_table,
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
    PackageRelationshipRevision,
    package_relationship_table,
    package_relationship_revision_table,
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
    system_info_revision_table,
    SystemInfo,
    SystemInfoRevision,
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


class Repository(vdm.sqlalchemy.Repository):
    _repo_path, _dot_repo_name = splitext(ckan.migration.__name__)
    migrate_repository = _repo_path + ':' + _dot_repo_name[1:]

    # note: tables_created value is not sustained between instantiations
    #       so only useful for tests. The alternative is to use
    #       are_tables_created().
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
        alembic_config = AlembicConfig()
        alembic_config.set_main_option(
            "script_location", self.migrate_repository
        )
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

    def purge_revision(self, revision, leave_record=False):
        '''Purge all changes associated with a revision.

        @param leave_record: if True leave revision in existence but
        change message to "PURGED: {date-time-of-purge}". If false
        delete revision object as well.

        Summary of the Algorithm
        ------------------------

        1. list all RevisionObjects affected by this revision
        2. check continuity objects and cascade on everything else ?
        3. crudely get all object revisions associated with this
        4. then check whether this is the only revision and delete
           the continuity object

        5. ALTERNATIVELY delete all associated object revisions then
           do a select on continutity to check which have zero
           associated revisions (should only be these ...) '''

        to_purge = []
        SQLAlchemySession.setattr(self.session, 'revisioning_disabled', True)
        self.session.autoflush = False
        for o in self.versioned_objects:
            revobj = o.__revision_class__
            items = self.session.query(revobj). \
                    filter_by(revision=revision).all()
            for item in items:
                continuity = item.continuity

                if continuity.revision == revision:  # must change continuity
                    trevobjs = self.session.query(revobj).join('revision'). \
                            filter(revobj.continuity == continuity). \
                            order_by(Revision.timestamp.desc()).all()
                    if len(trevobjs) == 0:
                        raise Exception('Should have at least one revision.')
                    if len(trevobjs) == 1:
                        to_purge.append(continuity)
                    else:
                        self.revert(continuity, trevobjs[1])
                        for num, obj in enumerate(trevobjs):
                            if num == 0:
                                continue

                            obj.expired_timestamp = datetime(9999, 12, 31)
                            self.session.add(obj)
                            break
                # now delete revision object
                self.session.delete(item)
            for cont in to_purge:
                self.session.delete(cont)
        if leave_record:
            revision.message = u'PURGED: %s' % datetime.now()
        else:
            self.session.delete(revision)
        self.commit_and_remove()


repo = Repository(meta.metadata, meta.Session,
                  versioned_objects=[Package, PackageTag, Resource,
                                     Member,
                                     Group, SystemInfo]
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
    username = text_type(self.author)
    user = meta.Session.query(User).filter_by(name=username).first()
    return user

Revision.packages = property(_get_packages)
Revision.groups = property(_get_groups)
Revision.user = property(_get_revision_user)


def revision_as_dict(revision, include_packages=True, include_groups=True,
                     ref_package_by='name'):
    revision_dict = OrderedDict((
        ('id', revision.id),
        ('timestamp', revision.timestamp.isoformat()),
        ('message', revision.message),
        ('author', revision.author),
        ('approved_timestamp',
         revision.approved_timestamp.isoformat() \
         if revision.approved_timestamp else None),
        ))
    if include_packages:
        revision_dict['packages'] = [getattr(pkg, ref_package_by) \
                                     for pkg in revision.packages
                                     if (pkg and not pkg.private)]
    if include_groups:
        revision_dict['groups'] = [getattr(grp, ref_package_by) \
                                     for grp in revision.groups if grp]

    return revision_dict


def is_id(id_string):
    '''Tells the client if the string looks like a revision id or not'''
    reg_ex = '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(reg_ex, id_string))
