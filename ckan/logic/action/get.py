from sqlalchemy.sql import select
from ckan.logic import NotFound, check_access
from ckan.plugins import (PluginImplementations,
                          IGroupController,
                          IPackageController)
import ckan.authz

from ckan.lib.dictization import table_dictize
from ckan.lib.dictization.model_dictize import group_to_api1, group_to_api2
from ckan.lib.dictization.model_dictize import (package_to_api1,
                                                package_to_api2,
                                                package_dictize,
                                                resource_list_dictize,
                                                group_dictize)


def package_list(context):
    model = context["model"]
    user = context["user"]
    api = context["api_version"]
    ref_package_by = 'id' if api == '2' else 'name'

    query = ckan.authz.Authorizer().authorized_query(user, model.Package)
    packages = query.all()
    return [getattr(p, ref_package_by) for p in packages]

def current_package_list_with_resources(context):
    model = context["model"]
    user = context["user"]
    limit = context.get("limit")

    q = ckan.authz.Authorizer().authorized_query(user, model.PackageRevision)
    q = q.order_by(model.package_revision_table.c.revision_timestamp.desc())
    if limit:
        q = q.limit(limit)
    pack_rev = q.all()
    package_list = []
    for package in pack_rev:
        result_dict = table_dictize(package, context)
        res_rev = model.resource_revision_table
        resource_group = model.resource_group_table
        q = select([res_rev], from_obj = res_rev.join(resource_group, 
                   resource_group.c.id == res_rev.c.resource_group_id))
        q = q.where(resource_group.c.package_id == package.id)
        result = q.where(res_rev.c.current == True).execute()
        result_dict["resources"] = resource_list_dictize(result, context)
        license_id = result_dict['license_id']
        if license_id:
            isopen = model.Package.get_license_register()[license_id].isopen()
            result_dict['isopen'] = isopen
        else:
            result_dict['isopen'] = False
        package_list.append(result_dict)
    return package_list

def revision_list(context):

    model = context["model"]
    revs = model.Session.query(model.Revision).all()
    return [rev.id for rev in revs]

def package_revision_list(context):
    model = context["model"]
    id = context["id"]
    pkg = model.Package.get(id)
    if pkg is None:
        raise NotFound
    check_access(pkg, model.Action.READ, context)

    revision_dicts = []
    for revision, object_revisions in pkg.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False))
    return revision_dicts

def group_list(context):
    model = context["model"]
    user = context["user"]
    api = context.get('api_version') or '1'
    ref_group_by = 'id' if api == '2' else 'name';

    query = ckan.authz.Authorizer().authorized_query(user, model.Group)
    groups = query.all() 
    return [getattr(p, ref_group_by) for p in groups]

def group_list_authz(context):
    model = context['model']
    user = context['user']
    pkg = context.get('package')

    query = ckan.authz.Authorizer().authorized_query(user, model.Group, model.Action.EDIT)
    groups = set(query.all())
    return dict((group.id, group.name) for group in groups)

def group_list_availible(context):
    model = context['model']
    user = context['user']
    pkg = context.get('package')

    query = ckan.authz.Authorizer().authorized_query(user, model.Group, model.Action.EDIT)
    groups = set(query.all())

    if pkg:
        groups = groups - set(pkg.groups)

    return [(group.id, group.name) for group in groups]

def licence_list(context):
    model = context["model"]
    license_register = model.Package.get_license_register()
    licenses = license_register.values()
    licences = [l.as_dict() for l in licenses]
    return licences

def tag_list(context):
    model = context["model"]
    tags = model.Session.query(model.Tag).all() #TODO
    tag_list = [tag.name for tag in tags]
    return tag_list

def package_relationships_list(context):

    ##TODO needs to work with dictization layer
    model = context['model']
    user = context['user']
    id = context["id"]
    id2 = context.get("id2")
    rel = context.get("rel")
    api = context.get('api_version') or '1'
    ref_package_by = 'id' if api == '2' else 'name';

    pkg1 = model.Package.get(id)
    pkg2 = None
    if not pkg1:
        raise NotFound('First package named in request was not found.')
    if id2:
        pkg2 = model.Package.get(id2)
        if not pkg2:
            raise NotFound('Second package named in address was not found.')

    if rel == 'relationships':
        rel = None

    relationships = ckan.authz.Authorizer().\
                    authorized_package_relationships(\
                    user, pkg1, pkg2, rel, model.Action.READ)

    if rel and not relationships:
        raise NotFound('Relationship "%s %s %s" not found.'
                                 % (id, rel, id2))
    
    relationship_dicts = [rel.as_dict(pkg1, ref_package_by=ref_package_by) 
                          for rel in relationships]

    return relationship_dicts

def package_show(context):

    model = context['model']
    api = context.get('api_version') or '1'
    id = context['id']

    pkg = model.Package.get(id)

    context['package'] = pkg

    if pkg is None:
        raise NotFound
    check_access(pkg, model.Action.READ, context)

    package_dict = package_dictize(pkg, context)

    for item in PluginImplementations(IPackageController):
        item.read(pkg)

    return package_dict


def revision_show(context):
    model = context['model']
    api = context.get('api_version') or '1'
    id = context['id']
    ref_package_by = 'id' if api == '2' else 'name'

    rev = model.Session.query(model.Revision).get(id)
    if rev is None:
        raise NotFound
    rev_dict = model.revision_as_dict(rev, include_packages=True,
                                      ref_package_by=ref_package_by)
    return rev_dict

def group_show(context):
    model = context['model']
    id = context['id']
    api = context.get('api_version') or '1'


    group = model.Group.get(id)
    context['group'] = group

    if group is None:
        raise NotFound
    check_access(group, model.Action.READ, context)

    group_dict = group_dictize(group, context)

    for item in PluginImplementations(IGroupController):
        item.read(group)

    return group_dict


def tag_show(context):
    model = context['model']
    api = context.get('api_version') or '1'
    id = context['id']
    ref_package_by = 'id' if api == '2' else 'name'
    obj = model.Tag.get(id) #TODO tags
    if obj is None:
        raise NotFound
    package_list = [getattr(pkgtag.package, ref_package_by)
                    for pkgtag in obj.package_tags]
    return package_list 


def package_show_rest(context):

    package_show(context)

    api = context.get('api_version') or '1'

    pkg = context['package']

    if api == '1':
        package_dict = package_to_api1(pkg, context)
    else:
        package_dict = package_to_api2(pkg, context)

    return package_dict

def group_show_rest(context):

    group_show(context)
    api = context.get('api_version') or '1'
    group = context['group']

    if api == '2':
        group_dict = group_to_api2(group, context)
    else:
        group_dict = group_to_api1(group, context)

    return group_dict

