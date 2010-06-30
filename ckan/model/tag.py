from types import make_uuid

from meta import *
import vdm.sqlalchemy
from core import *
from domain_object import DomainObject
from package import Package
import full_search

__all__ = ['tag_table', 'package_tag_table', 'Tag', 'PackageTag',
           'PackageTagRevision']

tag_table = Table('tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.Unicode(100), unique=True, nullable=False),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', types.UnicodeText, ForeignKey('package.id')),
        Column('tag_id', types.UnicodeText, ForeignKey('tag.id')),
        )

vdm.sqlalchemy.make_table_stateful(package_tag_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = vdm.sqlalchemy.make_revisioned_table(package_tag_table)

class Tag(DomainObject):
    def __init__(self, name=''):
        self.name = name

    # not stateful so same as purge
    def delete(self):
        self.purge()

    @classmethod
    def search_by_name(self, text_query):
        text_query = text_query.strip().lower()
        return Session.query(self).filter(self.name.contains(text_query))

    @property
    def packages_ordered(self):
        ourcmp = lambda pkg1, pkg2: cmp(pkg1.name, pkg2.name)
        return sorted(self.packages, cmp=ourcmp)

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


mapper(Tag, tag_table, properties={
    'package_tags':relation(PackageTag, backref='tag',
        cascade='all, delete, delete-orphan',
        )
    },
    order_by=tag_table.c.name,
    )

mapper(PackageTag, package_tag_table, properties={
    },
    order_by=package_tag_table.c.id,
    extension = [vdm.sqlalchemy.Revisioner(package_tag_revision_table),
                 full_search.SearchVectorTrigger()],
    )

from package_mapping import *

vdm.sqlalchemy.modify_base_object_mapper(PackageTag, Revision, State)
PackageTagRevision = vdm.sqlalchemy.create_object_version(mapper, PackageTag,
        package_tag_revision_table)


from vdm.sqlalchemy.base import add_stateful_versioned_m2m 
vdm.sqlalchemy.add_stateful_versioned_m2m(Package, PackageTag, 'tags', 'tag',
        'package_tags')
vdm.sqlalchemy.add_stateful_versioned_m2m_on_version(PackageRevision, 'tags')
vdm.sqlalchemy.add_stateful_versioned_m2m(Tag, PackageTag, 'packages', 'package',
        'package_tags')
