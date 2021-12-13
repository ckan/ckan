# encoding: utf-8

"""SQLAlchemy Metadata and Session object"""
import ckan.plugins as p

from sqlalchemy import MetaData, event
import sqlalchemy.orm as orm

__all__ = ['Session']


# SQLAlchemy database engine. Updated by model.init_model()
engine = None


Session = orm.scoped_session(orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
))


create_local_session = orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
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

    for plugin in p.PluginImplementations(p.ISession):
        if hasattr(plugin, 'before_flush'):
            plugin.before_flush(session, flush_context, instances)


@event.listens_for(create_local_session, 'after_commit')
@event.listens_for(Session, 'after_commit')
def ckan_after_commit(session):
    """ Cleans our custom _object_cache attribute after commiting.
    """
    if hasattr(session, '_object_cache'):
        del session._object_cache

    for plugin in p.PluginImplementations(p.ISession):
        if hasattr(plugin, 'after_commit'):
            plugin.after_commit(session)


@event.listens_for(create_local_session, 'before_commit')
@event.listens_for(Session, 'before_commit')
def ckan_before_commit(session):
    session.flush()
    try:
        session._object_cache
    except AttributeError:
        return

    for plugin in p.PluginImplementations(p.ISession):
        if hasattr(plugin, 'before_commit'):
            plugin.before_commit(session)


@event.listens_for(create_local_session, 'after_rollback')
@event.listens_for(Session, 'after_rollback')
def ckan_after_rollback(session):
    """ Cleans our custom _object_cache attribute after rollback.
    """
    if hasattr(session, '_object_cache'):
        del session._object_cache

    for plugin in p.PluginImplementations(p.ISession):
        if hasattr(plugin, 'after_rollback'):
            plugin.after_rollback(session)


@event.listens_for(create_local_session, 'after_begin')
@event.listens_for(Session, 'after_begin')
def ckan_after_begin(session, transaction, connection):
    """ Allows extensions to listen to the after_begin event.
    """
    for plugin in p.PluginImplementations(p.ISession):
        if hasattr(plugin, 'after_begin'):
            plugin.after_begin(session, transaction, connection)


@event.listens_for(create_local_session, 'after_flush')
@event.listens_for(Session, 'after_flush')
def ckan_after_flush(session, flush_context):
    """ Allows extensions to listen to the after_flush event.
    """
    for plugin in p.PluginImplementations(p.ISession):
        if hasattr(plugin, 'after_flush'):
            plugin.after_flush(session, flush_context)


#mapper = Session.mapper
mapper = orm.mapper

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()
