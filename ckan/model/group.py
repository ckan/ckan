# encoding: utf-8
from __future__ import annotations

import datetime
from typing import (
    Any, Optional, Union, overload
)
from typing_extensions import Literal, Self

from sqlalchemy import column, orm, types, Column, Table, ForeignKey, or_, and_, text
from sqlalchemy.ext.associationproxy import AssociationProxy

import ckan.model.meta as meta
import ckan.model.core as core
import ckan.model.package as _package
import ckan.model.types as _types
import ckan.model.domain_object as domain_object
import ckan.model.package as _package

from ckan.types import Context, Query

__all__ = ['group_table', 'Group',
           'Member',
           'member_table']


member_table = Table('member', meta.metadata,
                     Column('id', types.UnicodeText,
                            primary_key=True,
                            default=_types.make_uuid),
                     Column('table_name', types.UnicodeText,
                            nullable=False),
                     Column('table_id', types.UnicodeText,
                            nullable=False),
                     Column('capacity', types.UnicodeText,
                            nullable=False),
                     Column('group_id', types.UnicodeText,
                            ForeignKey('group.id')),
                     Column('state', types.UnicodeText,
                            default=core.State.ACTIVE),
                     )


group_table = Table('group', meta.metadata,
                    Column('id', types.UnicodeText,
                           primary_key=True,
                           default=_types.make_uuid),
                    Column('name', types.UnicodeText,
                           nullable=False, unique=True),
                    Column('title', types.UnicodeText),
                    Column('type', types.UnicodeText,
                           nullable=False),
                    Column('description', types.UnicodeText),
                    Column('image_url', types.UnicodeText),
                    Column('created', types.DateTime,
                           default=datetime.datetime.now),
                    Column('is_organization', types.Boolean, default=False),
                    Column('approval_status', types.UnicodeText,
                           default=u"approved"),
                    Column('state', types.UnicodeText,
                           default=core.State.ACTIVE),
                    )


class Member(core.StatefulObjectMixin,
             domain_object.DomainObject):
    '''A Member object represents any other object being a 'member' of a
    particular Group.

    Meanings:
    * Package - the Group is a collection of Packages
                 - capacity is 'public', 'private'
                   or 'organization' if the Group is an Organization
                   (see ckan.logic.action.package_owner_org_update)
    * User - the User is granted permissions for the Group
                 - capacity is 'admin', 'editor' or 'member'
    * Group - the Group (Member.group_id) is a parent of the Group (Member.id)
              in a hierarchy.
                 - capacity is 'parent'
    '''
    id: str
    table_name: Optional[str]
    table_id: Optional[str]
    capacity: str
    group_id: Optional[str]
    state: str

    group: Optional['Group']

    def __init__(self, group: Optional['Group']=None,
                 table_id: Optional[str]=None, group_id: Optional[str]=None,
                 table_name: Optional[str]=None, capacity: str='public',
                 state: str='active') -> None:
        self.group = group

        self.group_id = group_id
        self.table_id = table_id
        self.table_name = table_name
        self.capacity = capacity
        self.state = state

    @classmethod
    def get(cls, reference: str) -> Optional["Member"]:
        '''Returns a group object referenced by its id or name.'''
        if not reference:
            return None

        member = meta.Session.query(cls).get(reference)
        if member is None:
            member = cls.by_name(reference)
        return member

    def related_packages(self) -> list[_package.Package]:
        # TODO do we want to return all related packages or certain ones?
        return meta.Session.query(_package.Package).filter_by(
            id=self.table_id).all()

    def __str__(self):
        # refer to objects by name, not ID, to help debugging
        if self.table_name == 'package':
            pkg = meta.Session.query(_package.Package).get(self.table_id)
            table_info = 'package=%s' % pkg.name if pkg else 'None'
        elif self.table_name == 'group':
            group = meta.Session.query(Group).get(self.table_id)
            table_info = 'group=%s' % group.name if group else 'None'
        else:
            table_info = 'table_name=%s table_id=%s' % (self.table_name,
                                                        self.table_id)
        return u'<Member group=%s %s capacity=%s state=%s>' % \
               (self.group.name if self.group else repr(self.group),
                table_info, self.capacity, self.state)


