# encoding: utf-8

import vdm.sqlalchemy
from sqlalchemy import orm, types, Column, Table, ForeignKey

import meta
import core
import package as _package
import types as _types
import domain_object

# i18n only works when this is run as part of pylons,
# which isn't the case for paster commands.
try:
    from ckan.common import _
    _()
except:
    def _(txt):
        return txt

__all__ = ['PackageRelationship', 'package_relationship_table',
           'package_relationship_revision_table']

package_relationship_table = Table('package_relationship', meta.metadata,
     Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
     Column('subject_package_id', types.UnicodeText, ForeignKey('package.id')),
     Column('object_package_id', types.UnicodeText, ForeignKey('package.id')),
     Column('type', types.UnicodeText),
     Column('comment', types.UnicodeText),
     )

vdm.sqlalchemy.make_table_stateful(package_relationship_table)
package_relationship_revision_table = core.make_revisioned_table(package_relationship_table)

class PackageRelationship(vdm.sqlalchemy.RevisionedObjectMixin,
                          vdm.sqlalchemy.StatefulObjectMixin,
                          domain_object.DomainObject):
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
        return '<%sPackageRelationship %s %s %s>' % ("*" if self.active != core.State.ACTIVE else "",
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
        assert isinstance(package, _package.Package), package
        if self.subject == package:
            type_str = self.type
            other_package = self.object
        elif self.object == package:
            type_str = self.forward_to_reverse_type(self.type)
            other_package = self.subject
        else:
            # FIXME do we want a more specific error
            raise Exception('Package %s is not in this relationship: %s' % \
                             (package, self))
        return (type_str, other_package)
        
    @classmethod
    def by_subject(cls, package):
        return meta.Session.query(cls).filter(cls.subject_package_id==package.id)

    @classmethod
    def by_object(cls, package):
        return meta.Session.query(cls).filter(cls.object_package_id==package.id)
    
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

meta.mapper(PackageRelationship, package_relationship_table, properties={
    'subject':orm.relation(_package.Package, primaryjoin=\
           package_relationship_table.c.subject_package_id==_package.Package.id,
           backref='relationships_as_subject'),
    'object':orm.relation(_package.Package, primaryjoin=package_relationship_table.c.object_package_id==_package.Package.id,
           backref='relationships_as_object'),
    },
    extension = [vdm.sqlalchemy.Revisioner(package_relationship_revision_table)]
    )

vdm.sqlalchemy.modify_base_object_mapper(PackageRelationship, core.Revision, core.State)
PackageRelationshipRevision = vdm.sqlalchemy.create_object_version(
    meta.mapper, PackageRelationship, package_relationship_revision_table)
