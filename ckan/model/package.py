# encoding: utf-8
from __future__ import annotations

from typing import (
    ClassVar, Iterable,
    Optional,
    TYPE_CHECKING,
    Any,
)

import datetime
import logging
from typing_extensions import TypeAlias, Self

from sqlalchemy.sql import and_, or_
from sqlalchemy import orm, types, Column, Table, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict

from ckan.common import config

import ckan.model.meta as meta
import ckan.model.core as core
import ckan.model.license as _license
import ckan.model.types as _types
import ckan.model.domain_object as domain_object

import ckan.lib.maintain as maintain
from ckan.types import Query

if TYPE_CHECKING:
    from ckan.model import (
     PackageExtra, PackageRelationship, Resource,
     PackageTag, Tag, Vocabulary,
     Group,
    )


PrintableRelationship: TypeAlias = "tuple[Package, str, Optional[str]]"

logger = logging.getLogger(__name__)

__all__ = ['Package', 'package_table', 'PackageMember', 'package_member_table',
           'PACKAGE_NAME_MAX_LENGTH', 'PACKAGE_NAME_MIN_LENGTH',
           'PACKAGE_VERSION_MAX_LENGTH',
           ]


PACKAGE_NAME_MAX_LENGTH: int = 100
PACKAGE_NAME_MIN_LENGTH: int = 2
PACKAGE_VERSION_MAX_LENGTH: int = 100


# Our Domain Object Tables
package_table = Table('package', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
        Column('name', types.Unicode(PACKAGE_NAME_MAX_LENGTH),
               nullable=False, unique=True),
        Column('title', types.UnicodeText, doc='remove_if_not_provided'),
        Column('version', types.Unicode(PACKAGE_VERSION_MAX_LENGTH),
               doc='remove_if_not_provided'),
        Column('url', types.UnicodeText, doc='remove_if_not_provided'),
        Column('author', types.UnicodeText, doc='remove_if_not_provided'),
        Column('author_email', types.UnicodeText, doc='remove_if_not_provided'),
        Column('maintainer', types.UnicodeText, doc='remove_if_not_provided'),
        Column('maintainer_email', types.UnicodeText, doc='remove_if_not_provided'),
        Column('notes', types.UnicodeText, doc='remove_if_not_provided'),
        Column('license_id', types.UnicodeText, doc='remove_if_not_provided'),
        Column('type', types.UnicodeText, default=u'dataset'),
        Column('owner_org', types.UnicodeText),
        Column('creator_user_id', types.UnicodeText),
        Column('metadata_created', types.DateTime, default=datetime.datetime.utcnow),
        Column('metadata_modified', types.DateTime, default=datetime.datetime.utcnow),
        Column('private', types.Boolean, default=False),
        Column('state', types.UnicodeText, default=core.State.ACTIVE),
        Column('plugin_data', MutableDict.as_mutable(JSONB)),
)


package_member_table = Table(
    'package_member',
    meta.metadata,
    Column('package_id', ForeignKey('package.id'), primary_key=True),
    Column('user_id', ForeignKey('user.id'), primary_key = True),
    Column('capacity', types.UnicodeText, nullable=False),
    Column('modified', types.DateTime, default=datetime.datetime.utcnow),
)


## -------------------
## Mapped classes

