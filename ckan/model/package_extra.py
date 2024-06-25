# encoding: utf-8
from __future__ import annotations

from typing import Any

from sqlalchemy import orm, types, Column, Table, ForeignKey, Index
from sqlalchemy.ext.associationproxy import association_proxy

import ckan.model.meta as meta
import ckan.model.core as core
import ckan.model.package as _package
import ckan.model.domain_object as domain_object
import ckan.model.types as _types

__all__ = ['PackageExtra', 'package_extra_table']

Mapped = orm.Mapped
package_extra_table = Table('package_extra', meta.metadata,
    Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
    # NB: only (package, key) pair is unique
    Column('package_id', types.UnicodeText, ForeignKey('package.id')),
    Column('key', types.UnicodeText),
    Column('value', types.UnicodeText),
    Column('state', types.UnicodeText, default=core.State.ACTIVE),
    Index('idx_extra_id_pkg_id', 'id', 'package_id'),
    Index('idx_extra_pkg_id', 'package_id'),
)


class PackageExtra(core.StatefulObjectMixin, domain_object.DomainObject):
    id: Mapped[str]
    package_id: Mapped[str]
    key: Mapped[str]
    value: Mapped[str]
    state: Mapped[str]

    package: _package.Package

    def related_packages(self) -> list[_package.Package]:
        return [self.package]


meta.registry.map_imperatively(PackageExtra, package_extra_table, properties={
    'package': orm.relationship(_package.Package,
        backref=orm.backref('_extras',
            collection_class=orm.collections.attribute_mapped_collection(u'key'),  # type: ignore
            cascade='all, delete, delete-orphan',
            ),
        ),
    }
)


def _create_extra(key: str, value: Any):
    return PackageExtra(key=str(key), value=value)

_package.Package.extras = association_proxy(
    '_extras', 'value', creator=_create_extra)
