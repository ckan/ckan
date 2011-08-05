from sqlalchemy.sql import select
from sqlalchemy import or_, func, desc

from ckan.logic import NotFound, check_access
from ckan.plugins import (PluginImplementations,
                          IGroupController,
                          IPackageController)
import ckan.authz

from ckan.lib.dictization import table_dictize
from ckan.lib.dictization.model_dictize import (package_dictize,
                                                resource_list_dictize,
                                                group_dictize,
                                                group_list_dictize,
                                                tag_dictize,
                                                user_dictize)

from ckan.lib.dictization.model_dictize import (package_to_api1,
                                                package_to_api2,
                                                group_to_api1,
                                                group_to_api2,
                                                tag_to_api1,
                                                tag_to_api2)
from ckan.lib.search import query_for

def package_list(context, data_dict):
    '''Lists the package by name'''
    model = context["model"]
    user = context["user"]
    api = context.get("api_version", '1')
    ref_package_by = 'id' if api == '2' else 'name'

    query = ckan.authz.Authorizer().authorized_query(user, model.Package)
    packages = query.all()
    return [getattr(p, ref_package_by) for p in packages]

def current_package_list_with_resources(context, data_dict):
    model = context["model"]
    user = context["user"]
    limit = data_dict.get("limit")

    q = ckan.authz.Authorizer().authorized_query(user, model.PackageRevision)
    q = q.filter(model.PackageRevision.state=='active')
    q = q.filter(model.PackageRevision.current==True)

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
            try:
                isopen = model.Package.get_license_register()[license_id].isopen()
                result_dict['isopen'] = isopen
            except KeyError:
                # TODO: create a log message this error?
                result_dict['isopen'] = False 
        else:
            result_dict['isopen'] = False
        package_list.append(result_dict)
    return package_list

def revision_list(context, data_dict):

    model = context["model"]
    revs = model.Session.query(model.Revision).all()
    return [rev.id for rev in revs]

def package_revision_list(context, data_dict):
    model = context["model"]
    id = data_dict["id"]
    pkg = model.Package.get(id)
    if pkg is None:
        raise NotFound
    check_access(pkg, model.Action.READ, context)

    revision_dicts = []
    for revision, object_revisions in pkg.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False,
                                                     include_groups=False))
    return revision_dicts

def group_list(context, data_dict):
    '''Returns a list of groups'''

    model = context['model']
    user = context['user']
    api = context.get('api_version') or '1'
    ref_group_by = 'id' if api == '2' else 'name';

    all_fields = data_dict.get('all_fields',None)

    query = ckan.authz.Authorizer().authorized_query(user, model.Group)
    query = query.order_by(model.Group.name.asc())
    query = query.order_by(model.Group.title.asc())

    groups = query.all()

    if not all_fields:
        group_list = [getattr(p, ref_group_by) for p in groups]
    else:
        group_list = group_list_dictize(groups,context)
    
    return group_list

def group_list_authz(context, data_dict):
    model = context['model']
    user = context['user']
    pkg = context.get('package')

    query = ckan.authz.Authorizer().authorized_query(user, model.Group, model.Action.EDIT)
    groups = set(query.all())
    return dict((group.id, group.name) for group in groups)

def group_list_available(context, data_dict):
    model = context['model']
    user = context['user']
    pkg = context.get('package')

    query = ckan.authz.Authorizer().authorized_query(user, model.Group, model.Action.EDIT)
    groups = set(query.all())

    if pkg:
        groups = groups - set(pkg.groups)

    return [(group.id, group.name) for group in groups]

def group_revision_list(context, data_dict):
    model = context['model']
    id = data_dict['id']
    group = model.Group.get(id)
    if group is None:
        raise NotFound
    check_access(group, model.Action.READ, context)

    revision_dicts = []
    for revision, object_revisions in group.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False,
                                                     include_groups=False))
    return revision_dicts

def licence_list(context, data_dict):
    model = context["model"]
    license_register = model.Package.get_license_register()
    licenses = license_register.values()
    licences = [l.as_dict() for l in licenses]
    return licences

