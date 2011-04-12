import ckan.authz
from ckan.logic import NotFound, NotAuthorized, check_access

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
    from ckan.model.license import LicenseRegister
    licenses = LicenseRegister().values()
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
    api = context.get('api_version') or '1'
    ref_package_by = 'name' if api == '1' else 'id';

    pkg = model.Package.get(id)
    if not pkg:
        raise NotFound('First package named in request was not found.')

    relationships = ckan.authz.Authorizer().\
                    authorized_package_relationships(\
                    user, pkg, action=model.Action.READ)
    relationship_dicts = [rel.as_dict(package=pkg, ref_package_by=ref_package_by) for rel in relationships]
    return relationship_dicts

