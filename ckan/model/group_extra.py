from meta import *
from types import make_uuid
import vdm.sqlalchemy

from core import *
from package import *
from group import *
from types import JsonType


__all__ = ['GroupExtra', 'group_extra_table', 'GroupExtraRevision']

group_extra_table = Table('group_extra', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('group_id', UnicodeText, ForeignKey('group.id')),
    Column('key', UnicodeText),
    Column('value', JsonType),
)

vdm.sqlalchemy.make_table_stateful(group_extra_table)
group_extra_revision_table = make_revisioned_table(group_extra_table)


class GroupExtra(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    pass

mapper(GroupExtra, group_extra_table, properties={
    'group': orm.relation(Group,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),
            cascade='all, delete, delete-orphan',
            ),
        )
    },
    order_by=[group_extra_table.c.group_id, group_extra_table.c.key],
    extension=[vdm.sqlalchemy.Revisioner(group_extra_revision_table),],
)

vdm.sqlalchemy.modify_base_object_mapper(GroupExtra, Revision, State)
GroupExtraRevision = vdm.sqlalchemy.create_object_version(mapper, GroupExtra,
    group_extra_revision_table)

def _create_extra(key, value):
    return GroupExtra(key=unicode(key), value=value)

import vdm.sqlalchemy.stateful
_extras_active = vdm.sqlalchemy.stateful.DeferredProperty('_extras',
        vdm.sqlalchemy.stateful.StatefulDict, base_modifier=lambda x: x.get_as_of()) 
setattr(Group, 'extras_active', _extras_active)
Group.extras = vdm.sqlalchemy.stateful.OurAssociationProxy('extras_active', 'value',
            creator=_create_extra)