def tag_list(context, data_dict):
    '''Returns a list of tags'''

    model = context['model']
    user = context['user']

    all_fields = data_dict.get('all_fields',None)

    q = data_dict.get('q','')
    if q:
        limit = data_dict.get('limit',25)
        offset = data_dict.get('offset',0)
        return_objects = data_dict.get('return_objects',True)

        query = query_for(model.Tag, backend='sql')
        query.run(query=q,
                  limit=limit,
                  offset=offset,
                  return_objects=return_objects,
                  username=user)
        tags = query.results
    else:
        tags = model.Session.query(model.Tag).all() 
    
    tag_list = []
    if all_fields:
        for tag in tags:
            result_dict = tag_dictize(tag, context)
            tag_list.append(result_dict)
    else:
        tag_list = [tag.name for tag in tags]

    return tag_list

def user_list(context, data_dict):
    '''Lists the current users'''
    model = context['model']
    user = context['user']

    q = data_dict.get('q','')
    order_by = data_dict.get('order_by','name')

    query = model.Session.query(model.User, func.count(model.User.id))
    if q:
        query = model.User.search(q, query)

    if order_by == 'edits':
        query = query.join((model.Revision, or_(
                model.Revision.author==model.User.name,
                model.Revision.author==model.User.openid
                )))
        query = query.group_by(model.User)
        query = query.order_by(desc(func.count(model.User.id)))
    else:
        query = query.group_by(model.User)
        query = query.order_by(model.User.name)

    users_list = []

    for user in query.all():
        result_dict = user_dictize(user[0], context)
        del result_dict['apikey']
        users_list.append(result_dict)

    return users_list

def package_relationships_list(context, data_dict):

    ##TODO needs to work with dictization layer
    model = context['model']
    user = context['user']
    api = context.get('api_version') or '1'

    id = data_dict["id"]
    id2 = data_dict.get("id2")
    rel = data_dict.get("rel")
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

def package_show(context, data_dict):

    model = context['model']
    api = context.get('api_version') or '1'
    id = data_dict['id']

    pkg = model.Package.get(id)

    context['package'] = pkg

    if pkg is None:
        raise NotFound
    check_access(pkg, model.Action.READ, context)

    package_dict = package_dictize(pkg, context)

    for item in PluginImplementations(IPackageController):
        item.read(pkg)

    return package_dict


def revision_show(context, data_dict):
    model = context['model']
    api = context.get('api_version') or '1'
    id = data_dict['id']
    ref_package_by = 'id' if api == '2' else 'name'

    rev = model.Session.query(model.Revision).get(id)
    if rev is None:
        raise NotFound
    rev_dict = model.revision_as_dict(rev, include_packages=True,
                                      ref_package_by=ref_package_by)
    return rev_dict

def group_show(context, data_dict):
    '''Shows group details'''

    model = context['model']
    id = data_dict['id']
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


def tag_show(context, data_dict):
    '''Shows tag details'''

    model = context['model']
    api = context.get('api_version') or '1'
    id = data_dict['id']

    tag = model.Tag.get(id)
    context['tag'] = tag

    if tag is None:
        raise NotFound

    tag_dict = tag_dictize(tag,context)
    extended_packages = []
    for package in tag_dict['packages']:
        extended_packages.append(_extend_package_dict(package,context))

    tag_dict['packages'] = extended_packages

    return tag_dict

def user_show(context, data_dict):
    '''Shows user details'''
    model = context['model']

    id = data_dict.get('id',None)
    provided_user = data_dict.get('user_obj',None)
    if id:
        user = model.User.get(id)
        context['user_obj'] = user
        if user is None:
            raise NotFound
    elif provided_user:
        context['user_obj'] = user = provided_user
    else:
        raise NotFound

    user_dict = user_dictize(user,context)

    revisions_q = model.Session.query(model.Revision
            ).filter_by(author=user.name)
    
    revisions_list = []
    for revision in revisions_q.limit(20).all():
        revision_dict = revision_show(context,{'id':revision.id})
        revision_dict['state'] = revision.state
        revisions_list.append(revision_dict)

    user_dict['activity'] = revisions_list

    return user_dict

