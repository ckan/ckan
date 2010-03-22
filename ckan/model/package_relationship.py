import vdm.sqlalchemy

from meta import *
from core import DomainObject, Package
from types import make_uuid

# i18n only works when this is run as part of pylons,
# which isn't the case for paster commands.
try:
    from pylons.i18n import _
    _('')
except:
    def _(txt):
        return txt


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
    # List of (type, corresponding_reverse_type)
    # e.g. (A "depends_on" B, B has a "dependency_of" A)
    types = [(u'depends_on', u'dependency_of'),
             (u'derives_from', u'has_derivation'),
             (u'child_of', u'parent_of'),
             ]

    types_printable = \
            [(_(u'depends on %s'), _(u'is a dependency of %s')),
             (_(u'derives from %s'), _(u'has derivation %s')),
             (_(u'is a child of %s'), _(u'is a parent of %s')),
             ]

    inferred_types_printable = \
            {'sibling':_('has sibling %s')}

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

    @classmethod
    def forward_to_reverse_type(self, forward_type):
        for fwd, rev in self.types:
            if fwd == forward_type:
                return rev

    @classmethod
    def make_type_printable(self, type_):
        for i, types in enumerate(self.types):
            for j in range(2):
                if type_ == types[j]:
                    return self.types_printable[i][j]
        raise TypeError, type_

mapper(PackageRelationship, package_relationship_table, properties={
    'subject':relation(Package, primaryjoin=\
           package_relationship_table.c.subject_package_id==Package.c.id,
           backref='relationships_as_subject'),
    'object':relation(Package, primaryjoin=package_relationship_table.c.object_package_id==Package.c.id,
           backref='relationships_as_object'),
    },
    extension = [vdm.sqlalchemy.Revisioner(package_relationship_revision_table)]
    )

