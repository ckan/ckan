import vdm.sqlalchemy
from sqlalchemy.orm import relation

import tag
import meta
import core
import package as _package
import extension

__all__ = ['PackageRevision']

meta.mapper(_package.Package, _package.package_table, properties={
    # delete-orphan on cascade does NOT work!
    # Why? Answer: because of way SQLAlchemy/our code works there are points
    # where PackageTag object is created *and* flushed but does not yet have
    # the package_id set (this cause us other problems ...). Some time later a
    # second commit happens in which the package_id is correctly set.
    # However after first commit PackageTag does not have Package and
    # delete-orphan kicks in to remove it!
    'package_tags':relation(tag.PackageTag, backref='package',
        cascade='all, delete', #, delete-orphan',
        ),
    },
    order_by=_package.package_table.c.name,
    extension=[vdm.sqlalchemy.Revisioner(_package.package_revision_table),
               extension.PluginMapperExtension(),
               ],
    )

vdm.sqlalchemy.modify_base_object_mapper(_package.Package, core.Revision, core.State)
PackageRevision = vdm.sqlalchemy.create_object_version(meta.mapper, _package.Package,
        _package.package_revision_table)

def related_packages(self):
    return [self.continuity]

PackageRevision.related_packages = related_packages


