from sqlalchemy.sql import select
from sqlalchemy import or_, and_, func, desc, case

from ckan.logic import NotFound
from ckan.logic import check_access
from ckan.plugins import (PluginImplementations,
                          IGroupController,
                          IPackageController)
from ckan.authz import Authorizer
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
from ckan.lib.search import query_for, SearchError
import logging

log = logging.getLogger('ckan.logic')

def site_read(context,data_dict=None):
    check_access('site_read',context,data_dict)
    return True

def package_list(context, data_dict):
    '''Lists packages by name or id'''

    model = context["model"]
    user = context["user"]
    api = context.get("api_version", '1')
    ref_package_by = 'id' if api == '2' else 'name'
    
    check_access('package_list', context, data_dict)

    query = model.Session.query(model.PackageRevision)
    query = query.filter(model.PackageRevision.state=='active')
    query = query.filter(model.PackageRevision.current==True)

    packages = query.all()
    return [getattr(p, ref_package_by) for p in packages]

def current_package_list_with_resources(context, data_dict):
    model = context["model"]
    user = context["user"]
    limit = data_dict.get("limit")

    check_access('current_package_list_with_resources', context, data_dict)

    query = model.Session.query(model.PackageRevision)
    query = query.filter(model.PackageRevision.state=='active')
    query = query.filter(model.PackageRevision.current==True)

    query = query.order_by(model.package_revision_table.c.revision_timestamp.desc())
    if limit:
        query = query.limit(limit)
    pack_rev = query.all()
    package_list = []
    for package in pack_rev:
        result_dict = table_dictize(package, context)
        res_rev = model.resource_revision_table
        resource_group = model.resource_group_table
        query = select([res_rev], from_obj = res_rev.join(resource_group,
                   resource_group.c.id == res_rev.c.resource_group_id))
        query = query.where(resource_group.c.package_id == package.id)
        result = query.where(res_rev.c.current == True).execute()
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

    model = context['model']

    check_access('revision_list', context, data_dict)

    revs = model.Session.query(model.Revision).all()
    return [rev.id for rev in revs]

def package_revision_list(context, data_dict):
    model = context["model"]
    id = data_dict["id"]
    pkg = model.Package.get(id)
    if pkg is None:
        raise NotFound

    check_access('package_revision_list',context, data_dict)

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
   
    check_access('group_list',context, data_dict)

    # We need Groups for group_list_dictize
    query = model.Session.query(model.Group).join(model.GroupRevision)
    query = query.filter(model.GroupRevision.state=='active')
    query = query.filter(model.GroupRevision.current==True)
    query = query.order_by(model.Group.name.asc())
    query = query.order_by(model.Group.title.asc())


    groups = query.all()

    if not all_fields:
        group_list = [getattr(p, ref_group_by) for p in groups]
    else:
        group_list = group_list_dictize(groups,context)

    return group_list

def group_list_authz(context, data_dict):
    '''
    Returns a list of groups which the user is allowed to edit

    If 'available_only' is specified, the existing groups in the package are
    removed.

    '''
    model = context['model']
    user = context['user']
    available_only = data_dict.get('available_only',False)

    check_access('group_list_authz',context, data_dict)

    from ckan.authz import Authorizer
    query = Authorizer().authorized_query(user, model.Group, model.Action.EDIT)
    groups = set(query.all())
    
    if available_only:
        package = context.get('package')
        if package:
            groups = groups - set(package.groups)

    return [{'id':group.id,'name':group.name} for group in groups]

def group_revision_list(context, data_dict):
    model = context['model']
    id = data_dict['id']
    group = model.Group.get(id)
    if group is None:
        raise NotFound

    check_access('group_revision_list',context, data_dict)

    revision_dicts = []
    for revision, object_revisions in group.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False,
                                                     include_groups=False))
    return revision_dicts

def licence_list(context, data_dict):
    model = context["model"]

    check_access('licence_list',context, data_dict)

    license_register = model.Package.get_license_register()
    licenses = license_register.values()
    licences = [l.as_dict() for l in licenses]
    return licences

