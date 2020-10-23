# encoding: utf-8

import datetime
import logging

from sqlalchemy.sql import and_, or_
from sqlalchemy import orm, types, Column, Table, ForeignKey

from ckan.common import config
from ckan.model import (
    meta,
    core,
    license as _license,
    types as _types,
    domain_object,
    activity,
    extension,
)
import ckan.lib.maintain as maintain


logger = logging.getLogger(__name__)

__all__ = ['Package', 'package_table', 'PackageMember', 'package_member_table',
           'PACKAGE_NAME_MAX_LENGTH', 'PACKAGE_NAME_MIN_LENGTH',
           'PACKAGE_VERSION_MAX_LENGTH',
           ]


PACKAGE_NAME_MAX_LENGTH = 100
PACKAGE_NAME_MIN_LENGTH = 2
PACKAGE_VERSION_MAX_LENGTH = 100


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

    text_search_fields = ['name', 'title']

    def __init__(self, **kw):
        from ckan import model
        super(Package, self).__init__(**kw)

    @classmethod
    def search_by_name(cls, text_query):
        text_query = text_query
        return meta.Session.query(cls).filter(cls.name.contains(text_query.lower()))

    @classmethod
    def get(cls, reference, for_update=False):
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
    def resources(self):
        return [resource for resource in
                self.resources_all
                if resource.state != 'deleted']

    def related_packages(self):
        return [self]

    def add_resource(self, url, format=u'', description=u'', hash=u'', **kw):
        from ckan.model import resource
        self.resources_all.append(resource.Resource(
            package_id=self.id,
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

    def get_tags(self, vocab=None):
        """Return a sorted list of this package's tags

        Tags are sorted by their names.

        """
        import ckan.model as model
        query = meta.Session.query(model.Tag)
        query = query.join(model.PackageTag)
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
        _dict['extras'] = {key: value for key, value in self.extras.items()}
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
        from ckan.model import package_relationship
        if type_ in package_relationship.PackageRelationship.get_forward_types():
            subject = self
            object_ = related_package
            direction = "forward"
        elif type_ in package_relationship.PackageRelationship.get_reverse_types():
            type_ = package_relationship.PackageRelationship.reverse_to_forward_type(type_)
            assert type_
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

    def get_relationships(self, with_package=None, type=None, active=True,
                          direction='both'):
        '''Returns relationships this package has.
        Keeps stored type/ordering (not from pov of self).'''
        assert direction in ('both', 'forward', 'reverse')
        if with_package:
            assert isinstance(with_package, Package)
        from ckan.model.package_relationship import PackageRelationship
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
        from ckan.model.package_relationship import PackageRelationship
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
            raise Exception(msg)

    license = property(get_license, set_license)

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

    def activity_stream_item(self, activity_type, user_id):
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
            # We save the entire rendered package dict so we can support
            # viewing the past packages from the activity feed.
            dictized_package = ckan.logic.get_action('package_show')({
                'model': ckan.model,
                'session': ckan.model.Session,
                'for_view': False,  # avoid ckanext-multilingual translating it
                'ignore_auth': True
            }, {
                'id': self.id,
                'include_tracking': False
            })
        except ckan.logic.NotFound:
            # This happens if this package is being purged and therefore has no
            # current revision.
            # TODO: Purge all related activity stream items when a model object
            # is purged.
            return None

        actor = meta.Session.query(ckan.model.User).get(user_id)

        return activity.Activity(
            user_id,
            self.id,
            "%s package" % activity_type,
            {
                'package': dictized_package,
                # We keep the acting user name around so that actions can be
                # properly displayed even if the user is deleted in the future.
                'actor': actor.name if actor else None
            }
        )

    def set_rating(self, user_or_ip, rating):
        '''Record a user's rating of this package.

        The caller function is responsible for doing the commit.

        If a rating is outside the range MAX_RATING - MIN_RATING then a
        RatingValueException is raised.

        @param user_or_ip - user object or an IP address string
        '''
        user = None
        from ckan.model.user import User
        from ckan.model.rating import Rating, MAX_RATING, MIN_RATING
        if isinstance(user_or_ip, User):
            user = user_or_ip
            rating_query = meta.Session.query(Rating)\
                               .filter_by(package=self, user=user)
        else:
            ip = user_or_ip
            rating_query = meta.Session.query(Rating)\
                               .filter_by(package=self, user_ip_address=ip)

        try:
            rating = float(rating)
        except TypeError:
            raise RatingValueException
        except ValueError:
            raise RatingValueException
        if rating > MAX_RATING or rating < MIN_RATING:
            raise RatingValueException

        if rating_query.count():
            rating_obj = rating_query.first()
            rating_obj.rating = rating
        elif user:
            rating = Rating(package=self,
                            user=user,
                            rating=rating)
            meta.Session.add(rating)
        else:
            rating = Rating(package=self,
                            user_ip_address=ip,
                            rating=rating)
            meta.Session.add(rating)

    @property
    @maintain.deprecated()
    def extras_list(self):
        '''DEPRECATED in 2.9

        Returns a list of the dataset's extras, as PackageExtra object
        NB includes deleted ones too (state='deleted')
        '''
        from ckan.model.package_extra import PackageExtra
        return meta.Session.query(PackageExtra) \
            .filter_by(package_id=self.id) \
            .all()


class PackageMember(domain_object.DomainObject):
    pass


class RatingValueException(Exception):
    pass

# import here to prevent circular import
from ckan.model import tag

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
    extension=[extension.PluginMapperExtension()],
    )

meta.mapper(tag.PackageTag, tag.package_tag_table, properties={
    'pkg':orm.relation(Package, backref='package_tag_all',
        cascade='none',
        )
    },
    order_by=tag.package_tag_table.c.id,
    extension=[extension.PluginMapperExtension()],
    )

meta.mapper(PackageMember, package_member_table)
