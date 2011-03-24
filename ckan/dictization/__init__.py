import datetime
from sqlalchemy.orm import class_mapper
from pylons import config

def table_dictize(obj, state):

    result_dict = {}

    model = state["model"]
    session = state["session"]

    ModelClass = obj.__class__
    table = class_mapper(ModelClass).mapped_table

    fields = [field.name for field in table.c]
    if hasattr(obj, "get_extra_columns"):
        fields.extend(obj.get_extra_columns())

    for field in fields:
        name = field
        value = getattr(obj, name)
        if value is None:
            result_dict[name] = value
        elif isinstance(value, dict):
            result_dict[name] = value
        elif isinstance(value, int):
            result_dict[name] = value
        elif isinstance(value, datetime.datetime):
            result_dict[name] = value.isoformat()
        else:
            result_dict[name] = unicode(value)

    return result_dict


def obj_list_dictize(obj_list, state, sort_key=lambda x:x):

    result_list = []

    for obj in obj_list:
        result_list.append(table_dictize(obj, state))

    return sorted(result_list, key=sort_key)

def obj_dict_dictize(obj_dict, state, sort_key=lambda x:x):

    result_list = []

    for key, obj in obj_dict.items():
        result_list.append(table_dictize(obj, state))

    return sorted(result_list, key=sort_key)

def package_dictize(pkg, state):

    result_dict = table_dictize(pkg, state)

    result_dict["resources"] = obj_list_dictize(pkg.resources, state)
    result_dict["tags"] = obj_list_dictize(pkg.tags, state, lambda x: x["name"])
    result_dict["extras"] = obj_dict_dictize(pkg._extras, state)
    result_dict["groups"] = obj_list_dictize(pkg.groups, state)
    result_dict["relationships_as_subject"] = obj_list_dictize(pkg.relationships_as_subject, state)
    result_dict["relationships_as_object"] = obj_list_dictize(pkg.relationships_as_object, state)

    return result_dict


def resource_dict_to_api(res_dict, package_id, state):
    for key, value in res_dict["extras"].iteritems():
        if key not in res_dict:
            res_dict[key] = value
    res_dict.pop("extras")
    res_dict.pop("revision_id")
    res_dict.pop("state")
    res_dict["package_id"] = package_id

def package_to_api1(pkg, state):

    dictized = package_dictize(pkg, state)
    dictized["groups"] = [group["name"] for group in dictized["groups"]]
    dictized["tags"] = [tag["name"] for tag in dictized["tags"]]
    dictized["extras"] = dict((extra["key"], extra["value"]) 
                              for extra in dictized["extras"])

    resources = dictized["resources"] 
   
    for resource in resources:
        resource_dict_to_api(resource, pkg.id, state)
            
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
        model = state['model']
        swap_types = model.PackageRelationship.forward_to_reverse_type
        type = swap_types(relationship['type'])
        relationships.append({'subject': pkg.get(relationship['object_package_id']).name,
                              'type': type,
                              'object': pkg.get(relationship['subject_package_id']).name,
                              'comment': relationship["comment"]})
    for relationship in subjects:
        model = state['model']
        relationships.append({'subject': pkg.get(relationship['subject_package_id']).name,
                              'type': relationship['type'],
                              'object': pkg.get(relationship['object_package_id']).name,
                              'comment': relationship["comment"]})
        
        
    dictized['relationships'] = relationships 
    return dictized

def package_to_api2(pkg, state):

    dictized = package_dictize(pkg, state)
    dictized["groups"] = [group["id"] for group in dictized["groups"]]
    dictized["tags"] = [tag["name"] for tag in dictized["tags"]]
    dictized["extras"] = dict((extra["key"], extra["value"]) 
                              for extra in dictized["extras"])

    resources = dictized["resources"] 
   
    for resource in resources:
        resource_dict_to_api(resource,pkg.id, state)
            
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
        model = state['model']
        swap_types = model.PackageRelationship.forward_to_reverse_type
        type = swap_types(relationship['type'])
        relationships.append({'subject': relationship['object_package_id'],
                              'type': type,
                              'object': relationship['subject_package_id'],
                              'comment': relationship["comment"]})
    for relationship in subjects:
        model = state['model']
        relationships.append({'subject': relationship['subject_package_id'],
                              'type': relationship['type'],
                              'object': relationship['object_package_id'],
                              'comment': relationship["comment"]})
        
        
    dictized['relationships'] = relationships 
    return dictized
