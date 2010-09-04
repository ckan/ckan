from meta import *
from types import make_uuid
import vdm.sqlalchemy
from sqlalchemy.ext.associationproxy import association_proxy

from core import *
from group import *
from types import JsonType

__all__ = ['GroupExtra', 'group_extra_table']

group_extra_table = Table('group_extra', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    Column('group_id', UnicodeText, ForeignKey('group.id')),
    Column('key', UnicodeText),
    Column('value', JsonType),
)

class GroupExtra(DomainObject):
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
    extension=[],
)


def _create_extra(key, value):
    return GroupExtra(key=unicode(key), value=value)

Group.extras = association_proxy('_extras', 'value', creator=_create_extra)

