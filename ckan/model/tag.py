from sqlalchemy.orm import eagerload_all
from sqlalchemy import and_
import vdm.sqlalchemy

from types import make_uuid
from meta import *
from domain_object import DomainObject
from package import Package
from core import *
import activity

__all__ = ['tag_table', 'package_tag_table', 'Tag', 'PackageTag',
           'PackageTagRevision', 'package_tag_revision_table',
           'MAX_TAG_LENGTH', 'MIN_TAG_LENGTH']

MAX_TAG_LENGTH = 100
MIN_TAG_LENGTH = 2

tag_table = Table('tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.Unicode(MAX_TAG_LENGTH), nullable=False, unique=True),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', types.UnicodeText, ForeignKey('package.id')),
        Column('tag_id', types.UnicodeText, ForeignKey('tag.id')),
        )

vdm.sqlalchemy.make_table_stateful(package_tag_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = make_revisioned_table(package_tag_table)

class Tag(DomainObject):
    def __init__(self, name=''):
        self.name = name

    # not stateful so same as purge
    def delete(self):
        self.purge()

    @classmethod
    def get(cls, reference):
        '''Returns a tag object referenced by its id or name.'''
        query = Session.query(cls).filter(cls.id==reference)
        query = query.options(eagerload_all('package_tags'))
        tag = query.first()
        if tag == None:
            tag = cls.by_name(reference)
        return tag
    # Todo: Make sure tag names can't be changed to look like tag IDs?

    @classmethod
    def search_by_name(cls, text_query):
        text_query = text_query.strip().lower()
        q = Session.query(cls).filter(cls.name.contains(text_query))
        q = q.distinct().join(cls.package_tags)
        return q
        
    #@classmethod
    #def by_name(self, name, autoflush=True):
    #    q = Session.query(self).autoflush(autoflush).filter_by(name=name)
    #    q = q.distinct().join(self.package_tags)
    #    return q.first()
        
    @classmethod
    def all(cls):
        q = Session.query(cls)
        q = q.distinct().join(PackageTagRevision)
        q = q.filter(and_(
            PackageTagRevision.state == 'active', PackageTagRevision.current == True
        ))
        return q

    @property
    def packages_ordered(self):
        q = Session.query(Package)
        q = q.join(PackageTagRevision)
        q = q.filter(PackageTagRevision.tag_id == self.id)
        q = q.filter(and_(
            PackageTagRevision.state == 'active', PackageTagRevision.current == True
        ))
        packages = [p for p in q]
        ourcmp = lambda pkg1, pkg2: cmp(pkg1.name, pkg2.name)
        return sorted(packages, cmp=ourcmp)

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
        return '<PackageTag package=%s tag=%s>' % (self.package.name, self.tag.name)

    def activity_stream_detail(self, activity_id, activity_type):
        if activity_type == 'new':
            # New PackageTag objects are recorded as 'added tag' activities.
            activity_type = 'added'
        elif activity_type == 'changed':
            # Changed PackageTag objects are recorded as 'removed tag'
            # activities.
            # FIXME: This assumes that whenever a PackageTag is changed it's
            # because its' state has been changed from 'active' to 'deleted'.
            # Should do something more here to test whether that is in fact
            # what has changed.
            activity_type = 'removed'
        else:
            return None

        # Return an 'added tag' or 'removed tag' activity.
        import ckan.lib.dictization
        import ckan.model
        c = {'model': ckan.model}
        d = {'tag': ckan.lib.dictization.table_dictize(self.tag, c),
            'package': ckan.lib.dictization.table_dictize(self.package, c)}
        return activity.ActivityDetail(
            activity_id=activity_id,
            object_id=self.id,
            object_type='tag',
            activity_type=activity_type,
            data=d)

    @classmethod
    def by_name(self, package_name, tag_name, autoflush=True):
        q = Session.query(self).autoflush(autoflush).\
            join('package').filter(Package.name==package_name).\
            join('tag').filter(Tag.name==tag_name)
        assert q.count() <= 1, q.all()
        return q.first()

    def related_packages(self):
        return [self.package]

mapper(Tag, tag_table, properties={
    'package_tags':relation(PackageTag, backref='tag',
        cascade='all, delete, delete-orphan',
        ),
    },
    order_by=tag_table.c.name,
    )

mapper(PackageTag, package_tag_table, properties={
    'pkg':relation(Package, backref='package_tag_all',
        cascade='none',
        )
    },
    order_by=package_tag_table.c.id,
    extension=[vdm.sqlalchemy.Revisioner(package_tag_revision_table),
               extension.PluginMapperExtension(),
               ],
    )

from package_mapping import *

vdm.sqlalchemy.modify_base_object_mapper(PackageTag, Revision, State)
PackageTagRevision = vdm.sqlalchemy.create_object_version(mapper, PackageTag,
        package_tag_revision_table)

PackageTagRevision.related_packages = lambda self: [self.continuity.package]

from vdm.sqlalchemy.base import add_stateful_versioned_m2m 
vdm.sqlalchemy.add_stateful_versioned_m2m(Package, PackageTag, 'tags', 'tag',
        'package_tags')
vdm.sqlalchemy.add_stateful_versioned_m2m_on_version(PackageRevision, 'tags')
vdm.sqlalchemy.add_stateful_versioned_m2m(Tag, PackageTag, 'packages', 'package',
        'package_tags')
