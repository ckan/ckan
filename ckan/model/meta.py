# encoding: utf-8

"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData, event
import sqlalchemy.orm as orm

from ckan.model import extension

__all__ = ['Session', 'engine_is_sqlite', 'engine_is_pg']


# SQLAlchemy database engine. Updated by model.init_model()
engine = None


Session = orm.scoped_session(orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[extension.PluginSessionExtension(),],
))


create_local_session = orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[extension.PluginSessionExtension(),],
)


@event.listens_for(create_local_session, 'before_flush')
@event.listens_for(Session, 'before_flush')
def ckan_before_flush(session, flush_context, instances):
    """ Create a new _object_cache in the Session object.

    _object_cache is used in DomainObjectModificationExtension to trigger
    notifications on changes. e.g: re-indexing a package in solr upon update.
    """
    if not hasattr(session, '_object_cache'):
        session._object_cache= {'new': set(),
                                'deleted': set(),
                                'changed': set()}

    changed = [obj for obj in session.dirty if
        session.is_modified(obj, include_collections=False)]

    session._object_cache['new'].update(session.new)
    session._object_cache['deleted'].update(session.deleted)
    session._object_cache['changed'].update(changed)

@event.listens_for(create_local_session, 'after_commit')
@event.listens_for(Session, 'after_commit')
def ckan_after_commit(session):
    """ Cleans our custom _object_cache attribute after commiting.
    """
    if hasattr(session, '_object_cache'):
        del session._object_cache

@event.listens_for(create_local_session, 'before_commit')
@event.listens_for(Session, 'before_commit')
def ckan_before_commit(session):
    session.flush()
    try:
        session._object_cache
    except AttributeError:
        return

@event.listens_for(create_local_session, 'after_rollback')
@event.listens_for(Session, 'after_rollback')
def ckan_after_rollback(session):
    """ Cleans our custom _object_cache attribute after rollback.
    """
    if hasattr(session, '_object_cache'):
        del session._object_cache


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
