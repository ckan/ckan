# encoding: utf-8

import vdm.sqlalchemy
import vdm.sqlalchemy.stateful
from sqlalchemy import orm, types, Column, Table, ForeignKey

import group
import meta
import core
import types as _types
import domain_object


__all__ = ['GroupExtra', 'group_extra_table', 'GroupExtraRevision']

group_extra_table = Table('group_extra', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('group_id', types.UnicodeText, ForeignKey('group.id')),
    Column('key', types.UnicodeText),
    Column('value', types.UnicodeText),
)

vdm.sqlalchemy.make_table_stateful(group_extra_table)
group_extra_revision_table = core.make_revisioned_table(group_extra_table)


class GroupExtra(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        domain_object.DomainObject):
    pass

meta.mapper(GroupExtra, group_extra_table, properties={
    'group': orm.relation(group.Group,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),
            cascade='all, delete, delete-orphan',
            ),
        )
    },
    order_by=[group_extra_table.c.group_id, group_extra_table.c.key],
    extension=[vdm.sqlalchemy.Revisioner(group_extra_revision_table),],
)

vdm.sqlalchemy.modify_base_object_mapper(GroupExtra, core.Revision, core.State)
GroupExtraRevision = vdm.sqlalchemy.create_object_version(meta.mapper, GroupExtra,
    group_extra_revision_table)

def _create_extra(key, value):
    return GroupExtra(key=unicode(key), value=value)

_extras_active = vdm.sqlalchemy.stateful.DeferredProperty('_extras',
        vdm.sqlalchemy.stateful.StatefulDict, base_modifier=lambda x: x.get_as_of()) 
setattr(group.Group, 'extras_active', _extras_active)
group.Group.extras = vdm.sqlalchemy.stateful.OurAssociationProxy('extras_active', 'value',
            creator=_create_extra)