class Group(core.StatefulObjectMixin,
            domain_object.DomainObject):

    id: str
    name: str
    title: str
    type: str
    description: str
    image_url: str
    created: datetime.datetime
    is_organization: bool
    approval_status: str
    state: str

    _extras: dict[str, Any]  # list['GroupExtra']
    extras: AssociationProxy
    member_all: list[Member]

    def __init__(self, name: str = u'', title: str = u'',
                 description: str = u'', image_url: str = u'',
                 type: str = u'group', approval_status: str = u'approved',
                 is_organization: bool = False) -> None:
        self.name = name
        self.title = title
        self.description = description
        self.image_url = image_url
        self.type = type
        self.approval_status = approval_status
        self.is_organization = is_organization

    @property
    def display_name(self) -> str:
        if self.title is not None and len(self.title):
            return self.title
        else:
            return self.name

    @classmethod
    def get(cls, reference: Optional[str]) -> Optional[Self]:
        '''Returns a group object referenced by its id or name.'''
        query = meta.Session.query(cls).filter(cls.id == reference)
        group = query.first()
        if group is None:
            group = cls.by_name(reference)
        return group
    # Todo: Make sure group names can't be changed to look like group IDs?

    @classmethod
    def all(cls, group_type: Optional[str] = None,
            state: tuple[str]=('active',)) -> Query[Self]:
        """
        Returns all groups.
        """
        q = meta.Session.query(cls)
        if state:
            # type_ignore_reason: incomplete SQLAlchemy types
            q = q.filter(cls.state.in_(state))  # type: ignore

        if group_type:
            q = q.filter(cls.type == group_type)

        return q.order_by(cls.title)

    def set_approval_status(self, status: str) -> None:
        """
            Aproval status can be set on a group, where currently it does
            nothing other than act as an indication of whether it was
            approved or not. It may be that we want to tie the object
            status to the approval status
        """
        assert status in ["approved", "denied"]
        self.approval_status = status

    def get_children_groups(self, type: str='group') -> list[Self]:
        '''Returns the groups one level underneath this group in the hierarchy.
        '''
        # The original intention of this method was to provide the full depth
        # of the tree, but the CTE was incorrect. This new query does what that
        # old CTE actually did, but is now far simpler, and returns Group objects
        # instead of a dict.
        result: list[Group] = meta.Session.query(Group).\
            filter_by(type=type).\
            filter_by(state='active').\
            join(Member, Member.group_id == Group.id).\
            filter_by(table_id=self.id).\
            filter_by(table_name='group').\
            filter_by(state='active').\
            all()
        return result

    def get_children_group_hierarchy(
            self, type: str='group') -> list[tuple[str, str, str, str]]:
        '''Returns the groups in all levels underneath this group in the
        hierarchy. The ordering is such that children always come after their
        parent.

        :rtype: a list of tuples, each one a Group ID, name and title and then
        the ID of its parent group.

        e.g.
        >>> dept-health.get_children_group_hierarchy()
        [(u'8ac0...', u'national-health-service', u'National Health Service', u'e041...'),
         (u'b468...', u'nhs-wirral-ccg', u'NHS Wirral CCG', u'8ac0...')]
        '''
        results: list[tuple[str, str, str, str]] = meta.Session.query(
            Group.id, Group.name, Group.title,  column('parent_id')
        ).from_statement(text(HIERARCHY_DOWNWARDS_CTE)).params(
            id=self.id, type=type).all()
        return results

    def get_parent_groups(self, type: str='group') -> list[Self]:
        '''Returns this group's parent groups.
        Returns a list. Will have max 1 value for organizations.

        '''
        result: list[Group] = meta.Session.query(Group).\
            join(Member,
                 and_(Member.table_id == Group.id,
                      Member.table_name == 'group',
                      Member.state == 'active')).\
            filter(Member.group_id == self.id).\
            filter(Group.type == type).\
            filter(Group.state == 'active').\
            all()
        return result

    def get_parent_group_hierarchy(self, type: str='group') -> list[Self]:
        '''Returns this group's parent, parent's parent, parent's parent's
        parent etc.. Sorted with the top level parent first.'''
        result: list[Group] =  meta.Session.query(Group).\
            from_statement(text(HIERARCHY_UPWARDS_CTE)).\
            params(id=self.id, type=type).all()
        return result

    @classmethod
    def get_top_level_groups(cls, type: str='group') -> list[Self]:
        '''Returns a list of the groups (of the specified type) which have
        no parent groups. Groups are sorted by title.
        '''
        result: list[Group] = meta.Session.query(cls).\
            outerjoin(Member,
                      and_(Member.group_id == Group.id,
                           Member.table_name == 'group',
                           Member.state == 'active')).\
            filter(
                Member.id == None  # type: ignore
            ).filter(Group.type == type).\
            filter(Group.state == 'active').\
            order_by(Group.title).all()
        return result

    def groups_allowed_to_be_its_parent(
            self, type: str='group') -> list[Self]:
        '''Returns a list of the groups (of the specified type) which are
        allowed to be this group's parent. It excludes ones which would
        create a loop in the hierarchy, causing the recursive CTE to
        be in an infinite loop.

        :returns: A list of group objects ordered by group title

        '''
        all_groups = self.all(group_type=type)
        excluded_groups = set(group_name
                              for _group_id, group_name, _group_title, _parent
                              in self.get_children_group_hierarchy(type=type))
        excluded_groups.add(self.name)
        return [group for group in all_groups
                if group.name not in excluded_groups]

    @overload
    def packages(self, *,
                 return_query: Literal[True],
                 context: Optional[Context]=...
                 ) -> 'Query[_package.Package]': ...
    @overload
    def packages(self, with_private: bool, limit: Optional[int],
                 return_query: Literal[True],
                 context: Optional[Context]=...
                 ) -> 'Query[_package.Package]': ...
    @overload
    def packages(self, with_private: bool=..., limit: Optional[int]=...,
                 return_query: Literal[False]=...,
                 context: Optional[Context]=...
                 ) -> list[_package.Package]: ...

    def packages(
            self, with_private: bool = False,
            limit: Optional[int] = None,
            return_query: bool = False,
            context: Optional[Context] = None
    ) -> Union["Query[_package.Package]", list[_package.Package]]:
        '''Return this group's active packages.

        Returns all packages in this group with VDM state ACTIVE

        :param with_private: if True, include the group's private packages
        :type with_private: bool

        :param limit: the maximum number of packages to return
        :type limit: int

        :param return_query: if True, return the SQLAlchemy query object
            instead of the list of Packages resulting from the query
        :type return_query: bool

        :returns: a list of this group's packages
        :rtype: list of ckan.model.package.Package objects

        '''
        user_is_org_member = False
        context = context or {}
        user_is_admin = context.get('user_is_admin', False)
        user_id = context.get('user_id')
        if user_is_admin:
            user_is_org_member = True

        elif self.is_organization and user_id:
            member_query = meta.Session.query(Member) \
                    .filter(Member.state == 'active') \
                    .filter(Member.table_name == 'user') \
                    .filter(Member.group_id == self.id) \
                    .filter(Member.table_id == user_id)
            user_is_org_member = len(member_query.all()) != 0

        query = meta.Session.query(_package.Package).\
            filter(_package.Package.state == core.State.ACTIVE).\
            filter(group_table.c["id"] == self.id).\
            filter(member_table.c["state"] == 'active')

        # orgs do not show private datasets unless the user is a member
        if self.is_organization and not user_is_org_member:
            query = query.filter(_package.Package.private == False)
        # groups (not orgs) never show private datasets
        if not self.is_organization:
            query = query.filter(_package.Package.private == False)

        query: "Query[_package.Package]" = query.join(
            member_table, member_table.c["table_id"] == _package.Package.id)
        query: "Query[_package.Package]" = query.join(
            group_table, group_table.c["id"] == member_table.c["group_id"])

        if limit is not None:
            query = query.limit(limit)

        if return_query:
            return query
        else:
            return query.all()

    @classmethod
    def search_by_name_or_title(
            cls, text_query: str, group_type: Optional[str] = None,
            is_org: bool = False, limit: int = 20) -> Query[Self]:
        text_query = text_query.strip().lower()
        # type_ignore_reason: incomplete SQLAlchemy types
        q = meta.Session.query(cls) \
            .filter(or_(cls.name.contains(text_query),  # type: ignore
                        cls.title.ilike('%' + text_query + '%')))  # type: ignore
        if is_org:
            q = q.filter(cls.type == 'organization')
        else:
            q = q.filter(cls.type != 'organization')
            if group_type:
                q = q.filter(cls.type == group_type)
        q = q.filter(cls.state == 'active')
        q.order_by(cls.title)
        q = q.limit(limit)
        return q

    def add_package_by_name(self, package_name: str) -> None:
        if not package_name:
            return
        package = _package.Package.by_name(package_name)
        assert package
        if not package in self.packages():
            member = Member(group=self, table_id=package.id,
                            table_name='package')
            meta.Session.add(member)

    def __repr__(self):
        return '<Group %s>' % self.name

