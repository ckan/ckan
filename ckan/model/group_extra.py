# encoding: utf-8

from typing import Any
from sqlalchemy import orm, types, Column, Table, ForeignKey, Index
from sqlalchemy.ext.associationproxy import association_proxy


import ckan.model.group as group
import ckan.model.meta as meta
import ckan.model.core as core
import ckan.model.types as _types
import ckan.model.domain_object as domain_object


__all__ = ['GroupExtra', 'group_extra_table']

Mapped = orm.Mapped
group_extra_table = Table('group_extra', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    Column('group_id', types.UnicodeText, ForeignKey('group.id')),
    Column('key', types.UnicodeText),
    Column('value', types.UnicodeText),
    Column('state', types.UnicodeText, default=core.State.ACTIVE),
    Index('idx_group_extra_group_id', 'group_id'),
)


class GroupExtra(core.StatefulObjectMixin,
                 domain_object.DomainObject):
    id: Mapped[str]
    group_id: Mapped[str]
    key: Mapped[str]
    value: Mapped[str]
    state: Mapped[str]

    group: group.Group


meta.registry.map_imperatively(GroupExtra, group_extra_table, properties={
    'group': orm.relationship(group.Group,
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
