from pylons import config
from sqlalchemy.sql import select, and_
import datetime

from ckan.model import PackageRevision
from ckan.lib.dictization import (obj_list_dictize,
                                  obj_dict_dictize,
                                  table_dictize)
from ckan.logic import NotFound
import ckan.misc
from ckan.lib.helpers import json

## package save

def group_list_dictize(obj_list, context, 
                       sort_key=lambda x:x['display_name'], reverse=False):

    active = context.get('active', True)

    result_list = []

    for obj in obj_list:
        if context.get('with_capacity'):
            obj, capacity = obj
            group_dict = table_dictize(obj, context, capacity=capacity)
        else:
            group_dict = table_dictize(obj, context)
        group_dict.pop('created')
        if active and obj.state not in ('active', 'pending'):
            continue

        group_dict['display_name'] = obj.display_name

        group_dict['packages'] = len(obj.active_packages().all())

        result_list.append(group_dict)
    return sorted(result_list, key=sort_key, reverse=reverse)

def resource_list_dictize(res_list, context):

    active = context.get('active', True)
    result_list = []
    for res in res_list:
        if active and res.state not in ('active', 'pending'):
            continue
        result_list.append(resource_dictize(res, context))

    return sorted(result_list, key=lambda x: x["position"])

def extras_dict_dictize(extras_dict, context):
    result_list = []
    for name, extra in extras_dict.iteritems():
        dictized = table_dictize(extra, context)
        if not extra.state == 'active':
            continue
        value = dictized["value"]
        ## This is to make sure the frontend does not show a plain string
        ## as json with brackets.
        if not(context.get("extras_as_string") and isinstance(value, basestring)):
            dictized["value"] = json.dumps(value)
        result_list.append(dictized)

    return sorted(result_list, key=lambda x: x["key"])

def extras_list_dictize(extras_list, context):
    result_list = []
    active = context.get('active', True)
    for extra in extras_list:
        if active and extra.state not in ('active', 'pending'):
            continue
        dictized = table_dictize(extra, context)
        value = dictized["value"]
        if not(context.get("extras_as_string") and isinstance(value, basestring)):
            dictized["value"] = json.dumps(value)
        result_list.append(dictized)

    return sorted(result_list, key=lambda x: x["key"])

def resource_dictize(res, context):
    resource = table_dictize(res, context)
    extras = resource.pop("extras", None)
    if extras:
        resource.update(extras)
    return resource

def _execute_with_revision(q, rev_table, context):
    '''
    Takes an SqlAlchemy query (q) that is (at its base) a Select on an
    object revision table (rev_table), and normally it filters to the
    'current' object revision (latest which has been moderated) and
    returns that.

    But you can provide revision_id, revision_date or pending in the
    context and it will filter to an earlier time or the latest unmoderated
    object revision.
    
    Raises NotFound if context['revision_id'] is provided, but the revision
    ID does not exist.
    
    Returns [] if there are no results.

    '''
    model = context['model']
    meta = model.meta
    session = model.Session
    revision_id = context.get('revision_id')
    revision_date = context.get('revision_date')
    pending = context.get('pending')

    if revision_id:
        revision = session.query(context['model'].Revision).filter_by(
            id=revision_id).first()
        if not revision:
            raise NotFound
        revision_date = revision.timestamp
    
    if revision_date:
        q = q.where(rev_table.c.revision_timestamp <= revision_date)
        q = q.where(rev_table.c.expired_timestamp > revision_date)
    elif pending:
        q = q.where(rev_table.c.expired_timestamp == datetime.datetime(9999, 12, 31))
    else:
        q = q.where(rev_table.c.current == True)

    return session.execute(q)


