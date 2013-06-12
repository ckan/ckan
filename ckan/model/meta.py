import datetime

from paste.deploy.converters import asbool
from pylons import config
"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData, and_
import sqlalchemy.orm as orm
from sqlalchemy.orm.session import SessionExtension

import extension
import ckan.lib.activity_streams_session_extension as activity

__all__ = ['Session', 'engine_is_sqlite', 'engine_is_pg']


class CkanCacheExtension(SessionExtension):
    ''' This extension checks what tables have been affected by
    database access and allows us to act on them. Currently this is
    used by the page cache to flush the cache when data in the database
    is altered. '''

    def __init__(self, *args, **kw):
        super(CkanCacheExtension, self).__init__(*args, **kw)
        # Setup Redis support if needed.
        self.use_redis = asbool(config.get('ckan.page_cache_enabled'))
        if self.use_redis:
            import redis
            self.redis = redis
            self.redis_connection is None
            self.redis_exception = redis.exceptions.ConnectionError

    def after_commit(self, session):
        if hasattr(session, '_object_cache'):
            oc = session._object_cache
            oc_list = oc['new']
            oc_list.update(oc['changed'])
            oc_list.update(oc['deleted'])
            objs = set()
            for item in oc_list:
                objs.add(item.__class__.__name__)

        # Flush Redis
        if self.use_redis:
            if self.redis_connection is None:
                try:
                    self.redis_connection = self.redis.StrictRedis()
                except self.redis_exception:
                    pass
            try:
                self.redis_connection.flushdb()
            except self.redis_exception:
                pass

class CkanSessionExtension(SessionExtension):

    def before_flush(self, session, flush_context, instances):
        if not hasattr(session, '_object_cache'):
            session._object_cache= {'new': set(),
                                    'deleted': set(),
                                    'changed': set()}

        changed = [obj for obj in session.dirty if 
            session.is_modified(obj, include_collections=False, passive=True)]

        session._object_cache['new'].update(session.new)
        session._object_cache['deleted'].update(session.deleted)
        session._object_cache['changed'].update(changed)


    def before_commit(self, session):
        session.flush()
        try:
            obj_cache = session._object_cache
            revision = session.revision
        except AttributeError:
            return
        if getattr(session, 'revisioning_disabled', False):
            return
        new = obj_cache['new']
        changed = obj_cache['changed']
        deleted = obj_cache['deleted']
        for obj in new | changed | deleted:
            if not hasattr(obj, '__revision_class__'):
                continue
            revision_cls = obj.__revision_class__
            revision_table = orm.class_mapper(revision_cls).mapped_table
            ## when a normal active transaction happens
            if 'pending' not in obj.state:
                ### this is asql statement as we do not want it in object cache
                session.execute(
                    revision_table.update().where(
                        and_(revision_table.c.id == obj.id,
                             revision_table.c.current == '1')
                    ).values(current='0')
                )

            q = session.query(revision_cls)
            q = q.filter_by(expired_timestamp=datetime.datetime(9999, 12, 31), id=obj.id)
            results = q.all()
            for rev_obj in results:
                values = {}
                if rev_obj.revision_id == revision.id:
                    values['revision_timestamp'] = revision.timestamp
                    if 'pending' not in obj.state:
                        values['current'] = '1'
                else:
                    values['expired_id'] = revision.id
                    values['expired_timestamp'] = revision.timestamp
                session.execute(
                    revision_table.update().where(
                        and_(revision_table.c.id == rev_obj.id,
                             revision_table.c.revision_id == rev_obj.revision_id)
                    ).values(**values)
                )

    def after_commit(self, session):
        if hasattr(session, '_object_cache'):
            del session._object_cache

    def after_rollback(self, session):
        if hasattr(session, '_object_cache'):
            del session._object_cache

# __all__ = ['Session', 'engine', 'metadata', 'mapper']

# SQLAlchemy database engine. Updated by model.init_model()
engine = None

Session = orm.scoped_session(orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[CkanCacheExtension(),
               CkanSessionExtension(),
               extension.PluginSessionExtension(),
               activity.DatasetActivitySessionExtension()],
))

create_local_session = orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[CkanCacheExtension(),
               CkanSessionExtension(),
               extension.PluginSessionExtension(),
               activity.DatasetActivitySessionExtension()],
)

#mapper = Session.mapper
mapper = orm.mapper

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()


def engine_is_sqlite(sa_engine=None):
    # Returns true iff the engine is connected to a sqlite database.
    return (sa_engine or engine).url.drivername == 'sqlite'


def engine_is_pg(sa_engine=None):
    # Returns true iff the engine is connected to a postgresql database.
    # According to http://docs.sqlalchemy.org/en/latest/core/engines.html#postgresql
    # all Postgres driver names start with `postgresql`
    return (sa_engine or engine).url.drivername.startswith('postgresql')
