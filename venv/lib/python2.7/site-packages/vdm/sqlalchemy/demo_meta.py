'''SQLAlchemy Metadata and Session object'''
from sqlalchemy import MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

__all__ = ['Session', 'engine', 'metadata', 'init_with_engine' ]

engine = None

# IMPORTANT NOTE for vdm
# You cannot use autoflush=True, autocommit=False
# This is because flushes to the DB may then happen at 'random' times when no
# Revision has yet been set which may result in errors
Session = scoped_session(sessionmaker(
    autoflush=True,
    # autocommit=False,
    transactional=True,
    ))

# Global metadata. If you have multiple databases with overlapping table
# names, you'll need a metadata for each database
metadata = MetaData()

def init_with_engine(engine_):
    metadata.bind = engine_
    Session.configure(bind=engine_)
    engine = engine_

