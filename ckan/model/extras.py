from meta import *
from types import make_uuid
import vdm.sqlalchemy

from core import DomainObject, Package, Revision, State
from types import JsonType

__all__ = ['PackageExtra', 'package_extra_table', 'PackageExtraRevision']

package_extra_table = Table('package_extra', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    # NB: only (package, key) pair is unique
    Column('package_id', UnicodeText, ForeignKey('package.id')),
    Column('key', UnicodeText),
    Column('value', JsonType),
)

vdm.sqlalchemy.make_table_stateful(package_extra_table)
extra_revision_table= vdm.sqlalchemy.make_revisioned_table(package_extra_table)

class PackageExtra(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    pass

mapper(PackageExtra, package_extra_table, properties={
    'package': orm.relation(Package,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),
            cascade='all, delete, delete-orphan',
            ),
        )
    },
    order_by=[package_extra_table.c.package_id, package_extra_table.c.key],
    extension = vdm.sqlalchemy.Revisioner(extra_revision_table)
)

vdm.sqlalchemy.modify_base_object_mapper(PackageExtra, Revision, State)
PackageExtraRevision= vdm.sqlalchemy.create_object_version(mapper, PackageExtra,
        extra_revision_table)

def _create_extra(key, value):
    return PackageExtra(key=unicode(key), value=value)

import vdm.sqlalchemy.stateful
_extras_active = vdm.sqlalchemy.stateful.DeferredProperty('_extras',
        vdm.sqlalchemy.stateful.StatefulDict, base_modifier=lambda x: x.get_as_of()) 
setattr(Package, 'extras_active', _extras_active)
Package.extras = vdm.sqlalchemy.stateful.OurAssociationProxy('extras_active', 'value',
            creator=_create_extra)

