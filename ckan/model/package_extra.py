# encoding: utf-8

from six import text_type
import vdm.sqlalchemy
import vdm.sqlalchemy.stateful
from sqlalchemy import orm, types, Column, Table, ForeignKey
from sqlalchemy.ext.associationproxy import association_proxy

import meta
import core
import package as _package
import extension
import domain_object
import types as _types
import ckan.lib.dictization
import activity

__all__ = ['PackageExtra', 'package_extra_table', 'PackageExtraRevision',
           'extra_revision_table']

package_extra_table = Table('package_extra', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    # NB: only (package, key) pair is unique
    Column('package_id', types.UnicodeText, ForeignKey('package.id')),
    Column('key', types.UnicodeText),
    Column('value', types.UnicodeText),
    Column('state', types.UnicodeText, default=core.State.ACTIVE),
)


extra_revision_table= core.make_revisioned_table(package_extra_table)

class PackageExtra(vdm.sqlalchemy.RevisionedObjectMixin,
        core.StatefulObjectMixin,
        domain_object.DomainObject):

    def related_packages(self):
        return [self.package]

    def activity_stream_detail(self, activity_id, activity_type):
        import ckan.model as model

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

meta.mapper(PackageExtra, package_extra_table, properties={
    'package': orm.relation(_package.Package,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),
            cascade='all, delete, delete-orphan',
            ),
        ),
    },
    order_by=[package_extra_table.c.package_id, package_extra_table.c.key],
    extension=[vdm.sqlalchemy.Revisioner(extra_revision_table),
               extension.PluginMapperExtension(),
               ],
)

vdm.sqlalchemy.modify_base_object_mapper(PackageExtra, core.Revision, core.State)
PackageExtraRevision= vdm.sqlalchemy.create_object_version(meta.mapper, PackageExtra,
        extra_revision_table)

PackageExtraRevision.related_packages = lambda self: [self.continuity.package]

def _create_extra(key, value):
    return PackageExtra(key=text_type(key), value=value)

_package.Package.extras = association_proxy(
    '_extras', 'value', creator=_create_extra)
