import datetime
"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData, __version__ as sqav
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm import scoped_session, sessionmaker
import sqlalchemy.orm as orm
from sqlalchemy.orm.session import SessionExtension

# TODO: remove these imports from here and put them in client model modules
from sqlalchemy import Column, MetaData, Table, types, ForeignKey
from sqlalchemy import or_, and_
from sqlalchemy.types import *
from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref

from ckan.model import extension

from ckan.lib.activity import DatasetActivitySessionExtension

class CkanSessionExtension(SessionExtension):

    def before_flush(self, session, flush_context, instances):
        if not hasattr(session, '_object_cache'):
            session._object_cache= {'new': set(),
                                    'deleted': set(),
                                    'changed': set()}

        changed = [obj for obj in session.dirty if 
            session.is_modified(obj, include_collections=False)]

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
            revision_table = class_mapper(revision_cls).mapped_table
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

Session = scoped_session(sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[CkanSessionExtension(), extension.PluginSessionExtension(),
        DatasetActivitySessionExtension()],
))

create_local_session = sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    extension=[CkanSessionExtension(), extension.PluginSessionExtension(),
        DatasetActivitySessionExtension()],
)

#mapper = Session.mapper
mapper = orm.mapper

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()

def engine_is_sqlite():
    """
    Returns true iff the engine is connected to a sqlite database.
    """
    return engine.url.drivername == 'sqlite'
