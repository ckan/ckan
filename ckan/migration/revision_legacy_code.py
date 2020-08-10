# encoding: utf-8

# This file is code to do with vdm revisions, which was removed from CKAN after
# version 2.8. It is only used by a migration and its tests.

import uuid
import six
import datetime

from sqlalchemy.sql import select
from sqlalchemy import (Table, Column, ForeignKey, Boolean, UnicodeText, Text,
                        String, DateTime, and_, inspect)
import sqlalchemy.orm.properties
from sqlalchemy.orm import class_mapper
from sqlalchemy.orm import relation

import ckan.logic as logic
import ckan.lib.dictization as d
from ckan.lib.dictization.model_dictize import (
    _execute, resource_list_dictize, extras_list_dictize, group_list_dictize)
from ckan import model


# This is based on ckan.lib.dictization.model_dictize:package_dictize
# BUT you can ask for a old revision to the package by specifying 'revision_id'
# in the context
def package_dictize_with_revisions(pkg, context):
    '''
    Given a Package object, returns an equivalent dictionary.

    Normally this is the most recent version, but you can provide revision_id
    or revision_date in the context and it will filter to an earlier time.

    May raise NotFound if:
    * the specified revision_id doesn't exist
    * the specified revision_date was before the package was created
    '''
    model = context['model']
    try:
        model.PackageRevision
        # CKAN<=2.8
        revision_model = model
    except AttributeError:
        # CKAN>2.8
        revision_model = RevisionTableMappings.instance()

    is_latest_revision = not(context.get(u'revision_id') or
                             context.get(u'revision_date'))
    execute = _execute if is_latest_revision else _execute_with_revision
    # package
    if is_latest_revision:
        if isinstance(pkg, revision_model.PackageRevision):
            pkg = model.Package.get(pkg.id)
        result = pkg
    else:
        package_rev = revision_model.package_revision_table
        q = select([package_rev]).where(package_rev.c.id == pkg.id)
        result = execute(q, package_rev, context).first()
    if not result:
        raise logic.NotFound
    result_dict = d.table_dictize(result, context)
    # strip whitespace from title
    if result_dict.get(u'title'):
        result_dict['title'] = result_dict['title'].strip()

    # resources
    if is_latest_revision:
        res = model.resource_table
    else:
        res = revision_model.resource_revision_table
    # metadata_modified was added after the revisioning was removed so
    # it does not exist on the resource_revision table.
    mm_col = res._columns.get(u'metadata_modified')
    if mm_col is not None:
        res._columns.remove(mm_col)
    q = select([res]).where(res.c.package_id == pkg.id)
    result = execute(q, res, context)
    result_dict["resources"] = resource_list_dictize(result, context)
    result_dict['num_resources'] = len(result_dict.get(u'resources', []))

    # tags
    tag = model.tag_table
    if is_latest_revision:
        pkg_tag = model.package_tag_table
    else:
        pkg_tag = revision_model.package_tag_revision_table
    q = select([tag, pkg_tag.c.state],
               from_obj=pkg_tag.join(tag, tag.c.id == pkg_tag.c.tag_id)
               ).where(pkg_tag.c.package_id == pkg.id)
    result = execute(q, pkg_tag, context)
    result_dict["tags"] = d.obj_list_dictize(result, context,
                                             lambda x: x["name"])
    result_dict['num_tags'] = len(result_dict.get(u'tags', []))

    # Add display_names to tags. At first a tag's display_name is just the
    # same as its name, but the display_name might get changed later (e.g.
    # translated into another language by the multilingual extension).
    for tag in result_dict['tags']:
        assert u'display_name' not in tag
        tag['display_name'] = tag['name']

    # extras
    if is_latest_revision:
        extra = model.package_extra_table
    else:
        extra = revision_model.extra_revision_table
    q = select([extra]).where(extra.c.package_id == pkg.id)
    result = execute(q, extra, context)
    result_dict["extras"] = extras_list_dictize(result, context)

    # groups
    if is_latest_revision:
        member = model.member_table
    else:
        member = revision_model.member_revision_table
    group = model.group_table
    q = select([group, member.c.capacity],
               from_obj=member.join(group, group.c.id == member.c.group_id)
               ).where(member.c.table_id == pkg.id)\
                .where(member.c.state == u'active') \
                .where(group.c.is_organization == False)  # noqa
    result = execute(q, member, context)
    context['with_capacity'] = False
    # no package counts as cannot fetch from search index at the same
    # time as indexing to it.
    # tags, extras and sub-groups are not included for speed
    result_dict["groups"] = group_list_dictize(result, context,
                                               with_package_counts=False)

    # owning organization
    if is_latest_revision:
        group = model.group_table
    else:
        group = revision_model.group_revision_table
    q = select([group]
               ).where(group.c.id == result_dict['owner_org']) \
                .where(group.c.state == u'active')
    result = execute(q, group, context)
    organizations = d.obj_list_dictize(result, context)
    if organizations:
        result_dict["organization"] = organizations[0]
    else:
        result_dict["organization"] = None

    # relations
    if is_latest_revision:
        rel = model.package_relationship_table
    else:
        rel = revision_model \
            .package_relationship_revision_table
    q = select([rel]).where(rel.c.subject_package_id == pkg.id)
    result = execute(q, rel, context)
    result_dict["relationships_as_subject"] = \
        d.obj_list_dictize(result, context)
    q = select([rel]).where(rel.c.object_package_id == pkg.id)
    result = execute(q, rel, context)
    result_dict["relationships_as_object"] = \
        d.obj_list_dictize(result, context)

    # Extra properties from the domain object
    # We need an actual Package object for this, not a PackageRevision
    # if isinstance(pkg, model.PackageRevision):
    #     pkg = model.Package.get(pkg.id)

    # isopen
    result_dict['isopen'] = pkg.isopen if isinstance(pkg.isopen, bool) \
        else pkg.isopen()

    # type
    # if null assign the default value to make searching easier
    result_dict['type'] = pkg.type or u'dataset'

    # license
    if pkg.license and pkg.license.url:
        result_dict['license_url'] = pkg.license.url
        result_dict['license_title'] = pkg.license.title.split(u'::')[-1]
    elif pkg.license:
        result_dict['license_title'] = pkg.license.title
    else:
        result_dict['license_title'] = pkg.license_id

    # creation and modification date
    if is_latest_revision:
        result_dict['metadata_modified'] = pkg.metadata_modified.isoformat()
    # (If not is_latest_revision, don't use pkg which is the latest version.
    # Instead, use the dates already in result_dict that came from the dictized
    # PackageRevision)
    result_dict['metadata_created'] = pkg.metadata_created.isoformat()

    return result_dict


