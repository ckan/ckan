import vdm.sqlalchemy

from meta import *
from core import DomainObject, Package
from types import make_uuid

package_relationship_table = Table('package_relationship', metadata,
     Column('id', UnicodeText, primary_key=True, default=make_uuid),
     Column('subject_package_id', UnicodeText, ForeignKey('package.id')),
     Column('object_package_id', UnicodeText, ForeignKey('package.id')),
     Column('type', UnicodeText),
     Column('comment', UnicodeText),
     )

package_relationship_revision_table = vdm.sqlalchemy.make_revisioned_table(package_relationship_table)

class PackageRelationship(vdm.sqlalchemy.RevisionedObjectMixin,
                          DomainObject):
    types = [(u'depends_on', u'dependency_of'),
             (u'derives_from', u'has_derivation'),
             (u'child_of', u'parent_of'),
             ]

    @classmethod
    def by_subject(self, package):
        return Session.query(self).filter(self.subject_package_id==package.id)

    @classmethod
    def by_object(self, package):
        return Session.query(self).filter(self.object_package_id==package.id)
    
    @classmethod
    def get_forward_types(self):
        return [fwd for fwd, rev in self.types]

    @classmethod
    def get_reverse_types(self):
        return [rev for fwd, rev in self.types]

    @classmethod
    def reverse_to_forward_type(self, reverse_type):
        for fwd, rev in self.types:
            if rev == reverse_type:
                return fwd        
                 
mapper(PackageRelationship, package_relationship_table, properties={
    'subject':relation(Package, primaryjoin=\
           package_relationship_table.c.subject_package_id==Package.c.id,
           backref='relationships_as_subject'),
    'object':relation(Package, primaryjoin=package_relationship_table.c.object_package_id==Package.c.id,
           backref='relationships_as_object'),
    },
    extension = [vdm.sqlalchemy.Revisioner(package_relationship_revision_table)]
    )

