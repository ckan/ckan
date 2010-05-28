import datetime

from pylons import config
from meta import *
import vdm.sqlalchemy

from types import make_uuid
import full_search
from license import License, LicenseRegister

## VDM-specific tables

revision_table = vdm.sqlalchemy.make_revision_table(metadata)

## Our Domain Object Tables

package_table = Table('package', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.Unicode(100), unique=True, nullable=False),
        Column('title', types.UnicodeText),
        Column('version', types.Unicode(100)),
        Column('url', types.UnicodeText),
        Column('author', types.UnicodeText),
        Column('author_email', types.UnicodeText),
        Column('maintainer', types.UnicodeText),
        Column('maintainer_email', types.UnicodeText),                      
        Column('notes', types.UnicodeText),
        Column('license_id', types.UnicodeText),
)

tag_table = Table('tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('name', types.Unicode(100), unique=True, nullable=False),
)

package_tag_table = Table('package_tag', metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('package_id', types.UnicodeText, ForeignKey('package.id')),
        Column('tag_id', types.UnicodeText, ForeignKey('tag.id')),
        )


vdm.sqlalchemy.make_table_stateful(package_table)
vdm.sqlalchemy.make_table_stateful(package_tag_table)
package_revision_table = vdm.sqlalchemy.make_revisioned_table(package_table)
# TODO: this has a composite primary key ...
package_tag_revision_table = vdm.sqlalchemy.make_revisioned_table(package_tag_table)


## -------------------
## Mapped classes

# TODO: replace this (or at least inherit from) standard SqlalchemyMixin in vdm
class DomainObject(object):
    
    text_search_fields = []

    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def by_name(self, name, autoflush=True):
        obj = Session.query(self).autoflush(autoflush).filter_by(name=name).first()
        return obj

    @classmethod
    def text_search(self, query, term):
        register = self
        make_like = lambda x,y: x.ilike('%' + y + '%')
        q = None
        for field in self.text_search_fields:
            attr = getattr(register, field)
            q = or_(q, make_like(attr, term))
        return query.filter(q)

    @classmethod
    def active(self):
        return Session.query(self).filter_by(state=State.ACTIVE)

    def purge(self):
        sess = orm.object_session(self)
        if hasattr(self, '__revisioned__'): # only for versioned objects ...
            # this actually should auto occur due to cascade relationships but
            # ...
            for rev in self.all_revisions:
                sess.delete(rev)
        sess.delete(self)

    def as_dict(self):
        _dict = {}
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            val = getattr(self, col.name)
            if isinstance(val, datetime.date):
                val = str(val)
            _dict[col.name] = val
        return _dict

    def __str__(self):
        return self.__unicode__().encode('utf8')

    def __unicode__(self):
        repr = u'<%s' % self.__class__.__name__
        table = orm.class_mapper(self.__class__).mapped_table
        for col in table.c:
            repr += u' %s=%s' % (col.name, getattr(self, col.name))
        repr += '>'
        return repr

    def __repr__(self):
        return self.__unicode__()