def _execute_with_revision(q, rev_table, context):
    '''
    Takes an SqlAlchemy query (q) that is (at its base) a Select on an object
    revision table (rev_table), and you provide revision_id or revision_date in
    the context and it will filter the object revision(s) to an earlier time.

    Raises NotFound if context['revision_id'] is provided, but the revision
    ID does not exist.

    Returns [] if there are no results.

    '''
    model = context['model']
    session = model.Session
    revision_id = context.get(u'revision_id')
    revision_date = context.get(u'revision_date')

    if revision_id:
        revision = session.query(revision_model.Revision) \
            .filter_by(id=revision_id).first()
        if not revision:
            raise logic.NotFound
        revision_date = revision.timestamp

    q = q.where(rev_table.c.revision_timestamp <= revision_date)
    q = q.where(rev_table.c.expired_timestamp > revision_date)

    return session.execute(q)


# This function is copied from vdm, but:
# * added the 'frozen' param
# * copied in bits from ckan.model.core.make_revisioned_table()
# * it no longer adds revision_id to the base table (e.g. package.revision_id)
def make_revisioned_table(base_table, frozen=False):
    '''Modify base_table and create correponding revision table.

    A 'frozen' revision table is not written to any more - it's just there
    as a record. It doesn't have the continuity foreign key relation.

    @return revision table (e.g. package_revision)
    '''
    revision_table = Table(base_table.name + u'_revision', base_table.metadata)
    copy_table(base_table, revision_table)
    # we no longer add revision_id to the base table (e.g. package.revision_id)
    # because it is redundant - package_revision.current flags the latest.
    # However the revision_table needs revision_id still
    revision_table.append_column(
        Column(u'revision_id', UnicodeText, ForeignKey(u'revision.id'))
    )

    # create foreign key 'continuity' constraint
    # remember base table primary cols have been exactly duplicated onto our
    # table
    pkcols = []
    for col in base_table.c:
        if col.primary_key:
            pkcols.append(col)
    assert len(pkcols) <= 1,\
        u'Do not support versioning objects with multiple primary keys'
    fk_name = base_table.name + u'.' + pkcols[0].name
    revision_table.append_column(
        Column(u'continuity_id', pkcols[0].type,
               None if frozen else ForeignKey(fk_name))
    )

    # TODO: why do we iterate all the way through rather than just using dict
    # functionality ...? Surely we always have a revision here ...
    for col in revision_table.c:
        if col.name == u'revision_id':
            col.primary_key = True
            revision_table.primary_key.columns.add(col)

    # Copied from ckan.model.core.make_revisioned_table
    revision_table.append_column(Column(u'expired_id',
                                 Text))
    revision_table.append_column(Column(u'revision_timestamp', DateTime))
    revision_table.append_column(Column(u'expired_timestamp', DateTime,
                                 default=datetime.datetime(9999, 12, 31)))
    revision_table.append_column(Column(u'current', Boolean))
    return revision_table