def tag_list(context, data_dict):
    '''Returns a list of tags'''

    model = context['model']
    user = context['user']

    all_fields = data_dict.get('all_fields',None)

    check_access('tag_list',context, data_dict)

    q = data_dict.get('q','')
    if q:
        limit = data_dict.get('limit',25)
        offset = data_dict.get('offset',0)
        return_objects = data_dict.get('return_objects',True)

        query = query_for(model.Tag)
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

    check_access('user_list',context, data_dict)

    q = data_dict.get('q','')
    order_by = data_dict.get('order_by','name')

    query = model.Session.query(
        model.User,
        model.User.name.label('name'),
        model.User.fullname.label('fullname'),
        model.User.about.label('about'),
        model.User.about.label('email'),
        model.User.created.label('created'),
        select([func.count(model.Revision.id)], or_(
                model.Revision.author==model.User.name,
                model.Revision.author==model.User.openid
                )
        ).label('number_of_edits'),
        select([func.count(model.UserObjectRole.id)], and_(
            model.UserObjectRole.user_id==model.User.id,
            model.UserObjectRole.context=='Package',
            model.UserObjectRole.role=='admin'
            )
        ).label('number_administered_packages')
    )

    if q:
        query = model.User.search(q, query)

    if order_by == 'edits':
        query = query.order_by(desc(
            select([func.count(model.Revision.id)], or_(
                model.Revision.author==model.User.name,
                model.Revision.author==model.User.openid
                ))
        ))
    else:
        query = query.order_by(
            case([(or_(model.User.fullname == None, model.User.fullname == ''),
                   model.User.name)],
                 else_=model.User.fullname)
        )

    ## hack for pagination
    if context.get('return_query'):
        return query

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

    check_access('package_relationships_list',context, data_dict)
    
    # TODO: How to handle this object level authz?
    relationships = Authorizer().\
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

    check_access('package_show',context, data_dict)

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

    check_access('group_show',context, data_dict)

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

    check_access('tag_show',context, data_dict)

    tag_dict = tag_dictize(tag,context)
    extended_packages = []
    for package in tag_dict['packages']:
        extended_packages.append(_extend_package_dict(package,context))

    tag_dict['packages'] = extended_packages

    return tag_dict

def user_show(context, data_dict):
    '''Shows user details'''
    model = context['model']
    user = context['user']

    id = data_dict.get('id',None)
    provided_user = data_dict.get('user_obj',None)
    if id:
        user_obj = model.User.get(id)
        context['user_obj'] = user_obj
        if user_obj is None:
            raise NotFound
    elif provided_user:
        context['user_obj'] = user_obj = provided_user
    else:
        raise NotFound

    check_access('user_show',context, data_dict)

    user_dict = user_dictize(user_obj,context)

    if not (Authorizer().is_sysadmin(unicode(user)) or user == user_obj.name):
        # If not sysadmin or the same user, strip sensible info
        del user_dict['apikey']
        del user_dict['reset_key']

    revisions_q = model.Session.query(model.Revision
            ).filter_by(author=user_obj.name)

    revisions_list = []
    for revision in revisions_q.limit(20).all():
        revision_dict = revision_show(context,{'id':revision.id})
        revision_dict['state'] = revision.state
        revisions_list.append(revision_dict)

    user_dict['activity'] = revisions_list

    return user_dict

def package_show_rest(context, data_dict):

    check_access('package_show_rest',context, data_dict)

    package_show(context, data_dict)

    api = context.get('api_version') or '1'
    pkg = context['package']

    if api == '1':
        package_dict = package_to_api1(pkg, context)
    else:
        package_dict = package_to_api2(pkg, context)

    return package_dict

def group_show_rest(context, data_dict):

    check_access('group_show_rest',context, data_dict)

    group_show(context, data_dict)
    api = context.get('api_version') or '1'
    group = context['group']

    if api == '2':
        group_dict = group_to_api2(group, context)
    else:
        group_dict = group_to_api1(group, context)

    return group_dict

def tag_show_rest(context, data_dict):

    check_access('tag_show_rest',context, data_dict)

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

    check_access('package_autocomplete', context, data_dict)

    query = model.Session.query(model.PackageRevision)
    query = query.filter(model.PackageRevision.state=='active')
    query = query.filter(model.PackageRevision.current==True)
    query = query.filter(or_(model.PackageRevision.name.ilike(like_q),
                                model.PackageRevision.title.ilike(like_q)))
    query = query.limit(10)

    pkg_list = []
    for package in query:
        result_dict = {'name':package.name,'title':package.title}
        pkg_list.append(result_dict)

    return pkg_list

