from pylons import config
from sqlalchemy.sql import select, and_
import datetime

from ckan.lib.dictization import (obj_list_dictize,
                                  obj_dict_dictize,
                                  table_dictize)
from ckan.logic import NotFound
import ckan.misc
from ckan.lib.helpers import json

## package save

def group_list_dictize(obj_list, context, sort_key=lambda x:x['display_name']):

    active = context.get('active', True)

    result_list = []

    for obj in obj_list:
        group_dict = table_dictize(obj, context)
        group_dict.pop('created')
        if active and obj.state not in ('active', 'pending'):
            continue

        group_dict['display_name'] = obj.display_name

        group_dict['packages'] = len(obj.packages)

        result_list.append(group_dict)
    return sorted(result_list, key=sort_key)

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
    Raises NotFound if the context['revision_id'] does not exist.
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
    group_rev = model.package_group_revision_table
    group = model.group_table
    q = select([group],
               from_obj=group_rev.join(group, group.c.id == group_rev.c.group_id)
               ).where(group_rev.c.package_id == pkg.id)
    result = _execute_with_revision(q, group_rev, context)
    result_dict["groups"] = obj_list_dictize(result, context)
    #relations
    rel_rev = model.package_relationship_revision_table
    q = select([rel_rev]).where(rel_rev.c.subject_package_id == pkg.id)
    result = _execute_with_revision(q, rel_rev, context)
    result_dict["relationships_as_subject"] = obj_list_dictize(result, context)
    q = select([rel_rev]).where(rel_rev.c.object_package_id == pkg.id)
    result = _execute_with_revision(q, rel_rev, context)
    result_dict["relationships_as_object"] = obj_list_dictize(result, context)
    return result_dict

def group_dictize(group, context):

    result_dict = table_dictize(group, context)
    
    result_dict['display_name'] = group.display_name

    result_dict['extras'] = extras_dict_dictize(
        group._extras, context)

    result_dict['packages'] = obj_list_dictize(
        group.packages, context)

    return result_dict

def tag_dictize(tag, context):

    result_dict = table_dictize(tag, context)

    result_dict["packages"] = obj_list_dictize(
        tag.packages_ordered, context)
    
    return result_dict 

def user_dictize(user, context):

    result_dict = table_dictize(user, context)

    del result_dict['password']
    
    result_dict['display_name'] = user.display_name
    result_dict['number_of_edits'] = user.number_of_edits()
    result_dict['number_administered_packages'] = user.number_administered_packages()

    return result_dict 

## conversion to api

def group_to_api1(group, context):
    
    dictized = group_dictize(group, context)
    dictized["extras"] = dict((extra["key"], extra["value"]) 
                              for extra in dictized["extras"])
    dictized["packages"] = sorted([package["name"] for package in dictized["packages"]])
    return dictized

def group_to_api2(group, context):
    
    dictized = group_dictize(group, context)
    dictized["extras"] = dict((extra["key"], extra["value"]) 
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
        dictized['ckan_url'] = '%s/package/%s' % (site_url, pkg.name)
    dictized['metadata_modified'] = pkg.metadata_modified.isoformat() \
        if pkg.metadata_modified else None
    dictized['metadata_created'] = pkg.metadata_created.isoformat() \
        if pkg.metadata_created else None

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
        dictized['ckan_url'] = '%s/package/%s' % (site_url, pkg.name)
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