class Package(core.StatefulObjectMixin,
              domain_object.DomainObject):
    id: str
    name: str
    title: str
    version: str
    url: str
    author: str
    author_email: str
    maintainer: str
    maintainer_email: str
    notes: str
    licensce_id: str
    type: str
    owner_org: Optional[str]
    creator_user_id: str
    metadata_created: datetime.datetime
    metadata_modified: datetime.datetime
    private: bool
    state: str
    plugin_data: dict[str, Any]

    package_tags: list["PackageTag"]

    resources_all: list["Resource"]
    _extras: dict[str, Any]  # list['PackageExtra']
    extras: dict[str, Any]

    relationships_as_subject: 'PackageRelationship'
    relationships_as_object: 'PackageRelationship'

    _license_register: ClassVar['_license.LicenseRegister']

    text_search_fields: list[str] = ['name', 'title']

    @classmethod
    def search_by_name(cls, text_query: str) -> Query[Self]:
        return meta.Session.query(cls).filter(
            # type_ignore_reason: incomplete SQLAlchemy types
            cls.name.contains(text_query.lower())  # type: ignore
        )

    @classmethod
    def get(cls,
            reference: Optional[str],
            for_update: bool = False) -> Optional[Self]:
        '''Returns a package object referenced by its id or name.'''
        if not reference:
            return None

        q = meta.Session.query(cls)
        if for_update:
            q = q.with_for_update()
        pkg = q.get(reference)
        if pkg == None:
            pkg = cls.by_name(reference, for_update=for_update)
        return pkg
    # Todo: Make sure package names can't be changed to look like package IDs?

    @property
    def resources(self) -> list["Resource"]:
        return [resource for resource in
                self.resources_all
                if resource.state != 'deleted']

    def related_packages(self) -> list[Self]:
        return [self]

    def add_resource(
            self, url: str, format: str=u'',
            description: str=u'', hash: str=u'', **kw: Any) -> None:
        from ckan.model import resource
        self.resources_all.append(resource.Resource(
            package_id=self.id,
            url=url,
            format=format,
            description=description,
            hash=hash,
            **kw)
        )

    def add_tag(self, tag: "Tag") -> None:
        import ckan.model as model
        if tag in self.get_tags(tag.vocabulary):
            return
        else:
            package_tag = model.PackageTag(self, tag)
            meta.Session.add(package_tag)


    def add_tags(self, tags: Iterable["Tag"]) -> None:
        for tag in tags:
            self.add_tag(tag)

    def add_tag_by_name(
            self, tag_name: str,
            vocab: Optional["Vocabulary"] = None, autoflush: bool=True):
        """Add a tag with the given name to this package's tags.

        By default the given tag_name will be searched for among the free tags
        (tags which do not belong to any vocabulary) only. If the optional
        argument `vocab` is given then the named vocab will be searched for the
        tag name instead.

        If no tag with the given name is found, one will be created. If the
        optional argument vocab is given and there is no tag with the given
        name in the given vocabulary, then a new tag will be created and added
        to the vocabulary.

        """
        from ckan.model.tag import Tag
        if not tag_name:
            return
        # Get the named tag.
        tag = Tag.by_name(tag_name, vocab=vocab, autoflush=autoflush)
        if not tag:
            # Tag doesn't exist yet, make a new one.
            if vocab:
                tag = Tag(name=tag_name, vocabulary_id=vocab.id)
            else:
                tag = Tag(name=tag_name)
        assert tag is not None
        self.add_tag(tag)

    def get_tags(self, vocab: Optional["Vocabulary"] = None) -> list["Tag"]:
        """Return a sorted list of this package's tags

        Tags are sorted by their names.

        """
        import ckan.model as model
        query: Query[model.Tag] = meta.Session.query(model.Tag)
        query: Query[model.Tag] = query.join(model.PackageTag)
        query = query.filter(model.PackageTag.tag_id == model.Tag.id)
        query = query.filter(model.PackageTag.package_id == self.id)
        query = query.filter(model.PackageTag.state == 'active')
        if vocab:
            query = query.filter(model.Tag.vocabulary_id == vocab.id)
        else:
            query = query.filter(model.Tag.vocabulary_id == None)
        query = query.order_by(model.Tag.name)
        tags = query.all()
        return tags

    def remove_tag(self, tag: "Tag") -> None:
        import ckan.model as model
        query = meta.Session.query(model.PackageTag)
        query = query.filter(model.PackageTag.package_id == self.id)
        query = query.filter(model.PackageTag.tag_id == tag.id)
        package_tag = query.one()
        package_tag.delete()
        meta.Session.commit()

    def isopen(self) -> bool:
        if self.license and self.license.isopen():
            return True
        return False

    def as_dict(self, ref_package_by: str='name',
                ref_group_by: str='name') -> dict[str, Any]:
        _dict = domain_object.DomainObject.as_dict(self)
        # Set 'license' in _dict to cater for old clients.
        # Todo: Remove from Version 2?
        _dict['license'] = self.license.title if self.license else _dict.get('license_id', '')
        _dict['isopen'] = self.isopen()
        tags = [tag.name for tag in self.get_tags()]
        tags.sort() # so it is determinable
        _dict['tags'] = tags
        groups = [getattr(group, ref_group_by) for group in self.get_groups()]
        groups.sort()
        _dict['groups'] = groups
        _dict['extras'] = {key: value for key, value in self.extras.items()}
        _dict['resources'] = [res.as_dict(core_columns_only=False) \
                              for res in self.resources]
        site_url = config.get('ckan.site_url')
        if site_url:
            _dict['ckan_url'] = '%s/dataset/%s' % (site_url, self.name)
        _dict['relationships'] = [rel.as_dict(self, ref_package_by=ref_package_by) for rel in self.get_relationships()]
        _dict['metadata_modified'] = self.metadata_modified.isoformat() \
            if self.metadata_modified else None
        _dict['metadata_created'] = self.metadata_created.isoformat() \
            if self.metadata_created else None
        import ckan.lib.helpers as h
        _dict['notes_rendered'] = h.render_markdown(self.notes)
        _dict['type'] = self.type or u'dataset'
        return _dict

    def add_relationship(self, type_: str, related_package: Self,
                         comment: str=u''):
        '''Creates a new relationship between this package and a
        related_package. It leaves the caller to commit the change.

        Raises KeyError if the type_ is invalid.
        '''
        from ckan.model import package_relationship
        if type_ in package_relationship.PackageRelationship.get_forward_types():
            subject = self
            object_ = related_package
            direction = "forward"
        elif type_ in package_relationship.PackageRelationship.get_reverse_types():
            rev_type = package_relationship.PackageRelationship.reverse_to_forward_type(type_)
            assert rev_type
            type_ = rev_type
            subject = related_package
            object_ = self
            direction = "reverse"
        else:
            raise KeyError('Package relationship type: %r' % type_)

        rels = self.get_relationships(with_package=related_package,
                                      type=type_, active=False, direction=direction)
        if rels:
            rel = rels[0]
            if comment:
                rel.comment=comment
            if rel.state == core.State.DELETED:
                rel.undelete()
        else:
            rel = package_relationship.PackageRelationship(
                subject=subject,
                object=object_,
                type=type_,
                comment=comment)
        meta.Session.add(rel)
        return rel

    def get_relationships(
            self, with_package: Optional["Package"]=None, type:
            Optional[str]=None, active: bool=True,
            direction: str='both') -> list["PackageRelationship"]:
        '''Returns relationships this package has.
        Keeps stored type/ordering (not from pov of self).'''
        assert direction in ('both', 'forward', 'reverse')
        if with_package:
            assert isinstance(with_package, Package)
        from ckan.model.package_relationship import PackageRelationship
        forward_filters: Any = [PackageRelationship.subject==self]
        reverse_filters: Any = [PackageRelationship.object==self]
        if with_package:
            forward_filters.append(PackageRelationship.object==with_package)
            reverse_filters.append(PackageRelationship.subject==with_package)
        if active:
            forward_filters.append(PackageRelationship.state==core.State.ACTIVE)
            reverse_filters.append(PackageRelationship.state==core.State.ACTIVE)
        if type:
            forward_filters.append(PackageRelationship.type==type)
            reverse_type = PackageRelationship.reverse_type(type)
            reverse_filters.append(PackageRelationship.type==reverse_type)
        q = meta.Session.query(PackageRelationship)
        if direction == 'both':
            q = q.filter(or_(
            and_(*forward_filters),
            and_(*reverse_filters),
            ))
        elif direction == 'forward':
            q = q.filter(and_(*forward_filters))
        elif direction == 'reverse':
            q = q.filter(and_(*reverse_filters))
        return q.all()

    def get_relationships_with(
            self, other_package: "Package", type: Optional[str]=None,
            active: bool=True) -> list["PackageRelationship"]:
        return self.get_relationships(with_package=other_package,
                                      type=type,
                                      active=active)

    def get_relationships_printable(self) -> list[PrintableRelationship]:
        '''Returns a list of tuples describing related packages, including
        non-direct relationships (such as siblings).
        @return: e.g. [(annakarenina, u"is a parent"), ...]
        '''
        from ckan.model.package_relationship import PackageRelationship
        rel_list: list[PrintableRelationship] = []
        for rel in self.get_relationships():
            if rel.subject == self:
                type_printable = PackageRelationship.make_type_printable(rel.type)
                rel_list.append((rel.object, type_printable, rel.comment))
            else:
                type_ = PackageRelationship.forward_to_reverse_type(rel.type)
                assert type_
                type_printable = PackageRelationship.make_type_printable(type_)
                rel_list.append((rel.subject, type_printable, rel.comment))
        # sibling types
        # e.g. 'gary' is a child of 'mum', looking for 'bert' is a child of 'mum'
        # i.e. for each 'child_of' type relationship ...
        for rel_as_subject in self.get_relationships(direction='forward'):
            if rel_as_subject.state != core.State.ACTIVE:
                continue
            # ... parent is the object
            parent_pkg = rel_as_subject.object
            # Now look for the parent's other relationships as object ...
            for parent_rel_as_object in parent_pkg.get_relationships(direction='reverse'):
                if parent_rel_as_object.state != core.State.ACTIVE:
                    continue
                # and check children
                child_pkg = parent_rel_as_object.subject
                if (child_pkg != self and
                    parent_rel_as_object.type == rel_as_subject.type and
                    child_pkg.state == core.State.ACTIVE):
                    type_printable = PackageRelationship.inferred_types_printable['sibling']
                    rel_list.append((child_pkg, type_printable, None))
        return sorted(list(set(rel_list)))
    #
    ## Licenses are currently integrated into the domain model here.

    @classmethod
    def get_license_register(cls) -> "_license.LicenseRegister":
        if not hasattr(cls, '_license_register'):
            cls._license_register = _license.LicenseRegister()
        return cls._license_register

    @classmethod
    def get_license_options(cls) -> list[tuple[str, str]]:
        register = cls.get_license_register()
        return [(l.title, l.id) for l in register.values()]

    def get_license(self) -> Optional["_license.License"]:
        if self.license_id:
            try:
                license: Optional['_license.License'] = self.get_license_register()[self.license_id]
            except KeyError:
                license = None
        else:
            license = None
        return license

    def set_license(self, license: Any) -> None:
        if isinstance(license, _license.License):
            self.license_id = license.id
        elif isinstance(license, dict):
            self.license_id = license['id']
        else:
            msg = "Value not a license object or entity: %s" % repr(license)
            raise Exception(msg)

    license = property(get_license, set_license)

    @maintain.deprecated('`is_private` attriute of model.Package is ' +
                         'deprecated and should not be used.  Use `private`',
                         since="2.1.0")

    def _is_private(self):
        """
        DEPRECATED in 2.1

        A package is private if belongs to any private groups
        """
        return self.private

    is_private = property(_is_private)

    def is_in_group(self, group: "Group") -> bool:
        return group in self.get_groups()

    def get_groups(self, group_type: Optional[str]=None,
                   capacity: Optional[str]=None) -> list["Group"]:
        import ckan.model as model

        # Gets [ (group, capacity,) ...]
        pairs: list[tuple[model.Group, str]] = model.Session.query(
            model.Group,model.Member.capacity
        ). join(
            model.Member, model.Member.group_id == model.Group.id and
            model.Member.table_name == 'package'
        ).join(
            model.Package, model.Package.id == model.Member.table_id
        ).filter(model.Member.state == 'active').filter(
            model.Member.table_id == self.id
        ).all()

        if group_type:
            pairs = [pair for pair in pairs if pair[0].type == group_type]

        groups = [group for (group, cap) in pairs if not capacity or cap == capacity]
        return groups

    @property
    @maintain.deprecated(since="2.9.0")
    def extras_list(self) -> list['PackageExtra']:
        '''DEPRECATED in 2.9

        Returns a list of the dataset's extras, as PackageExtra object
        NB includes deleted ones too (state='deleted')
        '''
        from ckan.model.package_extra import PackageExtra
        return meta.Session.query(PackageExtra) \
            .filter_by(package_id=self.id) \
            .all()


class PackageMember(domain_object.DomainObject):
    package_id: str
    user_id: str
    capacity: str
    modified: datetime.datetime


# import here to prevent circular import
from ckan.model import tag

# type_ignore_reason: incomplete SQLAlchemy types
meta.mapper(Package, package_table, properties={
    # delete-orphan on cascade does NOT work!
    # Why? Answer: because of way SQLAlchemy/our code works there are points
    # where PackageTag object is created *and* flushed but does not yet have
    # the package_id set (this cause us other problems ...). Some time later a
    # second commit happens in which the package_id is correctly set.
    # However after first commit PackageTag does not have Package and
    # delete-orphan kicks in to remove it!
    'package_tags':orm.relation(tag.PackageTag, backref='package',
        cascade='all, delete', #, delete-orphan',
        ),
    })

meta.mapper(tag.PackageTag, tag.package_tag_table)

meta.mapper(PackageMember, package_member_table)
