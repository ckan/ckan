import datetime
from calendar import timegm
import logging
logger = logging.getLogger(__name__)

from sqlalchemy.sql import select, and_, union, or_
from sqlalchemy import orm
from sqlalchemy import types, Column, Table
from pylons import config
import vdm.sqlalchemy

import meta
import core
import license as _license
import types as _types
import domain_object
import activity
import extension

import ckan.lib.maintain as maintain
import ckan.lib.dictization as dictization

__all__ = ['Package', 'package_table', 'package_revision_table',
           'PACKAGE_NAME_MAX_LENGTH', 'PACKAGE_NAME_MIN_LENGTH',
           'PACKAGE_VERSION_MAX_LENGTH', 'PackageTagRevision', 'PackageRevision']

PACKAGE_NAME_MAX_LENGTH = 100
PACKAGE_NAME_MIN_LENGTH = 2
PACKAGE_VERSION_MAX_LENGTH = 100

## Our Domain Object Tables
package_table = Table('package', meta.metadata,
        Column('id', types.UnicodeText, primary_key=True, default=_types.make_uuid),
        Column('name', types.Unicode(PACKAGE_NAME_MAX_LENGTH),
               nullable=False, unique=True),
        Column('title', types.UnicodeText),
        Column('version', types.Unicode(PACKAGE_VERSION_MAX_LENGTH)),
        Column('url', types.UnicodeText),
        Column('author', types.UnicodeText),
        Column('author_email', types.UnicodeText),
        Column('maintainer', types.UnicodeText),
        Column('maintainer_email', types.UnicodeText),
        Column('notes', types.UnicodeText),
        Column('license_id', types.UnicodeText),
        Column('type', types.UnicodeText, default=u'dataset'),
        Column('owner_org', types.UnicodeText),
        Column('creator_user_id', types.UnicodeText),
        Column('metadata_modified', types.DateTime, default=datetime.datetime.utcnow),
        Column('private', types.Boolean, default=False),
)


vdm.sqlalchemy.make_table_stateful(package_table)
package_revision_table = core.make_revisioned_table(package_table)

## -------------------
## Mapped classes

