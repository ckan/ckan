from ckan.lib.dictization import table_dict_save
from sqlalchemy.orm import class_mapper
import json

##package saving

def resource_dict_save(res_dict, context):

    model = context["model"]
    session = context["session"]

    obj = None

    id = res_dict.get("id")
    
    if id:
        obj = session.query(model.Resource).get(id)

    if not obj:
        obj = model.Resource()

    table = class_mapper(model.Resource).mapped_table
    fields = [field.name for field in table.c]

    for key, value in res_dict.iteritems():
        if isinstance(value, list):
            continue
        if key == 'extras':
            continue
        if key in fields:
            setattr(obj, key, value)
        else:
            obj.extras[key] = value

    session.add(obj)

    return obj

def resource_list_save(res_dicts, context):

    obj_list = []
    for res_dict in res_dicts:
        obj = resource_dict_save(res_dict, context)
        obj_list.append(obj)

    return obj_list

def package_extras_save(extras_dicts, pkg, context):

    model = context["model"]
    session = context["session"]

    result_dict = {}
    for extra_dict in extras_dicts:
        result_dict[extra_dict["key"]] = json.loads(extra_dict["value"])

    return result_dict

def group_extras_save(extras_dicts, pkg, context):

    model = context["model"]
    session = context["session"]

    obj_dict = {}
    for extra_dict in extras_dicts:
        obj = table_dict_save(extra_dict, model.GroupExtra, context)
        obj_dict[extra_dict["key"]] = obj

    return obj_dict

def tag_list_save(tag_dicts, context):

    model = context["model"]
    session = context["session"]

    tag_list = []
    for table_dict in tag_dicts:
        obj = table_dict_save(table_dict, model.Tag, context)
        tag_list.append(obj)

    return tag_list

def group_list_save(group_dicts, context):

    model = context["model"]
    session = context["session"]

    group_list = []
    for group_dict in group_dicts:
        id = group_dict.get("id")
        name = group_dict.get("name")
        if id:
            group = session.query(model.Group).get(id)
        else:
            group = session.query(model.Group).filter_by(name=name).first()

        group_list.append(group)

    return group_list
    
def relationship_list_save(relationship_dicts, context):

    model = context["model"]
    session = context["session"]

    relationship_list = []
    for relationship_dict in relationship_dicts:
        obj = table_dict_save(relationship_dict, 
                              model.PackageRelationship, context)
        relationship_list.append(obj)

    return relationship_list

def package_dict_save(pkg_dict, context):

    model = context["model"]
    package = context.get("package")
    if package:
        pkg_dict["id"] = package.id 
    Package = model.Package

    pkg = table_dict_save(pkg_dict, Package, context)

    resources = resource_list_save(pkg_dict.get("resources", []), context)
    if resources:
        pkg.resources[:] = resources

    tags = tag_list_save(pkg_dict.get("tags", []), context)
    if tags:
        pkg.tags[:] = tags

    groups = group_list_save(pkg_dict.get("groups", []), context)
    if groups:
        pkg.groups[:] = groups

    subjects = pkg_dict.get("relationships_as_subject", [])
    if subjects:
        pkg.relationships_as_subject[:] = relationship_list_save(subjects, context)
    objects = pkg_dict.get("relationships_as_object", [])
    if objects:
        pkg.relationships_as_object[:] = relationship_list_save(objects, context)

    extras = package_extras_save(pkg_dict.get("extras", {}), pkg, context)
    if extras:
        old_extras = set(pkg.extras.keys())
        new_extras = set(extras.keys())
        for key in old_extras - new_extras:
            del pkg.extras[key]
        for key in new_extras:
            pkg.extras[key] = extras[key] 

    return pkg


def group_dict_save(group_dict, context):

    model = context["model"]
    session = context["session"]
    group = context.get("group")
    Group = model.Group
    Package = model.Package
    if group:
        group_dict["id"] = group.id 

    group = table_dict_save(group_dict, Group, context)

    extras = group_extras_save(group_dict.get("extras", []), group, context)

    group._extras.clear()
    for key, value in extras.iteritems():
        group._extras[key] = value

    package_dicts = group_dict.get("packages", [])

    packages = []

    for package in package_dicts:
        pkg = None
        id = package.get("id")
        if id:
            pkg = session.query(Package).get(id)
        if not pkg:
            pkg = session.query(Package).filter_by(name=package["name"]).one()
        packages.append(pkg)

    group.packages[:] = packages

    return group


def package_api_to_dict(api1_dict, context):

    package = context.get("package")

    dictized = {}

    for key, value in api1_dict.iteritems():
        new_value = value
        if key == 'tags':
            if isinstance(value, basestring):
                new_value = [{"name": item} for item in value.split()]
            else:
                new_value = [{"name": item} for item in value]
        if key == 'extras':
            updated_extras = {}
            if package:
                updated_extras.update(package.extras)
            updated_extras.update(value)

            new_value = []
            for extras_key, extras_value in updated_extras.iteritems():
                if extras_value is not None:
                    new_value.append({"key": extras_key,
                                      "value": json.dumps(extras_value)})

        dictized[key] = new_value

    groups = dictized.pop('groups', None)
    download_url = dictized.pop('download_url', None)
    if download_url and not dictized.get('resources'):
        dictized["resources"] = [{'url': download_url}]

    download_url = dictized.pop('download_url', None)
    
    return dictized

def group_api_to_dict(api1_dict, context):

    dictized = {}

    for key, value in api1_dict.iteritems():
        new_value = value
        if key == 'packages':
            new_value = [{"id": item} for item in value]
        if key == 'extras':
            new_value = [{"key": extra_key, "value": value[extra_key]} 
                         for extra_key in value]
        dictized[key] = new_value

    return dictized

