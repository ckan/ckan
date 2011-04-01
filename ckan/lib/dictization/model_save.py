from ckan.lib.dictization import table_dict_save

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

    obj.extras = res_dict.get("extras", {})

    for key, value in res_dict.iteritems():
        if isinstance(value, list):
            continue
        if key == 'extras':
            continue
        setattr(obj, key, value)

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

    obj_dict = {}
    for extra_dict in extras_dicts:
        obj = table_dict_save(extra_dict, model.PackageExtra, context)
        obj_dict[extra_dict["key"]] = obj

    return obj_dict

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

    extras = package_extras_save(pkg_dict.get("extras", []), pkg, context)
    pkg._extras.clear()
    for key, value in extras.iteritems():
        pkg._extras[key] = value


def group_dict_save(group_dict, context):

    model = context["model"]
    session = context["session"]
    Group = model.Group
    Package = model.Package

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


def package_api_to_dict(api1_dict, context):

    dictized = {}

    for key, value in api1_dict.iteritems():
        new_value = value
        if key == 'tags':
            if isinstance(value, basestring):
                new_value = [{"name": item} for item in value.split()]
            else:
                new_value = [{"name": item} for item in value]
        if key == 'extras':
            new_value = [{"key": extra_key, "value": value[extra_key]} 
                         for extra_key in value]
        dictized[key] = new_value

    return dictized

def group_api1_to_dict(api1_dict, context):

    dictized = {}

    for key, value in api1_dict.iteritems():
        new_value = value
        if key == 'packages':
            new_value = [{"name": item} for item in value]
        if key == 'extras':
            new_value = [{"key": extra_key, "value": value[extra_key]} 
                         for extra_key in value]
        dictized[key] = new_value

    return dictized

def group_api2_to_dict(api1_dict, context):

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