class Package(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        domain_object.DomainObject):

    text_search_fields = ['name', 'title']

    def __init__(self, **kw):
        from ckan import model
        super(Package, self).__init__(**kw)
        resource_group = model.ResourceGroup(label="default")
        self.resource_groups_all.append(resource_group)

    @classmethod
    def search_by_name(cls, text_query):
        text_query = text_query
        return meta.Session.query(cls).filter(cls.name.contains(text_query.lower()))

    @classmethod
    def get(cls, reference):
        '''Returns a package object referenced by its id or name.'''
        query = meta.Session.query(cls).filter(cls.id==reference)
        pkg = query.first()
        if pkg == None:
            pkg = cls.by_name(reference)
        return pkg
    # Todo: Make sure package names can't be changed to look like package IDs?

    @property
    def resources(self):
        if len(self.resource_groups_all) == 0:
            return []

        assert len(self.resource_groups_all) == 1, "can only use resources on packages if there is only one resource_group"
        return [resource for resource in 
                self.resource_groups_all[0].resources_all
                if resource.state <> 'deleted']

    def related_packages(self):
        return [self]

    def add_resource(self, url, format=u'', description=u'', hash=u'', **kw):
        import resource
        self.resource_groups_all[0].resources_all.append(resource.Resource(
            resource_group_id=self.resource_groups_all[0].id,
            url=url,
            format=format,
            description=description,
            hash=hash,
            **kw)
        )

    def add_tag(self, tag):
        import ckan.model as model
        if tag in self.get_tags(tag.vocabulary):
            return
        else:
            package_tag = model.PackageTag(self, tag)
            meta.Session.add(package_tag)


    def add_tags(self, tags):
        for tag in tags:
            self.add_tag(tag)

    def add_tag_by_name(self, tag_name, vocab=None, autoflush=True):
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
        from tag import Tag
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

    def get_tags(self, vocab=None):
        """Return a sorted list of this package's tags

        Tags are sorted by their names.

        """
        import ckan.model as model
        query = meta.Session.query(model.Tag)
        query = query.join(PackageTagRevision)
        query = query.filter(PackageTagRevision.tag_id == model.Tag.id)
        query = query.filter(PackageTagRevision.package_id == self.id)
        query = query.filter(and_(
            PackageTagRevision.state == 'active',
            PackageTagRevision.current == True))
        if vocab:
            query = query.filter(model.Tag.vocabulary_id == vocab.id)
        else:
            query = query.filter(model.Tag.vocabulary_id == None)
        query = query.order_by(model.Tag.name)
        tags = query.all()
        return tags

    def remove_tag(self, tag):
        import ckan.model as model
        query = meta.Session.query(model.PackageTag)
        query = query.filter(model.PackageTag.package_id == self.id)
        query = query.filter(model.PackageTag.tag_id == tag.id)
        package_tag = query.one()
        package_tag.delete()
        meta.Session.commit()

    def isopen(self):
        if self.license and self.license.isopen():
            return True
        return False

    def get_average_rating(self):
        total = 0
        for rating in self.ratings:
            total += rating.rating
        if total == 0:
            return None
        else:
            return total / len(self.ratings)

    def as_dict(self, ref_package_by='name', ref_group_by='name'):
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
        _dict['extras'] = dict([(key, value) for key, value in self.extras.items()])
        _dict['ratings_average'] = self.get_average_rating()
        _dict['ratings_count'] = len(self.ratings)
        _dict['resources'] = [res.as_dict(core_columns_only=False) \
                              for res in self.resources]
        site_url = config.get('ckan.site_url', None)
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

    def add_relationship(self, type_, related_package, comment=u''):
        '''Creates a new relationship between this package and a
        related_package. It leaves the caller to commit the change.

        Raises KeyError if the type_ is invalid.
        '''
        import package_relationship
        if type_ in package_relationship.PackageRelationship.get_forward_types():
            subject = self
            object_ = related_package
        elif type_ in package_relationship.PackageRelationship.get_reverse_types():
            type_ = package_relationship.PackageRelationship.reverse_to_forward_type(type_)
            assert type_
            subject = related_package
            object_ = self
        else:
            raise KeyError, 'Package relationship type: %r' % type_

        rels = self.get_relationships(with_package=related_package,
                                      type=type_, active=False, direction="forward")
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

    def get_relationships(self, with_package=None, type=None, active=True,
                          direction='both'):
        '''Returns relationships this package has.
        Keeps stored type/ordering (not from pov of self).'''
        assert direction in ('both', 'forward', 'reverse')
        if with_package:
            assert isinstance(with_package, Package)
        from package_relationship import PackageRelationship
        forward_filters = [PackageRelationship.subject==self]
        reverse_filters = [PackageRelationship.object==self]
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

    def get_relationships_with(self, other_package, type=None, active=True):
        return self.get_relationships(with_package=other_package,
                                      type=type,
                                      active=active)

    def get_relationships_printable(self):
        '''Returns a list of tuples describing related packages, including
        non-direct relationships (such as siblings).
        @return: e.g. [(annakarenina, u"is a parent"), ...]
        '''
        from package_relationship import PackageRelationship
        rel_list = []
        for rel in self.get_relationships():
            if rel.subject == self:
                type_printable = PackageRelationship.make_type_printable(rel.type)
                rel_list.append((rel.object, type_printable, rel.comment))
            else:
                type_printable = PackageRelationship.make_type_printable(\
                    PackageRelationship.forward_to_reverse_type(
                        rel.type)
                    )
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
    def get_license_register(cls):
        if not hasattr(cls, '_license_register'):
            cls._license_register = _license.LicenseRegister()
        return cls._license_register

    @classmethod
    def get_license_options(cls):
        register = cls.get_license_register()
        return [(l.title, l.id) for l in register.values()]

    def get_license(self):
        if self.license_id:
            try:
                license = self.get_license_register()[self.license_id]
            except KeyError:
                license = None
        else:
            license = None
        return license

    def set_license(self, license):
        if type(license) == _license.License:
            self.license_id = license.id
        elif type(license) == dict:
            self.license_id = license['id']
        else:
            msg = "Value not a license object or entity: %s" % repr(license)
            raise Exception, msg

    license = property(get_license, set_license)

    @property
    def all_related_revisions(self):
        '''Returns chronological list of all object revisions related to
        this package. Includes PackageRevisions, PackageTagRevisions,
        PackageExtraRevisions and ResourceRevisions.
        @return List of tuples (revision, [list of object revisions of this
                                           revision])
                Ordered by most recent first.
        '''
        from tag import PackageTag
        from resource import ResourceGroup, Resource
        from package_extra import PackageExtra

        results = {} # revision:[PackageRevision1, PackageTagRevision1, etc.]
        for pkg_rev in self.all_revisions:
            if not results.has_key(pkg_rev.revision):
                results[pkg_rev.revision] = []
            results[pkg_rev.revision].append(pkg_rev)
        for class_ in [ResourceGroup, Resource, PackageExtra, PackageTag]:
            rev_class = class_.__revision_class__
            if class_ == Resource:
                q = meta.Session.query(rev_class).join('continuity',
                                                  'resource_group')
                obj_revisions = q.filter(ResourceGroup.package_id == self.id).all()
            else:
                obj_revisions = meta.Session.query(rev_class).filter_by(package_id=self.id).all()
            for obj_rev in obj_revisions:
                if not results.has_key(obj_rev.revision):
                    results[obj_rev.revision] = []
                results[obj_rev.revision].append(obj_rev)

        result_list = results.items()
        ourcmp = lambda rev_tuple1, rev_tuple2: \
                 cmp(rev_tuple2[0].timestamp, rev_tuple1[0].timestamp)
        return sorted(result_list, cmp=ourcmp)

    @property
    def latest_related_revision(self):
        '''Returns the latest revision for the package and its related
        objects.'''
        return self.all_related_revisions[0][0]

    def diff(self, to_revision=None, from_revision=None):
        '''Overrides the diff in vdm, so that related obj revisions are
        diffed as well as PackageRevisions'''
        from tag import PackageTag
        from resource import ResourceGroup, Resource
        from package_extra import PackageExtra

        results = {} # field_name:diffs
        results.update(super(Package, self).diff(to_revision, from_revision))
        # Iterate over PackageTag, PackageExtra, Resources etc.
        for obj_class in [ResourceGroup, Resource, PackageExtra, PackageTag]:
            obj_rev_class = obj_class.__revision_class__
            # Query for object revisions related to this package
            if obj_class == Resource:
                obj_rev_query = meta.Session.query(obj_rev_class).\
                                join('continuity', 'resource_group').\
                                join('revision').\
                                filter(ResourceGroup.package_id == self.id).\
                                order_by(core.Revision.timestamp.desc())
            else:
                obj_rev_query = meta.Session.query(obj_rev_class).\
                                filter_by(package_id=self.id).\
                                join('revision').\
                                order_by(core.Revision.timestamp.desc())
            # Columns to include in the diff
            cols_to_diff = obj_class.revisioned_fields()
            cols_to_diff.remove('id')
            if obj_class is Resource:
                cols_to_diff.remove('resource_group_id')
            else:
                cols_to_diff.remove('package_id')
            # Particular object types are better known by an invariant field
            if obj_class is PackageTag:
                cols_to_diff.remove('tag_id')
            elif obj_class is PackageExtra:
                cols_to_diff.remove('key')
            # Iterate over each object ID
            # e.g. for PackageTag, iterate over Tag objects
            related_obj_ids = set([related_obj.id for related_obj in obj_rev_query.all()])
            for related_obj_id in related_obj_ids:
                q = obj_rev_query.filter(obj_rev_class.id==related_obj_id)
                to_obj_rev, from_obj_rev = super(Package, self).\
                    get_obj_revisions_to_diff(
                    q, to_revision, from_revision)
                for col in cols_to_diff:
                    values = [getattr(obj_rev, col) if obj_rev else '' for obj_rev in (from_obj_rev, to_obj_rev)]
                    value_diff = self._differ(*values)
                    if value_diff:
                        if obj_class.__name__ == 'PackageTag':
                            display_id = to_obj_rev.tag.name
                        elif obj_class.__name__ == 'PackageExtra':
                            display_id = to_obj_rev.key
                        else:
                            display_id = related_obj_id[:4]
                        key = '%s-%s-%s' % (obj_class.__name__, display_id, col)
                        results[key] = value_diff
        return results

    @property
    @maintain.deprecated('`is_private` attriute of model.Package is ' +
                         'deprecated and should not be used.  Use `private`')
    def is_private(self):
        """
        DEPRECATED in 2.1

        A package is private if belongs to any private groups
        """
        return self.private

    def is_in_group(self, group):
        return group in self.get_groups()

    def get_groups(self, group_type=None, capacity=None):
        import ckan.model as model

        # Gets [ (group, capacity,) ...]
        groups = model.Session.query(model.Group,model.Member.capacity).\
           join(model.Member, model.Member.group_id == model.Group.id and \
                model.Member.table_name == 'package' ).\
           join(model.Package, model.Package.id == model.Member.table_id).\
           filter(model.Member.state == 'active').\
           filter(model.Member.table_id == self.id).all()

        caps   = [g[1] for g in groups]
        groups = [g[0] for g in groups ]
        if group_type:
            groups = [g for g in groups if g.type == group_type]
        if capacity:
            groupcaps = zip( groups,caps )
            groups = [g[0] for g in groupcaps if g[1] == capacity]
        return groups

    @property
    def metadata_created(self):
        import ckan.model as model
        q = meta.Session.query(model.PackageRevision.revision_timestamp)\
            .filter(model.PackageRevision.id == self.id)\
            .order_by(model.PackageRevision.revision_timestamp.asc())
        ts = q.first()
        if ts:
            return ts[0]

    @staticmethod
    def get_fields(core_only=False, fields_to_ignore=None):
        '''Returns a list of the properties of a package.
        @param core_only - limit it to fields actually in the package table and
                           not those on related objects, such as tags & extras.
        @param fields_to_ignore - a list of names of fields to not return if
                           present.
        '''
        # ['id', 'name', 'title', 'version', 'url', 'author', 'author_email', 'maintainer', 'maintainer_email', 'notes', 'license_id', 'state']
        fields = Package.revisioned_fields()
        if not core_only:
            fields += ['resources', 'tags', 'groups', 'extras', 'relationships']

        if fields_to_ignore:
            for field in fields_to_ignore:
                fields.remove(field)

        return fields

    def activity_stream_item(self, activity_type, revision, user_id):
        import ckan.model
        import ckan.logic
        assert activity_type in ("new", "changed"), (
            str(activity_type))

        # Handle 'deleted' objects.
        # When the user marks a package as deleted this comes through here as
        # a 'changed' package activity. We detect this and change it to a
        # 'deleted' activity.
        if activity_type == 'changed' and self.state == u'deleted':
            if meta.Session.query(activity.Activity).filter_by(
                    object_id=self.id, activity_type='deleted').all():
                # A 'deleted' activity for this object has already been emitted
                # FIXME: What if the object was deleted and then activated
                # again?
                return None
            else:
                # Emit a 'deleted' activity for this object.
                activity_type = 'deleted'

        try:
            d = {'package': dictization.table_dictize(self,
                context={'model': ckan.model})}
            return activity.Activity(user_id, self.id, revision.id,
                    "%s package" % activity_type, d)
        except ckan.logic.NotFound:
            # This happens if this package is being purged and therefore has no
            # current revision.
            # TODO: Purge all related activity stream items when a model object
            # is purged.
            return None

    def activity_stream_detail(self, activity_id, activity_type):
        import ckan.model

        # Handle 'deleted' objects.
        # When the user marks a package as deleted this comes through here as
        # a 'changed' package activity. We detect this and change it to a
        # 'deleted' activity.
        if activity_type == 'changed' and self.state == u'deleted':
            activity_type = 'deleted'

        package_dict = dictization.table_dictize(self,
                context={'model':ckan.model})
        return activity.ActivityDetail(activity_id, self.id, u"Package", activity_type,
            {'package': package_dict })

# import here to prevent circular import
import tag

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
    },
    order_by=package_table.c.name,
    extension=[vdm.sqlalchemy.Revisioner(package_revision_table),
               extension.PluginMapperExtension(),
               ],
    )

vdm.sqlalchemy.modify_base_object_mapper(Package, core.Revision, core.State)
PackageRevision = vdm.sqlalchemy.create_object_version(meta.mapper, Package,
        package_revision_table)

def related_packages(self):
    return [self.continuity]

PackageRevision.related_packages = related_packages


vdm.sqlalchemy.modify_base_object_mapper(tag.PackageTag, core.Revision, core.State)
PackageTagRevision = vdm.sqlalchemy.create_object_version(meta.mapper, tag.PackageTag,
        tag.package_tag_revision_table)

PackageTagRevision.related_packages = lambda self: [self.continuity.package]
