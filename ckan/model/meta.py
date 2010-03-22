import logging
logger = logging.getLogger(__name__)

from pylons import config
from sqlalchemy import Column, MetaData, Table, types, ForeignKey
from sqlalchemy import orm
from sqlalchemy import or_, and_
from sqlalchemy.types import *

metadata = MetaData(bind=config['pylons.g'].sa_engine)

## --------------------------------------------------------
## Mapper Stuff

from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref
# both options now work
# Session = scoped_session(sessionmaker(autoflush=False, transactional=True))
# this is the more testing one ...
Session = scoped_session(sessionmaker(
    autoflush=True,
    transactional=True,
    bind=config['pylons.g'].sa_engine
    ))

#mapper = Session.mapper
mapper = orm.mapper