meta.mapper(Group, group_table)

meta.mapper(Member, member_table, properties={
    'group': orm.relation(Group,
                          backref=orm.backref('member_all',
                                              cascade='all, delete-orphan')),
})


# Should there arise a bug that allows loops in the group hierarchy, then it
# will lead to infinite recursion, tieing up postgres processes at 100%, and
# the server will suffer. To avoid ever failing this badly, we put in this
# limit on recursion.
MAX_RECURSES: int = 8

HIERARCHY_DOWNWARDS_CTE: str = """WITH RECURSIVE child(depth) AS
(
    -- non-recursive term
    SELECT 0, * FROM member
    WHERE table_id = :id AND table_name = 'group' AND state = 'active'
    UNION ALL
    -- recursive term
    SELECT c.depth + 1, m.* FROM member AS m, child AS c
    WHERE m.table_id = c.group_id AND m.table_name = 'group'
          AND m.state = 'active' AND c.depth < {max_recurses}
)
SELECT G.id, G.name, G.title, child.depth, child.table_id as parent_id FROM child
    INNER JOIN public.group G ON G.id = child.group_id
    WHERE G.type = :type AND G.state='active'
    ORDER BY child.depth ASC;""".format(max_recurses=MAX_RECURSES)

HIERARCHY_UPWARDS_CTE: str = """WITH RECURSIVE parenttree(depth) AS (
    -- non-recursive term
    SELECT 0, M.* FROM public.member AS M
    WHERE group_id = :id AND M.table_name = 'group' AND M.state = 'active'
    UNION
    -- recursive term
    SELECT PG.depth + 1, M.* FROM parenttree PG, public.member M
    WHERE PG.table_id = M.group_id AND M.table_name = 'group'
          AND M.state = 'active' AND PG.depth < {max_recurses}
    )

SELECT G.*, PT.depth FROM parenttree AS PT
    INNER JOIN public.group G ON G.id = PT.table_id
    WHERE G.type = :type AND G.state='active'
    ORDER BY PT.depth DESC;""".format(max_recurses=MAX_RECURSES)
