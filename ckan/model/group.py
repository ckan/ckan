from datetime import datetime

from meta import *
from core import *
from sqlalchemy.orm import eagerload_all
from domain_object import DomainObject
from package import *
from types import make_uuid
import vdm.sqlalchemy
from ckan.model import extension

__all__ = ['group_table', 'Group', 'package_revision_table',
           'PackageGroup', 'GroupRevision', 'PackageGroupRevision']

package_group_table = Table('package_group', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('package_id', UnicodeText, ForeignKey('package.id')),
    Column('group_id', UnicodeText, ForeignKey('group.id')),
    )
    
vdm.sqlalchemy.make_table_stateful(package_group_table)
package_group_revision_table = vdm.sqlalchemy.make_revisioned_table(package_group_table)

group_table = Table('group', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('name', UnicodeText, nullable=False),
    Column('title', UnicodeText),
    Column('description', UnicodeText),
    Column('created', DateTime, default=datetime.now),
    )

vdm.sqlalchemy.make_table_stateful(group_table)
group_revision_table = vdm.sqlalchemy.make_revisioned_table(group_table)


class PackageGroup(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    pass

class Group(vdm.sqlalchemy.RevisionedObjectMixin,
            vdm.sqlalchemy.StatefulObjectMixin,
            DomainObject):
    def __init__(self, name=u'', title=u'', description=u''):
        self.name = name
        self.title = title
        self.description = description

    # not versioned
    def delete(self):
        self.purge()

    def active_packages(self, load_eager=True):
        query = Session.query(Package).\
               filter_by(state=vdm.sqlalchemy.State.ACTIVE).\
               join('groups').filter_by(id=self.id)
        if load_eager:
            query = query.options(eagerload_all('package_tags.tag'))
            query = query.options(eagerload_all('package_resources_all'))
        return query

    @classmethod
    def search_by_name(self, text_query):
        text_query = text_query.strip().lower()
        return Session.query(self).filter(self.name.contains(text_query))

    def as_dict(self, ref_package_by='name'):
        _dict = DomainObject.as_dict(self)
        _dict['packages'] = [getattr(package, ref_package_by) for package in self.packages]
        _dict['extras'] = dict([(key, value) for key, value in self.extras.items()])
        return _dict

    def add_package_by_name(self, package_name):
        if not package_name:
            return
        package = Package.by_name(package_name)
        assert package
        if not package in self.packages:
            self.packages.append(package)

    @property
    def all_related_revisions(self):
        '''Returns chronological list of all object revisions related to
        this group. Ordered by most recent first.
        '''
        results = {}
        from group_extra import GroupExtra
        for grp_rev in self.all_revisions:
            if not results.has_key(grp_rev.revision):
                results[grp_rev.revision] = []
            results[grp_rev.revision].append(grp_rev)
        for class_ in [PackageGroup, GroupExtra]:
            rev_class = class_.__revision_class__
            obj_revisions = Session.query(rev_class).filter_by(group_id=self.id).all()
            for obj_rev in obj_revisions:
                if not results.has_key(obj_rev.revision):
                    results[obj_rev.revision] = []
                results[obj_rev.revision].append(obj_rev)
        result_list = results.items()
        ourcmp = lambda rev_tuple1, rev_tuple2: \
                 cmp(rev_tuple2[0].timestamp, rev_tuple1[0].timestamp)
        return sorted(result_list, cmp=ourcmp)

    def __repr__(self):
        return '<Group %s>' % self.name


mapper(Group, group_table, properties={
    'packages': relation(Package, secondary=package_group_table,
        backref='groups',
        order_by=package_table.c.name
    )},
    extension=[vdm.sqlalchemy.Revisioner(group_revision_table),],
)


vdm.sqlalchemy.modify_base_object_mapper(Group, Revision, State)
GroupRevision = vdm.sqlalchemy.create_object_version(mapper, Group,
        group_revision_table)


mapper(PackageGroup, package_group_table,
    extension=[vdm.sqlalchemy.Revisioner(package_group_revision_table),],
)


vdm.sqlalchemy.modify_base_object_mapper(PackageGroup, Revision, State)
PackageGroupRevision = vdm.sqlalchemy.create_object_version(mapper, PackageGroup,
        package_group_revision_table)


from vdm.sqlalchemy.base import add_stateful_versioned_m2m 
#vdm.sqlalchemy.add_stateful_versioned_m2m(Package, PackageGroup, 'groups', 'group',
#        'package_group')
vdm.sqlalchemy.add_stateful_versioned_m2m_on_version(GroupRevision, 'groups')
vdm.sqlalchemy.add_stateful_versioned_m2m(Group, PackageGroup, 'groups', 'group',
        'package_group')
