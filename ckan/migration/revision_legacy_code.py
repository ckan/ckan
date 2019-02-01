# encoding: utf-8

from sqlalchemy.sql import select

import ckan.logic as logic
import ckan.lib.dictization as d
from ckan.lib.dictization.model_dictize import (
    _execute, resource_list_dictize, extras_list_dictize, group_list_dictize)


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
    is_latest_revision = not(context.get(u'revision_id') or
                             context.get(u'revision_date'))
    execute = _execute if is_latest_revision else _execute_with_revision
    # package
    if is_latest_revision:
        if isinstance(pkg, model.PackageRevision):
            pkg = model.Package.get(pkg.id)
        result = pkg
    else:
        package_rev = model.package_revision_table
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
        res = model.resource_revision_table
    q = select([res]).where(res.c.package_id == pkg.id)
    result = execute(q, res, context)
    result_dict["resources"] = resource_list_dictize(result, context)
    result_dict['num_resources'] = len(result_dict.get(u'resources', []))

    # tags
    tag = model.tag_table
    if is_latest_revision:
        pkg_tag = model.package_tag_table
    else:
        pkg_tag = model.package_tag_revision_table
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
        extra = model.extra_revision_table
    q = select([extra]).where(extra.c.package_id == pkg.id)
    result = execute(q, extra, context)
    result_dict["extras"] = extras_list_dictize(result, context)

    # groups
    if is_latest_revision:
        member = model.member_table
    else:
        member = model.member_revision_table
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
        group = model.group_revision_table
    q = select([group]
               ).where(group.c.id == pkg.owner_org) \
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
        rel = model.package_relationship_revision_table
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
    if isinstance(pkg, model.PackageRevision):
        pkg = model.Package.get(pkg.id)

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
    result_dict['metadata_modified'] = pkg.metadata_modified.isoformat()
    result_dict['metadata_created'] = pkg.metadata_created.isoformat() \
        if pkg.metadata_created else None

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
        revision = session.query(context['model'].Revision).filter_by(
            id=revision_id).first()
        if not revision:
            raise logic.NotFound
        revision_date = revision.timestamp

    q = q.where(rev_table.c.revision_timestamp <= revision_date)
    q = q.where(rev_table.c.expired_timestamp > revision_date)

    return session.execute(q)
