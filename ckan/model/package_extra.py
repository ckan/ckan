from meta import *
from types import make_uuid
import vdm.sqlalchemy

from core import *
from package import *
from types import JsonType
from ckan.model import extension

__all__ = ['PackageExtra', 'package_extra_table', 'PackageExtraRevision',
           'extra_revision_table']

package_extra_table = Table('package_extra', metadata,
    Column('id', UnicodeText, primary_key=True, default=make_uuid),
    # NB: only (package, key) pair is unique
    Column('package_id', UnicodeText, ForeignKey('package.id')),
    Column('key', UnicodeText),
    Column('value', JsonType),
)

vdm.sqlalchemy.make_table_stateful(package_extra_table)
extra_revision_table= make_revisioned_table(package_extra_table)

class PackageExtra(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):

    def related_packages(self):
        return [self.package]

    def activity_stream_detail(self, activity_id, activity_type):
        import ckan.model as model
        import ckan.model.activity as activity
        import ckan.lib.dictization

        # Handle 'deleted' extras.
        # When the user marks an extra as deleted this comes through here as a
        # 'changed' extra. We detect this and change it to a 'deleted'
        # activity.
        if activity_type == 'changed' and self.state == u'deleted':
            activity_type = 'deleted'

        data_dict = ckan.lib.dictization.table_dictize(self,
                context={'model': model})
        return activity.ActivityDetail(activity_id, self.id, u"PackageExtra",
                activity_type, {'package_extra': data_dict})

mapper(PackageExtra, package_extra_table, properties={
    'package': orm.relation(Package,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),
            cascade='all, delete, delete-orphan',
            ),
        ),
    'package_no_state': orm.relation(Package,
        backref=orm.backref('extras_list',
            cascade='all, delete, delete-orphan',
            ),
        )
    },
    order_by=[package_extra_table.c.package_id, package_extra_table.c.key],
    extension=[vdm.sqlalchemy.Revisioner(extra_revision_table),
               extension.PluginMapperExtension(),
               ],
)

vdm.sqlalchemy.modify_base_object_mapper(PackageExtra, Revision, State)
PackageExtraRevision= vdm.sqlalchemy.create_object_version(mapper, PackageExtra,
        extra_revision_table)

PackageExtraRevision.related_packages = lambda self: [self.continuity.package]

def _create_extra(key, value):
    return PackageExtra(key=unicode(key), value=value)

import vdm.sqlalchemy.stateful
_extras_active = vdm.sqlalchemy.stateful.DeferredProperty('_extras',
        vdm.sqlalchemy.stateful.StatefulDict, base_modifier=lambda x: x.get_as_of()) 
setattr(Package, 'extras_active', _extras_active)
Package.extras = vdm.sqlalchemy.stateful.OurAssociationProxy('extras_active', 'value',
            creator=_create_extra)

