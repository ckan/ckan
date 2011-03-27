from ckan.lib.dictization import table_dict_save

##package saving

def resource_list_save(res_dicts, context):

    model = context["model"]
    session = context["session"]

    obj_list = []
    for res_dict in res_dicts:
        obj = table_dict_save(res_dict, model.Resource, context)
        obj_list.append(obj)

    return obj_list

def extras_save(extras_dicts, pkg, context):

    model = context["model"]
    session = context["session"]

    obj_dict = {}
    for extra_dict in extras_dicts:
        obj = table_dict_save(extra_dict, model.PackageExtra, context)
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
    for table_dict in group_dicts:
        obj = table_dict_save(table_dict, model.Group, context)
        group_list.append(obj)

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
    Package = model.Package

    pkg = table_dict_save(pkg_dict, Package, context)

    resources = resource_list_save(pkg_dict.get("resources", []), context)
    pkg.resources[:] = resources

    tags = tag_list_save(pkg_dict.get("tags", []), context)
    pkg.tags[:] = tags

    groups = group_list_save(pkg_dict.get("groups", []), context)
    pkg.groups[:] = groups

    subjects = pkg_dict.get("relationships_as_subject", [])
    objects = pkg_dict.get("relationships_as_object", [])
    pkg.relationships_as_subject[:] = relationship_list_save(subjects, context)
    pkg.relationships_as_object[:] = relationship_list_save(objects, context)

    extras = extras_save(pkg_dict.get("extras", []), pkg, context)
    pkg._extras.clear()
    for key, value in extras.iteritems():
        pkg._extras[key] = value

def resource_dict_save(res_dict, context):

    model = context["model"]
    Resource = model.Resource

    res = table_dict_save(res_dict, Resource, context)

