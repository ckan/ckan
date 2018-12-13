'''Demo of vdm for SQLAlchemy.

This module sets up a small domain model with some versioned objects. Code
that then uses these objects can be found in demo_test.py.
'''
from datetime import datetime
import logging
logger = logging.getLogger('vdm')

from sqlalchemy import *
from sqlalchemy import __version__ as sqla_version
# from sqlalchemy import create_engine

import vdm.sqlalchemy

TEST_ENGINE = "postgres"  # or "sqlite"

if TEST_ENGINE == "postgres":
    engine = create_engine('postgres://ckan_default:pass@localhost/vdmtest',
                           pool_threadlocal=True)
else:
    # setting the isolation_level is a hack required for sqlite support
    # until http://code.google.com/p/pysqlite/issues/detail?id=24 is
    # fixed.
    engine = create_engine('sqlite:///:memory:',
                           connect_args={'isolation_level': None})

metadata = MetaData(bind=engine)

## VDM-specific tables

revision_table = vdm.sqlalchemy.make_revision_table(metadata)

## Demo tables

license_table = Table('license', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('open', Boolean),
        )

import uuid
def uuidstr(): return str(uuid.uuid4())
package_table = Table('package', metadata,
        # Column('id', Integer, primary_key=True),
        Column('id', String(36), default=uuidstr, primary_key=True),
        Column('name', String(100), unique=True),
        Column('title', String(100)),
        Column('license_id', Integer, ForeignKey('license.id')),
        Column('notes', UnicodeText),
)

tag_table = Table('tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', Integer, primary_key=True),
        # Column('package_id', Integer, ForeignKey('package.id')),
        Column('package_id', String(36), ForeignKey('package.id')),
        Column('tag_id', Integer, ForeignKey('tag.id')),
        )


vdm.sqlalchemy.make_table_stateful(license_table)
vdm.sqlalchemy.make_table_stateful(package_table)
vdm.sqlalchemy.make_table_stateful(tag_table)
vdm.sqlalchemy.make_table_stateful(package_tag_table)
license_revision_table = vdm.sqlalchemy.make_revisioned_table(license_table)
package_revision_table = vdm.sqlalchemy.make_revisioned_table(package_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = vdm.sqlalchemy.make_revisioned_table(package_tag_table)



## -------------------
## Mapped classes


class License(vdm.sqlalchemy.RevisionedObjectMixin,
    vdm.sqlalchemy.StatefulObjectMixin,
    vdm.sqlalchemy.SQLAlchemyMixin
    ):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

class Package(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        vdm.sqlalchemy.SQLAlchemyMixin
        ):

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)


class Tag(vdm.sqlalchemy.SQLAlchemyMixin):
    def __init__(self, name):
        self.name = name


class PackageTag(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        vdm.sqlalchemy.SQLAlchemyMixin
        ):
    def __init__(self, package=None, tag=None, state=None, **kwargs):
        logger.debug('PackageTag.__init__: %s, %s' % (package, tag))
        self.package = package
        self.tag = tag
        self.state = state
        for k,v in kwargs.items():
            setattr(self, k, v)


## --------------------------------------------------------
## Mapper Stuff

from sqlalchemy.orm import scoped_session, sessionmaker, create_session
from sqlalchemy.orm import relation, backref
# both options now work
# Session = scoped_session(sessionmaker(autoflush=False, transactional=True))
# this is the more testing one ...
if sqla_version <= '0.4.99':
    Session = scoped_session(sessionmaker(autoflush=True, transactional=True))
else:
    Session = scoped_session(sessionmaker(autoflush=True,
                                          expire_on_commit=False,
                                          autocommit=False))

# mapper = Session.mapper
from sqlalchemy.orm import mapper

# VDM-specific domain objects
State = vdm.sqlalchemy.State
Revision = vdm.sqlalchemy.make_Revision(mapper, revision_table)

mapper(License, license_table, properties={
    },
    extension=vdm.sqlalchemy.Revisioner(license_revision_table)
    )

mapper(Package, package_table, properties={
    'license':relation(License),
    # delete-orphan on cascade does NOT work!
    # Why? Answer: because of way SQLAlchemy/our code works there are points
    # where PackageTag object is created *and* flushed but does not yet have
    # the package_id set (this cause us other problems ...). Some time later a
    # second commit happens in which the package_id is correctly set.
    # However after first commit PackageTag does not have Package and
    # delete-orphan kicks in to remove it!
    #
    # do we want lazy=False here? used in:
    # <http://www.sqlalchemy.org/trac/browser/sqlalchemy/trunk/examples/association/proxied_association.py>
    'package_tags':relation(PackageTag, backref='package', cascade='all'), #, delete-orphan'),
    },
    extension = vdm.sqlalchemy.Revisioner(package_revision_table)
    )

mapper(Tag, tag_table)

mapper(PackageTag, package_tag_table, properties={
    'tag':relation(Tag),
    },
    extension = vdm.sqlalchemy.Revisioner(package_tag_revision_table)
    )

vdm.sqlalchemy.modify_base_object_mapper(Package, Revision, State)
vdm.sqlalchemy.modify_base_object_mapper(License, Revision, State)
vdm.sqlalchemy.modify_base_object_mapper(PackageTag, Revision, State)
PackageRevision = vdm.sqlalchemy.create_object_version(mapper, Package,
        package_revision_table)
LicenseRevision = vdm.sqlalchemy.create_object_version(mapper, License,
        license_revision_table)
PackageTagRevision = vdm.sqlalchemy.create_object_version(mapper, PackageTag,
        package_tag_revision_table)

from base import add_stateful_versioned_m2m
vdm.sqlalchemy.add_stateful_versioned_m2m(Package, PackageTag, 'tags', 'tag',
        'package_tags')
vdm.sqlalchemy.add_stateful_versioned_m2m_on_version(PackageRevision, 'tags')

## ------------------------
## Repository helper object

from tools import Repository
repo = Repository(metadata, Session,
        versioned_objects = [ Package, License,  PackageTag ]
        )

