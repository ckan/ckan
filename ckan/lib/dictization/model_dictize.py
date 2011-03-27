from pylons import config

from ckan.lib.dictization import (obj_list_dictize,
                                  obj_dict_dictize,
                                  table_dictize)
import ckan.misc

## package save

def group_list_dictize(obj_list, context, sort_key=lambda x:x):

    result_list = []

    for obj in obj_list:
        group_dict = table_dictize(obj, context)
        group_dict.pop('created')
        result_list.append(group_dict)
    return sorted(result_list, key=sort_key)

def resource_list_dictize(res_list, context):

    result_list = []
    for res in res_list:
        result_list.append(table_dictize(res, context))

    return sorted(result_list, key=lambda x: x["position"])

def resource_dictize(res, context):
    return table_dictize(res, context)

def package_dictize(pkg, context):

    result_dict = table_dictize(pkg, context)

    result_dict["resources"] = resource_list_dictize(pkg.resources, context)

    result_dict["tags"] = obj_list_dictize(
        pkg.tags, context, lambda x: x["name"])
    result_dict["extras"] = obj_dict_dictize(
        pkg._extras, context, lambda x: x["key"])
    result_dict["groups"] = group_list_dictize(
        pkg.groups, context, lambda x: x["name"])
    result_dict["relationships_as_subject"] = obj_list_dictize(
        pkg.relationships_as_subject, context)
    result_dict["relationships_as_object"] = obj_list_dictize(
        pkg.relationships_as_object, context)

    return result_dict

## conversion to api

def resource_dict_to_api(res_dict, package_id, context):
    for key, value in res_dict["extras"].iteritems():
        if key not in res_dict:
            res_dict[key] = value
    res_dict.pop("extras")
    res_dict.pop("revision_id")
    res_dict.pop("state")
    res_dict["package_id"] = package_id


def package_to_api1(pkg, context):

    dictized = package_dictize(pkg, context)
    dictized["groups"] = [group["name"] for group in dictized["groups"]]
    dictized["tags"] = [tag["name"] for tag in dictized["tags"]]
    dictized["extras"] = dict((extra["key"], extra["value"]) 
                              for extra in dictized["extras"])
    dictized['notes_rendered'] = ckan.misc.MarkdownFormat().to_html(pkg.notes)

    resources = dictized["resources"] 
   
    for resource in resources:
        resource_dict_to_api(resource, pkg.id, context)
            
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
    dictized["tags"] = [tag["name"] for tag in dictized["tags"]]
    dictized["extras"] = dict((extra["key"], extra["value"]) 
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

