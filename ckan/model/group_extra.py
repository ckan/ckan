# encoding: utf-8

from sqlalchemy import orm, types, Column, Table, ForeignKey
from sqlalchemy.ext.associationproxy import association_proxy
from six import text_type

from ckan.model import (
    group,
    meta,
    core,
    types as _types,
    domain_object
)


__all__ = ['GroupExtra', 'group_extra_table']

group_extra_table = Table('group_extra', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('group_id', types.UnicodeText, ForeignKey('group.id')),
    Column('key', types.UnicodeText),
    Column('value', types.UnicodeText),
    Column('state', types.UnicodeText, default=core.State.ACTIVE),
)


class GroupExtra(core.StatefulObjectMixin,
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
)

def _create_extra(key, value):
    return GroupExtra(key=text_type(key), value=value)

group.Group.extras = association_proxy(
    '_extras', 'value', creator=_create_extra)