def package_dictize(pkg, context):
    '''
    Given a Package object, returns an equivalent dictionary.

    Normally this is the current revision (most recent moderated version),
    but you can provide revision_id, revision_date or pending in the
    context and it will filter to an earlier time or the latest unmoderated
    object revision.
    
    May raise NotFound. TODO: understand what the specific set of
    circumstances are that cause this.
    '''
    model = context['model']
    #package
    package_rev = model.package_revision_table
    q = select([package_rev]).where(package_rev.c.id == pkg.id)
    result = _execute_with_revision(q, package_rev, context).first()
    if not result:
        raise NotFound
    result_dict = table_dictize(result, context)
    #resources
    res_rev = model.resource_revision_table
    resource_group = model.resource_group_table
    q = select([res_rev], from_obj = res_rev.join(resource_group, 
               resource_group.c.id == res_rev.c.resource_group_id))
    q = q.where(resource_group.c.package_id == pkg.id)
    result = _execute_with_revision(q, res_rev, context)
    result_dict["resources"] = resource_list_dictize(result, context)
    #tags
    tag_rev = model.package_tag_revision_table
    tag = model.tag_table
    q = select([tag, tag_rev.c.state, tag_rev.c.revision_timestamp], 
        from_obj=tag_rev.join(tag, tag.c.id == tag_rev.c.tag_id)
        ).where(tag_rev.c.package_id == pkg.id)
    result = _execute_with_revision(q, tag_rev, context)
    result_dict["tags"] = obj_list_dictize(result, context, lambda x: x["name"])
    #extras
    extra_rev = model.extra_revision_table
    q = select([extra_rev]).where(extra_rev.c.package_id == pkg.id)
    result = _execute_with_revision(q, extra_rev, context)
    result_dict["extras"] = extras_list_dictize(result, context)
    #groups
    member_rev = model.member_revision_table
    group = model.group_table
    q = select([group],
               from_obj=member_rev.join(group, group.c.id == member_rev.c.group_id)
               ).where(member_rev.c.table_id == pkg.id)
    result = _execute_with_revision(q, member_rev, context)
    result_dict["groups"] = obj_list_dictize(result, context)
    #relations
    rel_rev = model.package_relationship_revision_table
    q = select([rel_rev]).where(rel_rev.c.subject_package_id == pkg.id)
    result = _execute_with_revision(q, rel_rev, context)
    result_dict["relationships_as_subject"] = obj_list_dictize(result, context)
    q = select([rel_rev]).where(rel_rev.c.object_package_id == pkg.id)
    result = _execute_with_revision(q, rel_rev, context)
    result_dict["relationships_as_object"] = obj_list_dictize(result, context)
    
    # Extra properties from the domain object
    # We need an actual Package object for this, not a PackageRevision
    if isinstance(pkg,PackageRevision):
        pkg = model.Package.get(pkg.id)

    # isopen
    result_dict['isopen'] = pkg.isopen if isinstance(pkg.isopen,bool) else pkg.isopen()

    # type
    result_dict['type']= pkg.type

    # creation and modification date
    result_dict['metadata_modified'] = pkg.metadata_modified.isoformat() \
        if pkg.metadata_modified else None
    result_dict['metadata_created'] = pkg.metadata_created.isoformat() \
        if pkg.metadata_created else None

    return result_dict

def _get_members(context, group, member_type):

    model = context['model']
    Entity = getattr(model, member_type[:-1].capitalize())
    return model.Session.query(Entity, model.Member.capacity).\
               join(model.Member, model.Member.table_id == Entity.id).\
               filter(model.Member.group_id == group.id).\
               filter(model.Member.state == 'active').\
               filter(model.Member.table_name == member_type[:-1]).all()


def group_dictize(group, context):
    model = context['model']
    result_dict = table_dictize(group, context)

    result_dict['display_name'] = group.display_name

    result_dict['extras'] = extras_dict_dictize(
        group._extras, context)

    context['with_capacity'] = True

    result_dict['packages'] = obj_list_dictize(
        _get_members(context, group, 'packages'),
        context)

    result_dict['tags'] = tag_list_dictize(
        _get_members(context, group, 'tags'),
        context)

    result_dict['groups'] = group_list_dictize(
        _get_members(context, group, 'groups'),
        context)

    result_dict['users'] = user_list_dictize(
        _get_members(context, group, 'users'),
        context)

    context['with_capacity'] = False

    return result_dict

def tag_list_dictize(tag_list, context):

    result_list = []
    for tag in tag_list:
        if context.get('with_capacity'):
            tag, capacity = tag
            dictized = table_dictize(tag, context, capacity=capacity)
        else:
            dictized = table_dictize(tag, context)
        result_list.append(dictized)

    return result_list

def tag_dictize(tag, context):

    result_dict = table_dictize(tag, context)

    result_dict["packages"] = obj_list_dictize(
        tag.packages_ordered, context)
    
    return result_dict 

def user_list_dictize(obj_list, context, 
                      sort_key=lambda x:x['name'], reverse=False):

    result_list = []

    for obj in obj_list:
        user_dict = user_dictize(obj, context)
        user_dict.pop('apikey')
        result_list.append(user_dict)
    return sorted(result_list, key=sort_key, reverse=reverse)


def user_dictize(user, context):

    if context.get('with_capacity'):
        user, capacity = user
        result_dict = table_dictize(user, context, capacity=capacity)
    else:
        result_dict = table_dictize(user, context)

    del result_dict['password']
    
    result_dict['display_name'] = user.display_name
    result_dict['email_hash'] = user.email_hash
    result_dict['number_of_edits'] = user.number_of_edits()
    result_dict['number_administered_packages'] = user.number_administered_packages()

    return result_dict 

def task_status_dictize(task_status, context):
    return table_dictize(task_status, context)

## conversion to api

def group_to_api1(group, context):
    
    dictized = group_dictize(group, context)
    dictized["extras"] = dict((extra["key"], json.loads(extra["value"])) 
                              for extra in dictized["extras"])
    dictized["packages"] = sorted([package["name"] for package in dictized["packages"]])
    return dictized

def group_to_api2(group, context):
    
    dictized = group_dictize(group, context)
    dictized["extras"] = dict((extra["key"], json.loads(extra["value"])) 
                              for extra in dictized["extras"])
    dictized["packages"] = sorted([package["id"] for package in dictized["packages"]])
    return dictized

def tag_to_api1(tag, context):
    
    dictized = tag_dictize(tag, context)
    return sorted([package["name"] for package in dictized["packages"]])

