# encoding: utf-8

from six import text_type
from sqlalchemy import orm, types, Column, Table, ForeignKey
from sqlalchemy.ext.associationproxy import association_proxy

from ckan.model import (
    meta,
    core,
    package as _package,
    extension,
    domain_object,
    types as _types,
)

__all__ = ['PackageExtra', 'package_extra_table']

package_extra_table = Table('package_extra', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    # NB: only (package, key) pair is unique
    Column('package_id', types.UnicodeText, ForeignKey('package.id')),
    Column('key', types.UnicodeText),
    Column('value', types.UnicodeText),
    Column('state', types.UnicodeText, default=core.State.ACTIVE),
)


class PackageExtra(
        core.StatefulObjectMixin,
        domain_object.DomainObject):

    def related_packages(self):
        return [self.package]


meta.mapper(PackageExtra, package_extra_table, properties={
    'package': orm.relation(_package.Package,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),
            cascade='all, delete, delete-orphan',
            ),
        ),
    },
    order_by=[package_extra_table.c.package_id, package_extra_table.c.key],
    extension=[extension.PluginMapperExtension()],
)


def _create_extra(key, value):
    return PackageExtra(key=text_type(key), value=value)

_package.Package.extras = association_proxy(
    '_extras', 'value', creator=_create_extra)
