# encoding: utf-8

"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData
import sqlalchemy.orm as orm
from sqlalchemy.orm.session import SessionExtension

from ckan.model import extension

__all__ = ['Session', 'engine_is_sqlite', 'engine_is_pg']


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
    extension=[CkanSessionExtension(),
               extension.PluginSessionExtension(),
    ],
))

create_local_session = orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[CkanSessionExtension(),
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