def tag_autocomplete(context, data_dict):
    '''Returns tags containing the provided string'''

    model = context['model']
    session = context['session']
    user = context['user']

    check_access('tag_autocomplete', context, data_dict)

    q = data_dict.get('q', None)
    if not q:
        return []

    limit = data_dict.get('limit',10)

    query = query_for('tag')
    query.run(query=q,
              return_objects=True,
              limit=10,
              username=user)

    return [tag.name for tag in query.results]

def format_autocomplete(context, data_dict):
    '''Returns formats containing the provided string'''
    model = context['model']
    session = context['session']
    user = context['user']

    check_access('format_autocomplete', context, data_dict)

    q = data_dict.get('q', None)
    if not q:
        return []

    limit = data_dict.get('limit', 5)
    like_q = u'%' + q + u'%'

    query = session.query(model.ResourceRevision.format,
        func.count(model.ResourceRevision.format).label('total'))\
        .filter(and_(
            model.ResourceRevision.state == 'active',
            model.ResourceRevision.current == True
        ))\
        .filter(model.ResourceRevision.format.ilike(like_q))\
        .group_by(model.ResourceRevision.format)\
        .order_by('total DESC')\
        .limit(limit)

    return [resource.format for resource in query]

def user_autocomplete(context, data_dict):
    '''Returns users containing the provided string'''
    model = context['model']
    session = context['session']
    user = context['user']
    q = data_dict.get('q',None)
    if not q:
        return []

    check_access('user_autocomplete', context, data_dict)

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

    check_access('package_search', context, data_dict)

    # return a list of package ids
    data_dict['fl'] = 'id'

    query = query_for(model.Package)
    query.run(data_dict)

    results = []
    for package in query.results:
        # get the package object
        pkg_query = session.query(model.PackageRevision)\
            .filter(model.PackageRevision.id == package)\
            .filter(and_(
                model.PackageRevision.state == u'active', 
                model.PackageRevision.current == True
            ))
        pkg = pkg_query.first()

        ## if the index has got a package that is not in ckan then
        ## ignore it.
        if not pkg:
            log.warning('package %s in index but not in database' % package)
            continue

        result_dict = table_dictize(pkg, context)
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
    license_id = package_dict.get('license_id')
    if license_id:
        try:
            isopen = model.Package.get_license_register()[license_id].isopen()
        except KeyError:
            isopen = False
        package_dict['isopen'] = isopen
    else:
        package_dict['isopen'] = False

    return package_dict

def resource_search(context, data_dict):
    model = context['model']
    session = context['session']

    fields = data_dict['fields']
    order_by = data_dict.get('order_by')
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    # TODO: should we check for user authentication first?
    q = model.Session.query(model.Resource)
    resource_fields = model.Resource.get_columns()

    for field, terms in fields.items():
        if isinstance(terms, basestring):
            terms = terms.split()
        if field not in resource_fields:
            raise SearchError('Field "%s" not recognised in Resource search.' % field)
        for term in terms:
            model_attr = getattr(model.Resource, field)
            if field == 'hash':                
                q = q.filter(model_attr.ilike(unicode(term) + '%'))
            elif field in model.Resource.get_extra_columns():
                model_attr = getattr(model.Resource, 'extras')

                like = or_(
                    model_attr.ilike(u'''%%"%s": "%%%s%%",%%''' % (field, term)),
                    model_attr.ilike(u'''%%"%s": "%%%s%%"}''' % (field, term))
                )
                q = q.filter(like)
            else:
                q = q.filter(model_attr.ilike('%' + unicode(term) + '%'))
    
    if order_by is not None:
        if hasattr(model.Resource, order_by):
            q = q.order_by(getattr(model.Resource, order_by))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    
    results = []
    for result in q:
        if isinstance(result, tuple) and isinstance(result[0], model.DomainObject):
            # This is the case for order_by rank due to the add_column.
            results.append(result[0])
        else:
            results.append(result)

    return {'count': count, 'results': results}

def tag_search(context, data_dict):
    model = context['model']
    session = context['session']

    query = data_dict.get('query')
    terms = [query] if query else []

    fields = data_dict.get('fields', {})
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    # TODO: should we check for user authentication first?
    q = model.Session.query(model.Tag)
    q = q.distinct().join(model.Tag.package_tags)
    for field, value in fields.items():
        if field in ('tag', 'tags'):
            terms.append(value)

    if not len(terms):
        return

    for term in terms:
        q = q.filter(model.Tag.name.contains(term.lower()))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    results = [r for r in q]
    return {'count': count, 'results': results}
