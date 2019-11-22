# encoding: utf-8

import datetime

from ckan.common import asbool
from ckan.common import config
"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData, and_
import sqlalchemy.orm as orm
from sqlalchemy.orm.session import SessionExtension

from ckan.model import extension

__all__ = ['Session', 'engine_is_sqlite', 'engine_is_pg']


class CkanCacheExtension(SessionExtension):
    ''' This extension checks what tables have been affected by
    database access and allows us to act on them. Currently this is
    used by the page cache to flush the cache when data in the database
    is altered. '''

    def __init__(self, *args, **kw):
        super(CkanCacheExtension, self).__init__(*args, **kw)

    def after_commit(self, session):
        if hasattr(session, '_object_cache'):
            oc = session._object_cache
            oc_list = oc['new']
            oc_list.update(oc['changed'])
            oc_list.update(oc['deleted'])
            objs = set()
            for item in oc_list:
                objs.add(item.__class__.__name__)


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
        except AttributeError:
            return

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
    ],
))

create_local_session = orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[CkanCacheExtension(),
               CkanSessionExtension(),
               extension.PluginSessionExtension(),
    ],
)

#mapper = Session.mapper
mapper = orm.mapper

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()


def engine_is_sqlite(sa_engine=None):
    # Returns true iff the engine is connected to a sqlite database.

    return (sa_engine or engine).engine.url.drivername == 'sqlite'


def engine_is_pg(sa_engine=None):
    # Returns true iff the engine is connected to a postgresql database.
    # According to http://docs.sqlalchemy.org/en/latest/core/engines.html#postgresql
    # all Postgres driver names start with `postgres`
    return (sa_engine or engine).engine.url.drivername.startswith('postgres')
