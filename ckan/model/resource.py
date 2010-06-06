import simplejson as json

from sqlalchemy.ext.orderinglist import ordering_list
import vdm.sqlalchemy

from meta import *
from types import make_uuid
from core import DomainObject, Package, package_table, Revision, State

__all__ = ['PackageResource', 'package_resource_table',
           'PackageResourceRevision', 'resource_revision_table']

package_resource_table = Table(
    'package_resource', metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('package_id', types.UnicodeText, ForeignKey('package.id')),
    Column('url', types.UnicodeText, nullable=False),
    Column('format', types.UnicodeText),
    Column('description', types.UnicodeText),
    Column('hash', types.UnicodeText),
    Column('position', types.Integer),
    )

vdm.sqlalchemy.make_table_stateful(package_resource_table)
resource_revision_table = vdm.sqlalchemy.make_revisioned_table(package_resource_table)

class PackageResource(vdm.sqlalchemy.RevisionedObjectMixin,
                      vdm.sqlalchemy.StatefulObjectMixin,
                      DomainObject):
    def __init__(self, package_id=None, url=u'', format=u'', description=u'', hash=u''):
        if package_id:
            self.package_id = package_id
        self.url = url
        self.format = format
        self.description = description
        self.hash = hash

    @property
    def as_dict(self):
        return dict([(col, getattr(self, col)) for col in self.get_columns()])
        
    @staticmethod
    def get_columns():
        return ['url', 'format', 'description', 'hash']

mapper(PackageResource, package_resource_table, properties={
    'package':orm.relation(Package,
        # all resources including deleted
        backref=orm.backref('package_resources_all',
                            collection_class=ordering_list('position'),
                            cascade='all, delete, delete-orphan',
                            order_by=package_resource_table.c.position,
                            ),
                       )
    },
    order_by=[package_resource_table.c.package_id],
    extension = vdm.sqlalchemy.Revisioner(resource_revision_table)       
)
    
vdm.sqlalchemy.modify_base_object_mapper(PackageResource, Revision, State)
PackageResourceRevision= vdm.sqlalchemy.create_object_version(
    mapper, PackageResource, resource_revision_table)

import vdm.sqlalchemy.stateful
# TODO: move this into vdm
def add_stateful_m21(object_to_alter, m21_property_name,
        underlying_m21_attrname, identifier, **kwargs):
    from sqlalchemy.orm import object_session
    def _f(obj_to_delete):
        sess = object_session(obj_to_delete)
        if sess: # for tests at least must support obj not being sqlalchemy
            sess.expunge(obj_to_delete)

    active_list = vdm.sqlalchemy.stateful.DeferredProperty(
            underlying_m21_attrname,
            vdm.sqlalchemy.stateful.StatefulList,
            # these args are passed to StatefulList
            # identifier if url (could use id but have issue with None)
            identifier=identifier,
            unneeded_deleter=_f,
            base_modifier=lambda x: x.get_as_of()
            )
    setattr(object_to_alter, m21_property_name, active_list)

def package_resource_identifier(obj):
    return json.dumps(obj.as_dict)
add_stateful_m21(Package, 'resources', 'package_resources_all',
                 package_resource_identifier)

