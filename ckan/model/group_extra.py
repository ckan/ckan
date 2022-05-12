# encoding: utf-8

from typing import Any
from sqlalchemy import orm, types, Column, Table, ForeignKey
from sqlalchemy.ext.associationproxy import association_proxy


import ckan.model.group as group
import ckan.model.meta as meta
import ckan.model.core as core
import ckan.model.types as _types
import ckan.model.domain_object as domain_object


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
    id: str
    group_id: str
    key: str
    value: str
    state: str

    group: group.Group

# type_ignore_reason: incomplete SQLAlchemy types
meta.mapper(GroupExtra, group_extra_table, properties={
    'group': orm.relation(group.Group,
        backref=orm.backref(
            '_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),  # type: ignore
            cascade='all, delete, delete-orphan',
            ),
        )
    }
)

def _create_extra(key: str, value: Any):
    return GroupExtra(key=str(key), value=value)

group.Group.extras = association_proxy(
    '_extras', 'value', creator=_create_extra)