def tag_to_api2(tag, context):

    dictized = tag_dictize(tag, context)
    return sorted([package["id"] for package in dictized["packages"]])

def resource_dict_to_api(res_dict, package_id, context):
    res_dict.pop("revision_id")
    res_dict.pop("state")
    res_dict.pop("revision_timestamp")
    res_dict["package_id"] = package_id


def package_to_api1(pkg, context):

    dictized = package_dictize(pkg, context)

    dictized.pop("revision_timestamp")

    dictized["groups"] = [group["name"] for group in dictized["groups"]]
    dictized["tags"] = [tag["name"] for tag in dictized["tags"]]
    dictized["extras"] = dict((extra["key"], json.loads(extra["value"])) 
                              for extra in dictized["extras"])
    dictized['notes_rendered'] = ckan.misc.MarkdownFormat().to_html(pkg.notes)

    resources = dictized["resources"] 
   
    for resource in resources:
        resource_dict_to_api(resource, pkg.id, context)

    if pkg.resources:
        dictized['download_url'] = pkg.resources[0].url
            
    dictized['license'] = pkg.license.title if pkg.license else None

    dictized['ratings_average'] = pkg.get_average_rating()
    dictized['ratings_count'] = len(pkg.ratings)
    site_url = config.get('ckan.site_url', None)
    if site_url:
        dictized['ckan_url'] = '%s/dataset/%s' % (site_url, pkg.name)
    metadata_modified = pkg.metadata_modified
    dictized['metadata_modified'] = metadata_modified.isoformat() \
        if metadata_modified else None
    metadata_created = pkg.metadata_created
    dictized['metadata_created'] = metadata_created.isoformat() \
        if metadata_created else None

    subjects = dictized.pop("relationships_as_subject") 
    objects = dictized.pop("relationships_as_object") 
    
    relationships = []
    for relationship in objects:
        model = context['model']
        swap_types = model.PackageRelationship.forward_to_reverse_type
        type = swap_types(relationship['type'])
        relationships.append({'subject': pkg.get(relationship['object_package_id']).name,
                              'type': type,
                              'object': pkg.get(relationship['subject_package_id']).name,
                              'comment': relationship["comment"]})
    for relationship in subjects:
        model = context['model']
        relationships.append({'subject': pkg.get(relationship['subject_package_id']).name,
                              'type': relationship['type'],
                              'object': pkg.get(relationship['object_package_id']).name,
                              'comment': relationship["comment"]})
        
        
    dictized['relationships'] = relationships 
    return dictized

def package_to_api2(pkg, context):

    dictized = package_dictize(pkg, context)

    dictized["groups"] = [group["id"] for group in dictized["groups"]]
    dictized.pop("revision_timestamp")
    
    dictized["tags"] = [tag["name"] for tag in dictized["tags"]]
    dictized["extras"] = dict((extra["key"], json.loads(extra["value"])) 
                              for extra in dictized["extras"])

    resources = dictized["resources"] 
   
    for resource in resources:
        resource_dict_to_api(resource,pkg.id, context)
            
    dictized['license'] = pkg.license.title if pkg.license else None

    dictized['ratings_average'] = pkg.get_average_rating()
    dictized['ratings_count'] = len(pkg.ratings)
    site_url = config.get('ckan.site_url', None)
    if site_url:
        dictized['ckan_url'] = '%s/dataset/%s' % (site_url, pkg.name)
    dictized['metadata_modified'] = pkg.metadata_modified.isoformat() \
        if pkg.metadata_modified else None
    dictized['metadata_created'] = pkg.metadata_created.isoformat() \
        if pkg.metadata_created else None
    dictized['notes_rendered'] = ckan.misc.MarkdownFormat().to_html(pkg.notes)

    subjects = dictized.pop("relationships_as_subject") 
    objects = dictized.pop("relationships_as_object") 
    
    relationships = []
    for relationship in objects:
        model = context['model']
        swap_types = model.PackageRelationship.forward_to_reverse_type
        type = swap_types(relationship['type'])
        relationships.append({'subject': relationship['object_package_id'],
                              'type': type,
                              'object': relationship['subject_package_id'],
                              'comment': relationship["comment"]})
    for relationship in subjects:
        model = context['model']
        relationships.append({'subject': relationship['subject_package_id'],
                              'type': relationship['type'],
                              'object': relationship['object_package_id'],
                              'comment': relationship["comment"]})
        
    dictized['relationships'] = relationships 
    return dictized

def activity_dictize(activity, context):
    activity_dict = table_dictize(activity, context)
    return activity_dict

def activity_list_dictize(activity_list, context):
    activity_dicts = []
    for activity in activity_list:
        activity_dict = activity_dictize(activity, context)
        activity_dicts.append(activity_dict)
    return activity_dicts

def activity_detail_dictize(activity_detail, context):
    return table_dictize(activity_detail, context)

def activity_detail_list_dictize(activity_detail_list, context):
    activity_detail_dicts = []
    for activity_detail in activity_detail_list:
        activity_detail_dict = activity_detail_dictize(activity_detail,
            context)
        activity_detail_dicts.append(activity_detail_dict)
    return activity_detail_dicts
