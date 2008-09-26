# TODO: in pylons 0.9.6 models -> model
# need to finish off converting to this new module layout

#from ckan.models import *   # Old sqlobject vdm code.

from pylons import config
from sqlalchemy import Column, MetaData, Table, types, ForeignKey
from sqlalchemy import orm
from sqlalchemy import or_
from sqlalchemy.types import *

# Instantiate meta data manager.
metadata = MetaData()

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

mapper = Session.mapper

from datetime import datetime
import logging
logger = logging.getLogger(__name__)

import vdm.sqlalchemy

## VDM-specific tables

state_table = vdm.sqlalchemy.make_state_table(metadata)
revision_table = vdm.sqlalchemy.make_revision_table(metadata)

## Demo tables

license_table = Table('license', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('open', Boolean),
        )

package_table = Table('package', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
        Column('title', String(100)),
        Column('license_id', Integer, ForeignKey('license.id')),
)

tag_table = Table('tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('name', String(100)),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', Integer, primary_key=True),
        Column('package_id', Integer, ForeignKey('package.id')),
        Column('tag_id', Integer, ForeignKey('tag.id')),
        )


vdm.sqlalchemy.make_table_stateful(license_table)
vdm.sqlalchemy.make_table_stateful(package_table)
vdm.sqlalchemy.make_table_stateful(tag_table)
vdm.sqlalchemy.make_table_stateful(package_tag_table)
package_revision_table = vdm.sqlalchemy.make_table_revisioned(package_table)
tag_revision_table = vdm.sqlalchemy.make_table_revisioned(tag_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = vdm.sqlalchemy.make_table_revisioned(package_tag_table)


## -------------------
## Mapped classes

class DomainObject(object):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def delete(self):
        # sess = orm.object_session(self)
        # print self, sess
        Session.delete(self)

    @classmethod
    def byName(self, name):
        obj = self.query.filter_by(name=name).first()
        return obj
        
class License(DomainObject):
    pass

class Package(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin):
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<Package %s>' % self.name

class Tag(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<Tag %s>' % self.name

class PackageTag(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin):
    def __init__(self, package=None, tag=None, state=None, **kwargs):
        logger.debug('PackageTag.__init__: %s, %s' % (package, tag))
        self.package = package
        self.tag = tag
        self.state = state
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<PackageTag %s %s>' % (self.package, self.tag)


# VDM-specific domain objects
State = vdm.sqlalchemy.make_State(mapper, state_table)
Revision = vdm.sqlalchemy.make_Revision(mapper, revision_table)

mapper(License, license_table)

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
    'package_tags':relation(PackageTag, cascade='all'), #, delete-orphan'),
    },
    extension = vdm.sqlalchemy.Revisioner(package_revision_table)
    )

mapper(Tag, tag_table)

mapper(PackageTag, package_tag_table, properties={
    'package':relation(Package),
    'tag':relation(Tag),
    },
    extension = vdm.sqlalchemy.Revisioner(package_tag_revision_table)
    )

vdm.sqlalchemy.modify_base_object_mapper(Package, Revision, State)
vdm.sqlalchemy.modify_base_object_mapper(PackageTag, Revision, State)
PackageRevision = vdm.sqlalchemy.create_object_version(mapper, Package,
        package_revision_table)
PackageTagRevision = vdm.sqlalchemy.create_object_version(mapper, PackageTag,
        package_tag_revision_table)

from vdm.sqlalchemy.base import add_stateful_versioned_m2m 
vdm.sqlalchemy.add_stateful_versioned_m2m(Package, PackageTag, 'tags', 'tag',
        'package_tags')
vdm.sqlalchemy.add_stateful_versioned_m2m_on_version(PackageRevision, 'tags')