# Copied from vdm
def copy_column(name, src_table, dest_table):
    col = src_table.c[name]
    if col.unique is True:
        # don't copy across unique constraints, as different versions
        # of an object may have identical column values
        col.unique = False
    dest_table.append_column(col.copy())
    # only get it once we have a parent table
    newcol = dest_table.c[name]
    if len(col.foreign_keys) > 0:
        for fk in col.foreign_keys:
            newcol.append_foreign_key(fk.copy())


# Copied from vdm
def copy_table_columns(table):
    columns = []
    for col in table.c:
        newcol = col.copy()
        if len(col.foreign_keys) > 0:
            for fk in col.foreign_keys:
                newcol.foreign_keys.add(fk.copy())
        columns.append(newcol)
    return columns


# Copied from vdm
def copy_table(table, newtable):
    for key in table.c.keys():
        copy_column(key, table, newtable)


# Copied from vdm
def make_revision_table(metadata):
    revision_table = Table(
        u'revision', metadata,
        Column(u'id', UnicodeText, primary_key=True,
               default=lambda: six.u(uuid.uuid4())),
        Column(u'timestamp', DateTime, default=datetime.datetime.utcnow),
        Column(u'author', String(200)),
        Column(u'message', UnicodeText),
        Column(u'state', UnicodeText, default=model.State.ACTIVE)
    )
    return revision_table


# Copied from vdm
def make_Revision(mapper, revision_table):
    mapper(Revision, revision_table, properties={},
           order_by=revision_table.c.timestamp.desc())
    return Revision


# Copied from vdm
class Revision(object):
    '''A Revision to the Database/Domain Model.

    All versioned objects have an associated Revision which can be accessed via
    the revision attribute.
    '''
    def __init__(self, **kw):
        for k, v in six.iteritems(kw):
            setattr(self, k, v)

    # @property
    # def __id__(self):
    #     if self.id is None:
    #         self.id = make_uuid()
    #     return self.id
    # @classmethod
    # def youngest(self, session):
    #     '''Get the youngest (most recent) revision.

    #     If session is not provided assume there is a contextual session.
    #     '''
    #     q = session.query(self)
    #     return q.first()


# Copied from vdm BUT without '.continuity' mapped to the base object
def create_object_version(mapper_fn, base_object, rev_table):
    '''Create the Version Domain Object corresponding to base_object.

    E.g. if Package is our original object we should do::

        # name of Version Domain Object class
        PackageVersion = create_object_version(..., Package, ...)

    NB: This must obviously be called after mapping has happened to
    base_object.
    '''
    # TODO: can we always assume all versioned objects are stateful?
    # If not need to do an explicit check
    class MyClass(object):
        def __init__(self, **kw):
            for k, v in six.iteritems(kw):
                setattr(self, k, v)

    name = base_object.__name__ + u'Revision'
    MyClass.__name__ = str(name)
    MyClass.__continuity_class__ = base_object

    # Must add this so base object can retrieve revisions ...
    base_object.__revision_class__ = MyClass

    ourmapper = mapper_fn(
        MyClass, rev_table,
        # NB: call it all_revisions_... rather than just revisions_... as it
        # will yield all revisions not just those less than the current
        # revision

        # ---------------------
        # Deviate from VDM here
        #
        # properties={
        # 'continuity':relation(base_object,
        #     backref=backref('all_revisions_unordered',
        #         cascade='all, delete, delete-orphan'),
        #         order_by=rev_table.c.revision_id.desc()
        #     ),
        # },
        # order_by=[rev_table.c.continuity_id, rev_table.c.revision_id.desc()]
        # ---------------------
    )
    base_mapper = class_mapper(base_object)
    # add in 'relationship' stuff from continuity onto revisioned obj
    # 3 types of relationship
    # 1. scalar (i.e. simple fk)
    # 2. list (has many) (simple fk the other way)
    # 3. list (m2m) (join table)
    #
    # Also need to check whether related object is revisioned
    #
    # If related object is revisioned then can do all of these
    # If not revisioned can only support simple relation (first case -- why?)
    for prop in base_mapper.iterate_properties:
        try:
            is_relation = prop.__class__ == \
                sqlalchemy.orm.properties.PropertyLoader
        except AttributeError:
            # SQLAlchemy 0.9
            is_relation = prop.__class__ == \
                sqlalchemy.orm.properties.RelationshipProperty

        if is_relation:
            # in sqlachemy 0.4.2
            # prop_remote_obj = prop.select_mapper.class_
            # in 0.4.5
            prop_remote_obj = prop.argument
            remote_obj_is_revisioned = \
                getattr(prop_remote_obj, u'__revisioned__', False)
            # this is crude, probably need something better
            is_many = (prop.secondary is not None or prop.uselist)
            if remote_obj_is_revisioned:
                propname = prop.key
                add_fake_relation(MyClass, propname, is_many=is_many)
            elif not is_many:
                ourmapper.add_property(prop.key, relation(prop_remote_obj))
            else:
                # TODO: actually deal with this
                # raise a warning of some kind
                msg = \
                    u'Skipping adding property %s to revisioned object' % prop

    return MyClass


