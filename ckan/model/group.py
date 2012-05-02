import datetime

from meta import *
from core import *
from sqlalchemy.orm import eagerload_all
from domain_object import DomainObject
from package import *
from types import make_uuid
import vdm.sqlalchemy
from ckan.model import extension, User
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
    Column('image_url', UnicodeText),
    Column('created', DateTime, default=datetime.datetime.now),
    Column('approval_status', UnicodeText, default=u"approved"),
    )

vdm.sqlalchemy.make_table_stateful(group_table)
group_revision_table = make_revisioned_table(group_table)


class Member(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    def __init__(self, group=None, table_id=None, group_id=None,
                 table_name=None, capacity='public', state='active'):
        self.group = group
        self.group_id = group_id
        self.table_id = table_id
        self.table_name = table_name
        self.capacity = capacity
        self.state = state

    @classmethod
    def get(cls, reference):
        '''Returns a group object referenced by its id or name.'''
        query = Session.query(cls).filter(cls.id==reference)
        member = query.first()
        if member == None:
            member = cls.by_name(reference)
        return member


    def get_related(self, type):
        """ TODO: Determine if this is useful
            Get all objects that are members of the group of the specified type.

            Should the type be used to get table_name or should we use the one in
            the constructor
        """
        pass

    def related_packages(self):
        # TODO do we want to return all related packages or certain ones?
        return Session.query(Package).filter_by(id=self.table_id).all()

class Group(vdm.sqlalchemy.RevisionedObjectMixin,
            vdm.sqlalchemy.StatefulObjectMixin,
            DomainObject):

    def __init__(self, name=u'', title=u'', description=u'', image_url=u'',
                 type=u'group', approval_status=u'approved'):
        self.name = name
        self.title = title
        self.description = description
        self.image_url = image_url
        self.type = type
        self.approval_status= approval_status

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

    @classmethod
    def all(cls, group_type=None, state=('active',)):
        """
        Returns all groups.
        """
        q = Session.query(cls)
        if state:
            q = q.filter(cls.state.in_(state))

        if group_type:
            q = q.filter(cls.type==group_type)

        return q.order_by(cls.title)

    def set_approval_status(self, status):
        """
            Aproval status can be set on a group, where currently it does
            nothing other than act as an indication of whether it was
            approved or not. It may be that we want to tie the object
            status to the approval status
        """
        assert status in ["approved", "pending", "denied"]
        self.approval_status = status
        if status == "denied":
            pass

    def members_of_type(self, object_type, capacity=None):
        from ckan import model
        object_type_string = object_type.__name__.lower()
        query = Session.query(object_type).\
               filter(model.Group.id == self.id).\
               filter(model.Member.state == 'active').\
               filter(model.Member.table_name == object_type_string)

        if hasattr(object_type,'state'):
            query = query.filter(object_type.state == 'active' )

        if capacity:
            query = query.filter(model.Member.capacity == capacity)

        query = query.join(model.Member, member_table.c.table_id == getattr(object_type,'id') ).\
               join(model.Group, group_table.c.id == member_table.c.group_id)

        return query

    def add_child(self, object_instance):
        object_type_string = object_instance.__class__.__name__.lower()
        if not object_instance in self.members_of_type(object_instance.__class__).all():
            member = Member(group=self, table_id=getattr(object_instance,'id'), table_name=object_type_string)
            Session.add(member)

    def get_children_groups(self, type='group'):
        # Returns a list of dicts where each dict contains "id", "name", and "title"
        # When querying with a CTE specifying a model in the query parameter causes
        # problems as it returns only the first level deep apparently not recursing
        # any deeper than that.  If we simplify and request only specific fields then
        # if returns the full depth of the hierarchy.
        results = Session.query("id","name", "title").\
                from_statement(HIERARCHY_CTE).params(id=self.id, type=type).all()
        return [ { "id":idf, "name": name, "title": title } for idf,name,title in results ]

    def active_packages(self, load_eager=True, with_private=False):
        query = Session.query(Package).\
               filter_by(state=vdm.sqlalchemy.State.ACTIVE).\
               filter(group_table.c.id == self.id).\
               filter(member_table.c.state == 'active')

        if not with_private:
               query = query.filter(member_table.c.capacity == 'public')

        query = query.join(member_table, member_table.c.table_id == Package.id).\
               join(group_table, group_table.c.id == member_table.c.group_id)

        return query

    @classmethod
    def search_by_name(cls, text_query, group_type=None):
        text_query = text_query.strip().lower()
        if not group_type:
            q = Session.query(cls).filter(cls.name.contains(text_query))
        else:
            q = Session.query(cls).filter(cls.name.contains(text_query)).filter(cls.type==group_type)
        return q.order_by(cls.title)

    def as_dict(self, ref_package_by='name'):
        _dict = DomainObject.as_dict(self)
        _dict['packages'] = [getattr(package, ref_package_by) for package in self.packages]
        _dict['extras'] = dict([(key, value) for key, value in self.extras.items()])
        if ( self.type == 'organization' ):
            _dict['users'] = [getattr(user, "name") for user in self.members_of_type(User)]
        return _dict

    def add_package_by_name(self, package_name):
        if not package_name:
            return
        package = Package.by_name(package_name)
        assert package
        if not package in self.members_of_type( package.__class__ ).all():
            member = Member(group=self, table_id=package.id, table_name='package')
            Session.add(member)

    def get_groups(self, group_type=None, capacity=None):
        """ Get all groups that this group is within """
        import ckan.model as model
        if '_groups' not in self.__dict__:
            self._groups = model.Session.query(model.Group).\
               join(model.Member, model.Member.group_id == model.Group.id and \
                    model.Member.table_name == 'group').\
               filter(model.Member.state == 'active').\
               filter(model.Member.table_id == self.id).all()

        groups = self._groups
        if group_type:
            groups = [g for g in groups if g.type == group_type]
        if capacity:
            groups = [g for g in groups if g.capacity == capacity]
        return groups



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

HIERARCHY_CTE =  """
    WITH RECURSIVE subtree(id) AS (
        SELECT M.* FROM public.member AS M
        WHERE M.table_name = 'group' AND M.state = 'active'
        UNION
        SELECT M.* FROM public.member M, subtree SG
        WHERE M.table_id = SG.group_id AND M.table_name = 'group' AND M.state = 'active')

    SELECT G.* FROM subtree AS ST
    INNER JOIN public.group G ON G.id = ST.table_id
    WHERE group_id = :id AND G.type = :type and table_name='group'
"""
