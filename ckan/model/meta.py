# encoding: utf-8

"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData, event
import sqlalchemy.orm as orm

from ckan.model import extension

__all__ = ['Session']


# SQLAlchemy database engine. Updated by model.init_model()
engine = None


Session = orm.scoped_session(orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
))


create_local_session = orm.sessionmaker(
    autoflush=False,
    autocommit=False,
    expire_on_commit=False
)

#mapper = Session.mapper
mapper = orm.mapper

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()