def package_show_rest(context, data_dict):

    package_show(context, data_dict)

    api = context.get('api_version') or '1'
    pkg = context['package']

    if api == '1':
        package_dict = package_to_api1(pkg, context)
    else:
        package_dict = package_to_api2(pkg, context)

    return package_dict

def group_show_rest(context, data_dict):

    group_show(context, data_dict)
    api = context.get('api_version') or '1'
    group = context['group']

    if api == '2':
        group_dict = group_to_api2(group, context)
    else:
        group_dict = group_to_api1(group, context)

    return group_dict

def tag_show_rest(context, data_dict):

    tag_show(context, data_dict)
    api = context.get('api_version') or '1'
    tag = context['tag']

    if api == '2':
        tag_dict = tag_to_api2(tag, context)
    else:
        tag_dict = tag_to_api1(tag, context)

    return tag_dict

def package_autocomplete(context, data_dict):
    '''Returns packages containing the provided string'''
    model = context['model']
    session = context['session']
    user = context['user']
    q = data_dict['q']

    like_q = u"%s%%" % q

    #TODO: Auth
    pkg_query = ckan.authz.Authorizer().authorized_query(user, model.Package)
    pkg_query = session.query(model.Package) \
                    .filter(or_(model.Package.name.ilike(like_q),
                                model.Package.title.ilike(like_q)))
    pkg_query = pkg_query.limit(10)

    pkg_list = []
    for package in pkg_query:
        result_dict = table_dictize(package, context)
        pkg_list.append(result_dict)

    return pkg_list

def tag_autocomplete(context, data_dict):
    '''Returns tags containing the provided string'''
    model = context['model']
    session = context['session']
    user = context['user']

    q = data_dict.get('q',None)
    if not q:
        return []

    limit = data_dict.get('limit',10)

    like_q = u"%s%%" % q

    query = query_for('tag', backend='sql')
    query.run(query=like_q,
              return_objects=True,
              limit=10,
              username=user)

    return [tag.name for tag in query.results]

def user_autocomplete(context, data_dict):
    '''Returns users containing the provided string'''
    model = context['model']
    session = context['session']
    user = context['user']
    q = data_dict.get('q',None)
    if not q:
        return []

    limit = data_dict.get('limit',20)

    query = model.User.search(q).limit(limit)

    user_list = []
    for user in query.all():
        result_dict = {}
        for k in ['id', 'name', 'fullname']:
                result_dict[k] = getattr(user,k)

        user_list.append(result_dict)

    return user_list

def package_search(context, data_dict):
    model = context['model']
    session = context['session']
    user = context['user']

    q=data_dict.get('q','')
    fields=data_dict.get('fields',[])
    facet_by=data_dict.get('facet_by',[])
    limit=data_dict.get('limit',20)
    offset=data_dict.get('offset',0)
    return_objects=data_dict.get('return_objects',False)
    filter_by_openness=data_dict.get('filter_by_openness',False)
    filter_by_downloadable=data_dict.get('filter_by_downloadable',False)

    query = query_for(model.Package)
    query.run(query=q,
              fields=fields,
              facet_by=facet_by,
              limit=limit,
              offset=offset,
              return_objects=return_objects,
              filter_by_openness=filter_by_openness,
              filter_by_downloadable=filter_by_downloadable,
              username=user)
    
    results = []
    for package in query.results:
        result_dict = table_dictize(package, context)
        result_dict = _extend_package_dict(result_dict,context)

        results.append(result_dict)

    return {
        'count': query.count,
        'facets': query.facets,
        'results': results
    }

def _extend_package_dict(package_dict,context):
    model = context['model']

    resources = model.Session.query(model.Resource)\
                .join(model.ResourceGroup)\
                .filter(model.ResourceGroup.package_id == package_dict['id'])\
                .all()
    if resources:
        package_dict['resources'] = resource_list_dictize(resources, context)
    else:
        package_dict['resources'] = []
    license_id = package_dict['license_id']
    if license_id:
        try:
            isopen = model.Package.get_license_register()[license_id].isopen()
        except KeyError:
            isopen = False
        package_dict['isopen'] = isopen
    else:
        package_dict['isopen'] = False

    return package_dict