# Copied from vdm
def add_fake_relation(revision_class, name, is_many=False):
    '''Add a 'fake' relation on ObjectRevision objects.

    These relation are fake in that they just proxy to the continuity object
    relation.
    '''
    def _pget(self):
        related_object = getattr(self.continuity, name)
        if is_many:
            # do not need to do anything to get to right revision since either
            # 1. this is implemented inside the is_many relation we proxy to
            # (as is the case with StatefulLists and assoc proxy setup as used
            # in add_stateful_versioned_m2m)
            # 2. it is not because it is not appropriate to apply it
            # (e.g. package.package_tags which points to PackageTag objects and
            # which is not versioned here ...)
            return related_object
        else:
            return related_object.get_as_of()
    x = property(_pget)
    setattr(revision_class, name, x)


# Tests use this to manually create revisions, that look just like how
# CKAN<=2.8 used to create automatically.
def make_package_revision(package):
    '''Manually create a revision for a package and its related objects
    '''
    instances = [package]
    package_tags = model.Session.query(model.PackageTag) \
        .filter_by(package_id=package.id) \
        .all()
    instances.extend(package_tags)
    extras = model.Session.query(model.PackageExtra) \
        .filter_by(package_id=package.id) \
        .all()
    instances.extend(extras)
    instances.extend(package.resources)
    instances.extend(package.get_groups())
    members = model.Session.query(model.Member) \
        .filter_by(table_id=package.id) \
        .all()
    instances.extend(members)
    make_revision(instances)


# Tests use this to manually create revisions, that look just like how
# CKAN<=2.8 used to create automatically.
def make_revision(instances):
    '''Manually create a revision.

    Copies a new/changed row from a table (e.g. Package) into its
    corresponding revision table (e.g. PackageRevision) and makes an entry
    in the Revision table.
    '''
    # model.repo.new_revision() was called in the model code, which is:
    # vdm.sqlalchemy.tools.Repository.new_revision() which did this:
    Revision = RevisionTableMappings.instance().Revision
    revision = Revision()
    model.Session.add(revision)
    # new_revision then calls:
    # SQLAlchemySession.set_revision(self.session, rev), which is:
    # vdm.sqlalchemy.base.SQLAlchemySession.set_revision() which did this:
    revision.id = str(uuid.uuid4())
    model.Session.add(revision)
    model.Session.flush()

    # In CKAN<=2.8 the revisioned tables (e.g. Package) had a mapper
    # extension: vdm.sqlalchemy.Revisioner(package_revision_table)
    # that triggered on table changes and records a copy in the
    # corresponding revision table (e.g. PackageRevision).

    # In Revisioner.before_insert() it set instance.revision_id, however we no
    # longer have that column on the package (or whatever the instance is)

    # In Revision.after_update() or after_insert() it does this:
    # self.make_revision(instance, mapper, connection)
    # which is vdm.sqlalchemy.base.Revisioner.make_revision()
    # which copies the Package to make a new PackageRevision
    for instance in instances:
        colvalues = {}
        mapper = inspect(type(instance))
        table = mapper.tables[0]
        for key in table.c.keys():
            val = getattr(instance, key)
            colvalues[key] = val
        colvalues['revision_id'] = revision.id
        colvalues['continuity_id'] = instance.id

        # Allow for multiple SQLAlchemy flushes/commits per VDM revision
        revision_table = \
            RevisionTableMappings.instance() \
            .revision_table_mapping[type(instance)]
        ins = revision_table.insert().values(colvalues)
        model.Session.execute(ins)

    # the related Activity would get the revision_id added to it too.
    # Here we simply assume it's the latest activity.
    activity = model.Session.query(model.Activity) \
        .order_by(model.Activity.timestamp.desc()) \
        .first()
    activity.revision_id = revision.id
    model.Session.flush()

    # In CKAN<=2.8 the session extension CkanSessionExtension had some
    # extra code in before_commit() which wrote `revision_timestamp` and
    # `expired_timestamp` values in the revision tables
    # (e.g. package_revision) so that is added here:
    for instance in instances:
        if not hasattr(instance, u'__revision_class__'):
            continue
        revision_cls = instance.__revision_class__
        revision_table = \
            RevisionTableMappings.instance() \
            .revision_table_mapping[type(instance)]
        # when a normal active transaction happens

        # this is an sql statement as we do not want it in object cache
        model.Session.execute(
            revision_table.update().where(
                and_(revision_table.c.id == instance.id,
                     revision_table.c.current is True)
            ).values(current=False)
        )

        q = model.Session.query(revision_cls)
        q = q.filter_by(expired_timestamp=datetime.datetime(9999, 12, 31),
                        id=instance.id)
        results = q.all()
        for rev_obj in results:
            values = {}
            if rev_obj.revision_id == revision.id:
                values['revision_timestamp'] = revision.timestamp
            else:
                values['expired_timestamp'] = revision.timestamp
            model.Session.execute(
                revision_table.update().where(
                    and_(revision_table.c.id == rev_obj.id,
                         revision_table.c.revision_id == rev_obj.revision_id)
                ).values(**values)
            )


