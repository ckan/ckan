import vdm.sqlalchemy

from meta import *
from core import *
from package import *
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

vdm.sqlalchemy.make_table_stateful(package_relationship_table)
package_relationship_revision_table = make_revisioned_table(package_relationship_table)

class PackageRelationship(vdm.sqlalchemy.RevisionedObjectMixin,
                          vdm.sqlalchemy.StatefulObjectMixin,
                          DomainObject):
    '''The rule with PackageRelationships is that they are stored in the model
    always as the "forward" relationship - i.e. "child_of" but never
    as "parent_of". However, the model functions provide the relationships
    from both packages in the relationship and the type is swapped from
    forward to reverse accordingly, for meaningful display to the user.'''
    
    # List of (type, corresponding_reverse_type)
    # e.g. (A "depends_on" B, B has a "dependency_of" A)
    # don't forget to add specs to Solr's schema.xml
    types = [(u'depends_on', u'dependency_of'),
             (u'derives_from', u'has_derivation'),
             (u'links_to', u'linked_from'),
             (u'child_of', u'parent_of'),
             ]

    types_printable = \
            [(_(u'depends on %s'), _(u'is a dependency of %s')),
             (_(u'derives from %s'), _(u'has derivation %s')),
             (_(u'links to %s'), _(u'is linked from %s')),
             (_(u'is a child of %s'), _(u'is a parent of %s')),
             ]

    inferred_types_printable = \
            {'sibling':_('has sibling %s')}

    def __str__(self):
        from ckan import model
        return '<%sPackageRelationship %s %s %s>' % ("*" if self.active != model.State.ACTIVE else "",
                                                     self.subject.name, self.type, self.object.name)

    def __repr__(self):
        return str(self)

    def as_dict(self, package=None, ref_package_by='id'):
        """Returns full relationship info as a dict from the point of view
        of the given package if specified.
        e.g. {'subject':u'annakarenina',
              'type':u'depends_on',
              'object':u'warandpeace',
              'comment':u'Since 1843'}"""
        subject_pkg = self.subject
        object_pkg = self.object
        relationship_type = self.type
        if package and package == object_pkg:
            subject_pkg = self.object
            object_pkg = self.subject
            relationship_type = self.forward_to_reverse_type(self.type)
        subject_ref = getattr(subject_pkg, ref_package_by)
        object_ref = getattr(object_pkg, ref_package_by)
        return {'subject':subject_ref,
                'type':relationship_type,
                'object':object_ref,
                'comment':self.comment}

    def as_tuple(self, package):
        '''Returns basic relationship info as a tuple from the point of view
        of the given package with the object package object.
        e.g. rel.as_tuple(warandpeace) gives (u'depends_on', annakarenina)
        meaning warandpeace depends_on annakarenina.'''
        assert isinstance(package, Package), package
        if self.subject == package:
            type_str = self.type
            other_package = self.object
        elif self.object == package:
            type_str = self.forward_to_reverse_type(self.type)
            other_package = self.subject
        else:
            raise InputError('Package %s is not in this relationship: %s' % \
                             (package, self))
        return (type_str, other_package)
        
    @classmethod
    def by_subject(cls, package):
        return Session.query(cls).filter(cls.subject_package_id==package.id)

    @classmethod
    def by_object(cls, package):
        return Session.query(cls).filter(cls.object_package_id==package.id)
    
    @classmethod
    def get_forward_types(cls):
        if not hasattr(cls, 'fwd_types'):
            cls.fwd_types = [fwd for fwd, rev in cls.types]
        return cls.fwd_types

    @classmethod
    def get_reverse_types(cls):
        if not hasattr(cls, 'rev_types'):
            cls.rev_types = [rev for fwd, rev in cls.types]
        return cls.rev_types

    @classmethod
    def get_all_types(cls):
        if not hasattr(cls, 'all_types'):
            cls.all_types = []
            for fwd, rev in cls.types:
                cls.all_types.append(fwd)
                cls.all_types.append(rev)
        return cls.all_types

    @classmethod
    def reverse_to_forward_type(cls, reverse_type):
        for fwd, rev in cls.types:
            if rev == reverse_type:
                return fwd        

    @classmethod
    def forward_to_reverse_type(cls, forward_type):
        for fwd, rev in cls.types:
            if fwd == forward_type:
                return rev

    @classmethod
    def reverse_type(cls, forward_or_reverse_type):
        for fwd, rev in cls.types:
            if fwd == forward_or_reverse_type:
                return rev
            if rev == forward_or_reverse_type:
                return fwd        

    @classmethod
    def make_type_printable(cls, type_):
        for i, types in enumerate(cls.types):
            for j in range(2):
                if type_ == types[j]:
                    return cls.types_printable[i][j]
        raise TypeError, type_

mapper(PackageRelationship, package_relationship_table, properties={
    'subject':relation(Package, primaryjoin=\
           package_relationship_table.c.subject_package_id==Package.id,
           backref='relationships_as_subject'),
    'object':relation(Package, primaryjoin=package_relationship_table.c.object_package_id==Package.id,
           backref='relationships_as_object'),
    },
    extension = [vdm.sqlalchemy.Revisioner(package_relationship_revision_table)]
    )

vdm.sqlalchemy.modify_base_object_mapper(PackageRelationship, Revision, State)
PackageRelationshipRevision = vdm.sqlalchemy.create_object_version(
    mapper, PackageRelationship, package_relationship_revision_table)
