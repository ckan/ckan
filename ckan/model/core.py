from meta import *

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
        Column('name', types.Unicode(100), unique=True, nullable=False),
        Column('title', types.UnicodeText),
        Column('version', types.Unicode(100)),
        Column('url', types.UnicodeText),
        Column('download_url', types.UnicodeText),
        Column('author', types.UnicodeText),
        Column('author_email', types.UnicodeText),
        Column('maintainer', types.UnicodeText),
        Column('maintainer_email', types.UnicodeText),                      
        Column('notes', types.UnicodeText),
        Column('license_id', types.Integer, ForeignKey('license.id')),
)

tag_table = Table('tag', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('name', types.Unicode(100), unique=True, nullable=False),
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

# TODO: replace this (or at least inherit from) standard SqlalchemyMixin in vdm
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

    def isopen(self):
        if self.license and \
            (self.license.name.startswith('OKD Compliant')
                or
                self.license.name.startswith('OSI Approved')):
            return True
        return False


class Tag(DomainObject):
    def __init__(self, name=''):
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

