# TODO: in pylons 0.9.6 models -> model
# need to finish off converting to this new module layout

#from ckan.models import *   # Old sqlobject vdm code.
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

from pylons import config
from sqlalchemy import Column, MetaData, Table, types, ForeignKey
from sqlalchemy import orm
from sqlalchemy import or_
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

mapper = Session.mapper

import vdm.sqlalchemy

## VDM-specific tables

state_table = vdm.sqlalchemy.make_state_table(metadata)
revision_table = vdm.sqlalchemy.make_revision_table(metadata)

## Our Domain Object Tables

license_table = Table('license', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('name', types.Unicode(100)),
        )

package_table = Table('package', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('name', types.Unicode(100), unique=True),
        Column('title', types.UnicodeText),
        Column('url', types.UnicodeText),
        Column('download_url', types.UnicodeText),
        Column('notes', types.UnicodeText),
        Column('license_id', types.Integer, ForeignKey('license.id')),
)

tag_table = Table('tag', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('name', types.Unicode(100), unique=True),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('package_id', types.Integer, ForeignKey('package.id')),
        Column('tag_id', types.Integer, ForeignKey('tag.id')),
        )


vdm.sqlalchemy.make_table_stateful(license_table)
vdm.sqlalchemy.make_table_stateful(package_table)
vdm.sqlalchemy.make_table_stateful(package_tag_table)
package_revision_table = vdm.sqlalchemy.make_table_revisioned(package_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = vdm.sqlalchemy.make_table_revisioned(package_tag_table)


## -------------------
## Mapped classes

class DomainObject(object):
    
    text_search_fields = []

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
    
    # TODO: remove once refactoring is done 2008-09-29 
    @classmethod
    def byName(self, name):
        return self.by_name(name)

    @classmethod
    def by_name(self, name):
        obj = self.query.filter_by(name=name).first()
        return obj

    @classmethod
    def text_search(self, query, term):
        register = self
        make_like = lambda x,y: x.ilike('%' + y + '%')
        q = None
        for field in self.text_search_fields:
            attr = getattr(register, field)
            q = or_(q, make_like(attr, term))
        return query.filter(q)

    def purge(self):
        sess = orm.object_session(self)
        if hasattr(self, '__revisioned__'): # only for versioned objects ...
            # this actually should auto occur due to cascade relationships but
            # ...
            for rev in self.all_revisions:
                sess.delete(rev)
        sess.delete(self)

    def __str__(self):
        repr = u'<%s' % self.__class__.__name__
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            repr += u' %s=%s' % (col.name, getattr(self, col.name))
        repr += '>'
        return repr

    def __repr__(self):
        return self.__str__()

        
class License(DomainObject):
    pass


class Package(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    
    text_search_fields = ['name', 'title']

    @classmethod
    def search_by_name(self, text_query):
        text_query = text_query
        return self.query.filter(self.name.contains(text_query.lower()))

    def add_tag_by_name(self, tagname):
        if not tagname:
            return
        tag = Tag.byName(tagname)
        if not tag:
            tag = Tag(name=tagname)
        if not tag in self.tags:
            self.tags.append(tag)

    def drop_tag_by_name(self, tagname):
        tag = Tag.by_name(tagname)
        # TODO:
        # self.tags.delete(tag=tag)
        pass


class Tag(DomainObject):
    def __init__(self, name):
        self.name = name

    # not versioned so same as purge
    def delete(self):
        self.purge()

    @classmethod
    def search_by_name(self, text_query):
        text_query = text_query.strip().lower()
        return self.query.filter(self.name.contains(text_query))

    def __repr__(self):
        return '<Tag %s>' % self.name


class PackageTag(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    def __init__(self, package=None, tag=None, state=None, **kwargs):
        self.package = package
        self.tag = tag
        self.state = state
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<PackageTag %s %s>' % (self.package, self.tag)

# API Key
# import apikey # TODO: see apikey.py
import uuid

def make_uuid():
    return str(uuid.uuid4())

apikey_table = Table('apikey', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('name', types.UnicodeText),
        Column('key', types.String(36), default=make_uuid)
        )

class ApiKey(DomainObject):
    pass

mapper(ApiKey, apikey_table,
    order_by=apikey_table.c.id)


# VDM-specific domain objects
State = vdm.sqlalchemy.make_State(mapper, state_table)
Revision = vdm.sqlalchemy.make_Revision(mapper, revision_table)

mapper(License, license_table,
    order_by=license_table.c.id)

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
    'package_tags':relation(PackageTag, backref='package',
        cascade='all, delete', #, delete-orphan',
        lazy=False)
    },
    order_by=package_table.c.name,
    extension = vdm.sqlalchemy.Revisioner(package_revision_table)
    )

mapper(Tag, tag_table,
    order_by=tag_table.c.name)

mapper(PackageTag, package_tag_table, properties={
    'tag':relation(Tag, backref='package_tags'),
    },
    order_by=package_tag_table.c.id,
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

# TODO: move this onto the repo object
def create_db():
    metadata.create_all()

# create default data as well
def init_db():
    metadata.create_all()
    if len(State.query.all()) == 0:
        ACTIVE, DELETED = vdm.sqlalchemy.make_states(Session())
    for name in license_names:
        if not License.by_name(name):
            License(name=name)
    if Revision.query.count() == 0:
        rev = Revision()
        rev.author = 'system'
        rev.message = u'Initialising the Repository'
    Session.commit()
    Session.remove()

def rebuild_db():
    metadata.drop_all()
    init_db()

def new_revision():
    '''Convenience method to create new revision and set it on session.'''
    rev = Revision()
    vdm.sqlalchemy.set_revision(Session, rev)
    return rev

from license import LicenseList
license_names = LicenseList.all_formatted

# TODO: here for backwards compatability with v0.6 but should remove at some
# point
class Repository(object):
    def begin_transaction(self):
        # do *not* call begin again as we are automatically within a
        # transaction at all times as session was set up as transactional
        # (every commit is paired with a begin)
        # <http://groups.google.com/group/sqlalchemy/browse_thread/thread/a54ce150b33517db/17587ca675ab3674>
        # Session.begin()
        rev = new_revision()
        self.revision = rev
        return rev

    def begin(self):
        return self.begin_transaction()

    def commit(self):
        self.revision = None
        try:
            Session.commit()
        except:
            Session.rollback()
            Session.remove()
            raise

    def history(self):
        active = State.query.filter_by(name='active').one()
        return Revision.query.filter_by(state=active).all()

    def youngest_revision(self):
        return Revision.youngest()

repo = Repository()
