import datetime

from meta import *
from core import *
from sqlalchemy.orm import eagerload_all
from domain_object import DomainObject
from package import *
from types import make_uuid
import vdm.sqlalchemy
from ckan.model import extension
from sqlalchemy.ext.associationproxy import association_proxy

__all__ = ['group_table', 'Group', 'package_revision_table',
           'Member', 'GroupRevision', 'MemberRevision',
           'member_revision_table', 'member_table']

member_table = Table('member', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('table_name', UnicodeText, nullable=False),
    Column('table_id', UnicodeText, nullable=False),
    Column('capacity', UnicodeText, nullable=False),
    Column('group_id', UnicodeText, ForeignKey('group.id')),
    )
    
vdm.sqlalchemy.make_table_stateful(member_table)
member_revision_table = make_revisioned_table(member_table)

group_table = Table('group', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('name', UnicodeText, nullable=False, unique=True),
    Column('title', UnicodeText),
    Column('type', UnicodeText, nullable=False),
    Column('description', UnicodeText),
    Column('created', DateTime, default=datetime.datetime.now),
    )

vdm.sqlalchemy.make_table_stateful(group_table)
group_revision_table = make_revisioned_table(group_table)


class Member(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    def __init__(self, group=None, table_id=None, group_id=None,
                 table_name=None, capacity='member', state='active'):
        self.group = group
        self.group_id = group_id
        self.table_id = table_id
        self.table_name = table_name
        self.capacity = capacity
        self.state = state
        
    def related_packages(self):
        # TODO do we want to return all related packages or certain ones?
        return Session.query(Package).filter_by(id=self.table_id).all()

class Group(vdm.sqlalchemy.RevisionedObjectMixin,
            vdm.sqlalchemy.StatefulObjectMixin,
            DomainObject):
    def __init__(self, name=u'', title=u'', description=u'', type=u'group'):
        self.name = name
        self.title = title
        self.description = description
        self.type = type

    @property
    def display_name(self):
        if self.title is not None and len(self.title):
            return self.title
        else:
            return self.name

    @classmethod
    def get(cls, reference):
        '''Returns a group object referenced by its id or name.'''
        query = Session.query(cls).filter(cls.id==reference)
        group = query.first()
        if group == None:
            group = cls.by_name(reference)
        return group
    # Todo: Make sure group names can't be changed to look like group IDs?

    def active_packages(self, load_eager=True):
        query = Session.query(Package).\
               filter_by(state=vdm.sqlalchemy.State.ACTIVE).\
               filter(group_table.c.id == self.id).\
               filter(member_table.c.state == 'active').\
               join(member_table, member_table.c.table_id == Package.id).\
               join(group_table, group_table.c.id == member_table.c.group_id)
        return query

    @classmethod
    def search_by_name(cls, text_query):
        text_query = text_query.strip().lower()
        return Session.query(cls).filter(cls.name.contains(text_query))

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
        if not package in self.active_packages().all():
            member = Member(group=self, table_id=package.id, table_name='package')
            Session.add(member)


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
        for class_ in [Member, GroupExtra]:
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


mapper(Group, group_table, 
       extension=[vdm.sqlalchemy.Revisioner(group_revision_table),],
)

vdm.sqlalchemy.modify_base_object_mapper(Group, Revision, State)
GroupRevision = vdm.sqlalchemy.create_object_version(mapper, Group,
        group_revision_table)

mapper(Member, member_table, properties={
    'group': relation(Group,
        backref=backref('member_all', cascade='all, delete-orphan')
    ),
},
    extension=[vdm.sqlalchemy.Revisioner(member_revision_table),],
)


vdm.sqlalchemy.modify_base_object_mapper(Member, Revision, State)
MemberRevision = vdm.sqlalchemy.create_object_version(mapper, Member,
        member_revision_table)

#TODO
MemberRevision.related_packages = lambda self: [self.continuity.package]