# Revision tables (singleton)
class RevisionTableMappings(object):
    _instance = None

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # This uses the strangler pattern to gradually move the revision model
        # out of ckan/model and into this file.
        # We start with references to revision model in ckan/model/ and then
        # gradually move the definitions here
        self.revision_table = make_revision_table(model.meta.metadata)
        self.revision_table.append_column(
            Column(u'approved_timestamp', DateTime))

        self.Revision = make_Revision(model.meta.mapper, self.revision_table)

        self.package_revision_table = \
            make_revisioned_table(model.package_table)
        self.PackageRevision = create_object_version(
            model.meta.mapper, model.Package, self.package_revision_table)

        self.resource_revision_table = \
            make_revisioned_table(model.resource_table)
        self.ResourceRevision = create_object_version(
            model.meta.mapper, model.Resource, self.resource_revision_table)

        self.extra_revision_table = \
            make_revisioned_table(model.package_extra_table)
        self.PackageExtraRevision = create_object_version(
            model.meta.mapper, model.PackageExtra,
            self.extra_revision_table)

        self.package_tag_revision_table = \
            make_revisioned_table(model.package_tag_table)
        self.PackageTagRevision = create_object_version(
            model.meta.mapper, model.PackageTag,
            self.package_tag_revision_table)

        self.member_revision_table = \
            make_revisioned_table(model.member_table)
        self.MemberRevision = create_object_version(
            model.meta.mapper, model.Member,
            self.member_revision_table)

        self.group_revision_table = \
            make_revisioned_table(model.group_table)
        self.GroupRevision = create_object_version(
            model.meta.mapper, model.Group,
            self.group_revision_table)

        self.group_extra_revision_table = \
            make_revisioned_table(model.group_extra_table)
        self.GroupExtraRevision = create_object_version(
            model.meta.mapper, model.GroupExtra,
            self.group_extra_revision_table)

        self.package_relationship_revision_table = \
            make_revisioned_table(model.package_relationship_table)
        # Commented because it gives an error, but we probably don't need it
        # self.PackageRelationshipRevision = \
        #     create_object_version(
        #         model.meta.mapper, model.PackageRelationship,
        #         self.package_relationship_revision_table)

        self.system_info_revision_table = \
            make_revisioned_table(model.system_info_table)
        self.SystemInfoRevision = create_object_version(
            model.meta.mapper, model.SystemInfo,
            self.system_info_revision_table)

        self.revision_table_mapping = {
            model.Package: self.package_revision_table,
            model.Resource: self.resource_revision_table,
            model.PackageExtra: self.extra_revision_table,
            model.PackageTag: self.package_tag_revision_table,
            model.Member: self.member_revision_table,
            model.Group: self.group_revision_table,
        }


# It's easiest if this code works on all versions of CKAN. After CKAN 2.8 the
# revision model is separate from the main model.
try:
    model.PackageExtraRevision
    # CKAN<=2.8
    revision_model = model
except AttributeError:
    # CKAN>2.8
    revision_model = RevisionTableMappings.instance()
