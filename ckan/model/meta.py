"""SQLAlchemy Metadata and Session object"""
from sqlalchemy import MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
import sqlalchemy.orm as orm

# TODO: remove these imports from here and put them in client model modules
from sqlalchemy import Column, MetaData, Table, types, ForeignKey
from sqlalchemy import or_, and_
from sqlalchemy.types import *
from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref

# __all__ = ['Session', 'engine', 'metadata', 'mapper']

# SQLAlchemy database engine. Updated by model.init_model()
engine = None

# SQLAlchemy session manager. Updated by model.init_model()
Session = scoped_session(sessionmaker(
    autoflush=True,
    transactional=True,
    ))

#mapper = Session.mapper
mapper = orm.mapper

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()

