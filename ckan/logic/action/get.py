from ckan.logic import NotFound, check_access
from ckan.plugins import (PluginImplementations,
                          IGroupController,
                          IPackageController)
import ckan.authz

from ckan.lib.dictization.model_dictize import group_to_api1, group_to_api2
from ckan.lib.dictization.model_dictize import package_to_api1, package_to_api2


def package_list(context):
    model = context["model"]
    user = context["user"]
    api = context["api_version"]
    ref_package_by = 'id' if api == '2' else 'name'

    query = ckan.authz.Authorizer().authorized_query(user, model.Package)
    packages = query.all()
    return [getattr(p, ref_package_by) for p in packages]

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
    
    if pkg is None:
        raise NotFound
    check_access(pkg, model.Action.READ, context)

    if api == '1':
        package_dict = package_to_api1(pkg, context)
    else:
        package_dict = package_to_api2(pkg, context)

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
    if group is None:
        raise NotFound

    check_access(group, model.Action.READ, context)

    for item in PluginImplementations(IGroupController):
        item.read(group)
    if api == '2':
        _dict = group_to_api2(group, context)
    else:
        _dict = group_to_api1(group, context)
    #TODO check it's not none
    return _dict

def tag_show(context):
    model = context['model']
    api = context.get('api') or '1'
    id = context['id']
    ref_package_by = 'id' if api == '2' else 'name'
    obj = model.Tag.get(id) #TODO tags
    if obj is None:
        raise NotFound
    package_list = [getattr(pkgtag.package, ref_package_by)
                    for pkgtag in obj.package_tags]
    return package_list 