class Package(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    
    text_search_fields = ['name', 'title']

    @classmethod
    def search_by_name(self, text_query):
        text_query = text_query
        return Session.query(self).filter(self.name.contains(text_query.lower()))

    def update_resources(self, res_dicts, autoflush=True):
        '''Change this package\'s resources.
        @param res_dicts - ordered list of dicts, each detailing a resource
        The resource dictionaries contain 'url', 'format' etc. Optionally they
        can also provide the 'id' of the PackageResource, to help matching
        res_dicts to existing PackageResources. Otherwise, it searches
        for an exactly matching PackageResource.
        The caller is responsible for creating a revision and committing.'''
        import resource
        assert isinstance(res_dicts, (list, tuple))
        # Map the incoming res_dicts (by index) to existing resources
        index_to_res = {}
        # Match up the res_dicts by id
        for i, res_dict in enumerate(res_dicts):
            assert isinstance(res_dict, dict)
            id = res_dict.get('id')
            if id:
                res = Session.query(resource.PackageResource).autoflush(autoflush).get(id)
                index_to_res[i] = res
            elif res_dict.has_key('id'):
                # get rid of blank id - disrupts creation of new resource
                del res_dict['id']
        # Edit resources and create the new ones
        new_res_list = []
        for i, res_dict in enumerate(res_dicts):
            if i in index_to_res:
                res = index_to_res[i]
                for col, value in res_dict.items():
                    setattr(res, col, value)
            else:
                res = resource.PackageResource(**res_dict)
            new_res_list.append(res)
        self.resources = new_res_list

    def add_resource(self, url, format=u'', description=u'', hash=u''):
        import resource
        self.resources.append(resource.PackageResource(
            package_id=self.id,
            url=url,
            format=format,
            description=description,
            hash=hash))

    def add_tag_by_name(self, tagname, autoflush=True):
        if not tagname:
            return
        tag = Tag.by_name(tagname, autoflush=autoflush)
        if not tag:
            tag = Tag(name=tagname)
        if not tag in self.tags:
            self.tags.append(tag)

    @property
    def tags_ordered(self):
        ourcmp = lambda tag1, tag2: cmp(tag1.name, tag2.name)
        return sorted(self.tags, cmp=ourcmp)

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

    def as_dict(self):
        _dict = DomainObject.as_dict(self)
        _dict['tags'] = [tag.name for tag in self.tags]
        _dict['groups'] = [group.name for group in self.groups]
        _dict['extras'] = dict([(extra.key, extra.value) for key, extra in self._extras.items()])
        _dict['ratings_average'] = self.get_average_rating()
        _dict['ratings_count'] = len(self.ratings)
        _dict['resources'] = [{'url':res.url, 'format':res.format, 'description':res.description} for res in self.resources]
        _dict['download_url'] = self.resources[0].url if self.resources else ''
        ckan_host = config.get('ckan_host', None)
        if ckan_host:
            _dict['ckan_url'] = 'http://%s/package/%s' % (ckan_host, self.name)
        _dict['relationships'] = [rel.as_dict(self) for rel in self.get_relationships()]
        return _dict

    def add_relationship(self, type_, related_package, comment=u''):
        '''Creates a new relationship between this package and a
        related_package. It leaves the caller to commit the change.'''
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
            raise NotImplementedError, 'Package relationship type: %r' % type_
            
        rel = package_relationship.PackageRelationship(
            subject=subject,
            object=object_,
            type=type_,
            comment=comment)
        Session.add(rel)
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
            forward_filters.append(PackageRelationship.state==State.ACTIVE)
            reverse_filters.append(PackageRelationship.state==State.ACTIVE)
        if type:
            forward_filters.append(PackageRelationship.type==type)
            reverse_type = PackageRelationship.reverse_type(type)
            reverse_filters.append(PackageRelationship.type==reverse_type)
        q = Session.query(PackageRelationship)
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
                rel_list.append((rel.object, type_printable))
            else:
                type_printable = PackageRelationship.make_type_printable(\
                    PackageRelationship.forward_to_reverse_type(
                        rel.type)
                    )
                rel_list.append((rel.subject, type_printable))
        # sibling types
        # e.g. 'gary' is a child of 'mum', looking for 'bert' is a child of 'mum'
        # i.e. for each 'child_of' type relationship ...
        for rel_as_subject in self.get_relationships(direction='forward'):
            # ... parent is the object
            parent_pkg = rel_as_subject.object
            # Now look for the parent's other relationships as object ...
            for parent_rel_as_object in parent_pkg.get_relationships(direction='reverse'):
                # and check children
                child_pkg = parent_rel_as_object.subject
                if child_pkg != self and \
                       parent_rel_as_object.type == rel_as_subject.type:
                    type_printable = PackageRelationship.inferred_types_printable['sibling']
                    rel_list.append((child_pkg, type_printable))
        return rel_list
    #
    ## Licenses are currently integrated into the domain model here.   
 
    @classmethod
    def get_license_register(self):
        if not hasattr(self, '_license_register'):
            self._license_register = LicenseRegister()
        return self._license_register

    @classmethod
    def get_license_options(self):
        register = self.get_license_register()
        return [(l.title, l.id) for l in register.values()]

    def get_license(self):
        license = None
        if self.license_id:
            try:
                license = self.get_license_register()[self.license_id]
            except Exception, inst:
                # Todo: Log a warning.
                pass
        return license

    def set_license(self, license):
        if type(license) == License:
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
        PackageExtraRevisions and PackageResourceRevisions.
        @return List of tuples (revision, [list of object revisions of this
                                           revision])
                Ordered by most recent first.
        '''
        results = {} # revision:[PackageRevision1, PackageTagRevision1, etc.]
        for pkg_rev in self.all_revisions:
            if not results.has_key(pkg_rev.revision):
                results[pkg_rev.revision] = []
            results[pkg_rev.revision].append(pkg_rev)
        for class_ in get_revisioned_classes_related_to_package():
            rev_class = class_.__revision_class__
            obj_revisions = Session.query(rev_class).filter_by(package_id=self.id).all()
            for obj_rev in obj_revisions:
                if not results.has_key(obj_rev.revision):
                    results[obj_rev.revision] = []
                results[obj_rev.revision].append(obj_rev)
        result_list = results.items()
        ourcmp = lambda rev_tuple1, rev_tuple2: \
                 cmp(rev_tuple2[0].timestamp, rev_tuple1[0].timestamp)
        return sorted(result_list, cmp=ourcmp)

    def diff(self, to_revision=None, from_revision=None):
        '''Overrides the diff in vdm, so that related obj revisions are
        diffed as well as PackageRevisions'''
        import extras, resource
        results = {} # field_name:diffs
        results.update(super(Package, self).diff(to_revision, from_revision))
        # Iterate over PackageTag, PackageExtra, PackageResources etc.
        for obj_class in get_revisioned_classes_related_to_package():
            obj_rev_class = obj_class.__revision_class__
            # Query for object revisions related to this package            
            obj_rev_query = Session.query(obj_rev_class).\
                            filter_by(package_id=self.id).\
                            join('revision').\
                            order_by(Revision.timestamp.desc())
            # Columns to include in the diff
            cols_to_diff = obj_class.revisioned_fields()
            cols_to_diff.remove('id')
            cols_to_diff.remove('package_id')
            # Particular object types are better known by an invariant field
            if obj_class.__name__ == 'PackageTag':
                cols_to_diff.remove('tag_id')
            elif obj_class.__name__ == 'PackageExtra':
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


class Tag(DomainObject):
    def __init__(self, name=''):
        self.name = name

    # not stateful so same as purge
    def delete(self):
        self.purge()

    @classmethod
    def search_by_name(self, text_query):
        text_query = text_query.strip().lower()
        return Session.query(self).filter(self.name.contains(text_query))

    @property
    def packages_ordered(self):
        ourcmp = lambda pkg1, pkg2: cmp(pkg1.name, pkg2.name)
        return sorted(self.packages, cmp=ourcmp)

    def __repr__(self):
        return '<Tag %s>' % self.name


class PackageTag(vdm.sqlalchemy.RevisionedObjectMixin,
        vdm.sqlalchemy.StatefulObjectMixin,
        DomainObject):
    def __init__(self, package=None, tag=None, state=None, **kwargs):
        self.package = package
        self.tag = tag
        self.state = state
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return '<PackageTag %s %s>' % (self.package, self.tag)

class System(DomainObject):
    def __str__(self):
        return 'System'
    def purge(self):
        pass

def get_revisioned_classes_related_to_package():
    import resource
    import extras
    return [PackageTag, resource.PackageResource,
            extras.PackageExtra]

# VDM-specific domain objects
State = vdm.sqlalchemy.State
State.all = [ State.ACTIVE, State.DELETED ]
Revision = vdm.sqlalchemy.make_Revision(mapper, revision_table)

mapper(Package, package_table, properties={
    # delete-orphan on cascade does NOT work!
    # Why? Answer: because of way SQLAlchemy/our code works there are points
    # where PackageTag object is created *and* flushed but does not yet have
    # the package_id set (this cause us other problems ...). Some time later a
    # second commit happens in which the package_id is correctly set.
    # However after first commit PackageTag does not have Package and
    # delete-orphan kicks in to remove it!
    'package_tags':relation(PackageTag, backref='package',
        cascade='all, delete', #, delete-orphan',
        ),
    'package_search':relation(full_search.PackageSearch,
        cascade='all, delete', #, delete-orphan',
        ),
    },
    order_by=package_table.c.name,
    extension = [vdm.sqlalchemy.Revisioner(package_revision_table),
                 full_search.SearchVectorTrigger()]
    )

mapper(Tag, tag_table, properties={
    'package_tags':relation(PackageTag, backref='tag',
        cascade='all, delete, delete-orphan',
        )
    },
    order_by=tag_table.c.name,
    )

mapper(PackageTag, package_tag_table, properties={
    },
    order_by=package_tag_table.c.id,
    extension = [vdm.sqlalchemy.Revisioner(package_tag_revision_table),
                 full_search.SearchVectorTrigger()],
    )

vdm.sqlalchemy.modify_base_object_mapper(Package, Revision, State)
vdm.sqlalchemy.modify_base_object_mapper(PackageTag, Revision, State)
PackageRevision = vdm.sqlalchemy.create_object_version(mapper, Package,
        package_revision_table)
PackageTagRevision = vdm.sqlalchemy.create_object_version(mapper, PackageTag,
        package_tag_revision_table)

from vdm.sqlalchemy.base import add_stateful_versioned_m2m 
vdm.sqlalchemy.add_stateful_versioned_m2m(Package, PackageTag, 'tags', 'tag',
        'package_tags')
vdm.sqlalchemy.add_stateful_versioned_m2m_on_version(PackageRevision, 'tags')
vdm.sqlalchemy.add_stateful_versioned_m2m(Tag, PackageTag, 'packages', 'package',
        'package_tags')


