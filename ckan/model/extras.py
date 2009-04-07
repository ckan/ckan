from meta import *
from core import DomainObject, Package
from types import JsonType

extra_table = Table('package_extra', metadata,
    Column('id', Integer, primary_key=True),
    # NB: only (package, key) pair is unique
    Column('package_id', Integer, ForeignKey('package.id')),
    Column('key', UnicodeText),
    Column('value', JsonType),
)


class Extra(DomainObject):
    pass

mapper(Extra, extra_table, properties={
    'package': orm.relation(Package,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),
            cascade='all, delete, delete-orphan',
            ),
        )
    },
    order_by=[extra_table.c.package_id, extra_table.c.key]
)

from sqlalchemy.ext.associationproxy import association_proxy
def _create_extra(key, value):
    return Extra(key=unicode(key), value=value)
Package.extras = association_proxy('_extras', 'value',
            creator=_create_extra)

