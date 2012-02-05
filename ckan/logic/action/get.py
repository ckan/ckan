from sqlalchemy.sql import select
from sqlalchemy.orm import aliased
from sqlalchemy import or_, and_, func, desc, case
import uuid
from pylons import config
import logging

import ckan
from ckan.lib.base import _
from ckan.logic import NotFound, ParameterError
from ckan.logic import check_access
from ckan.model import misc
from ckan.plugins import (PluginImplementations,
                          IGroupController,
                          IPackageController)
from pylons import config
from ckan.authz import Authorizer
from ckan.lib.dictization import table_dictize
from ckan.lib.dictization.model_dictize import (package_dictize,
                                                resource_list_dictize,
                                                resource_dictize,
                                                group_dictize,
                                                group_list_dictize,
                                                tag_dictize,
                                                task_status_dictize,
                                                user_dictize,
                                                activity_list_dictize,
                                                activity_detail_list_dictize)

from ckan.lib.dictization.model_dictize import (package_to_api1,
                                                package_to_api2,
                                                group_to_api1,
                                                group_to_api2,
                                                tag_to_api1,
                                                tag_to_api2)
from ckan.lib.search import query_for, SearchError
from ckan.lib.base import render
from webhelpers.html import literal
from ckan.logic.action import get_domain_object

log = logging.getLogger('ckan.logic')

def _package_list_with_resources(context, package_revision_list):
    package_list = []
    model = context["model"]
    for package in package_revision_list:
        result_dict = package_dictize(package,context)
        package_list.append(result_dict)
    return package_list

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
    return _package_list_with_resources(context, pack_rev)

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
    order_by = data_dict.get('order_by', 'name')
    if order_by not in set(('name', 'packages')):
        raise ParameterError('"order_by" value %r not implemented.' % order_by)
    all_fields = data_dict.get('all_fields',None)

    check_access('group_list',context, data_dict)

    query = model.Session.query(model.Group).join(model.GroupRevision)
    query = query.filter(model.GroupRevision.state=='active')
    query = query.filter(model.GroupRevision.current==True)

    if order_by == 'name':
        sort_by, reverse = 'name', False

    groups = query.all()

    if order_by == 'packages':
        sort_by, reverse = 'packages', True

    group_list = group_list_dictize(groups, context,
                                    lambda x:x[sort_by], reverse)

    if not all_fields:
        group_list = [group[ref_group_by] for group in group_list]

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

    query = Authorizer().authorized_query(user, model.Group, model.Action.EDIT)
    groups = set(query.all())

    if available_only:
        package = context.get('package')
        if package:
            groups = groups - set(package.get_groups())

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

    check_access('package_show', context, data_dict)

    package_dict = package_dictize(pkg, context)

    for item in PluginImplementations(IPackageController):
        item.read(pkg)

    return package_dict

def resource_show(context, data_dict):
    model = context['model']
    api = context.get('api_version') or '1'
    id = data_dict['id']

    resource = model.Resource.get(id)
    context['resource'] = resource

    if not resource:
        raise NotFound

    check_access('resource_show', context, data_dict)

    return resource_dictize(resource, context)

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

def group_package_show(context, data_dict):
    """
    Shows all packages belonging to a group.
    """
    model = context["model"]
    user = context["user"]
    id = data_dict['id']
    limit = data_dict.get("limit")

    group = model.Group.get(id)
    context['group'] = group
    if group is None:
        raise NotFound

    check_access('group_show', context, data_dict)

    query = model.Session.query(model.PackageRevision)\
        .filter(model.PackageRevision.state=='active')\
        .filter(model.PackageRevision.current==True)\
        .join(model.Member, model.Member.table_id==model.PackageRevision.id)\
        .join(model.Group, model.Group.id==model.Member.group_id)\
        .filter_by(id=group.id)\
        .order_by(model.PackageRevision.name)

    if limit:
        query = query.limit(limit)

    if context.get('return_query'):
        return query

    result = []
    for pkg_rev in query.all():
        result.append(package_dictize(pkg_rev, context))

    return result

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
        pkg = model.Package.get(package['id'])
        extended_packages.append(package_dictize(pkg,context))

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

    user_dict['datasets'] = []
    dataset_q = model.Session.query(model.Package).join(model.PackageRole
            ).filter_by(user=user_obj, role=model.Role.ADMIN
            ).limit(50)

    for dataset in dataset_q:
        try:
            dataset_dict = package_show(context, {'id': dataset.id})
        except ckan.logic.NotAuthorized:
            continue
        user_dict['datasets'].append(dataset_dict)

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
    '''Returns packages containing the provided string in either the name
    or the title'''

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

    q_lower = q.lower()
    pkg_list = []
    for package in query:
        if package.name.startswith(q_lower):
            match_field = 'name'
            match_displayed = package.name
        else:
            match_field = 'title'
            match_displayed = '%s (%s)' % (package.title, package.name)
        result_dict = {'name':package.name, 'title':package.title,
                       'match_field':match_field, 'match_displayed':match_displayed}
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

    # check if some extension needs to modify the search params
    for item in PluginImplementations(IPackageController):
        data_dict = item.before_search(data_dict)

    # the extension may have decided that it's no necessary to perform the query
    abort = data_dict.get('abort_search',False)

    results = []
    if not abort:
        # return a list of package ids
        data_dict['fl'] = 'id'

        query = query_for(model.Package)
        query.run(data_dict)

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

            result_dict = package_dictize(pkg,context)
            results.append(result_dict)

        count = query.count
        facets = query.facets
    else:
        count = 0
        facets = {}
        results = []

    search_results = {
        'count': count,
        'facets': facets,
        'results': results
    }

    # check if some extension needs to modify the search results
    for item in PluginImplementations(IPackageController):
        search_results = item.after_search(search_results,data_dict)

    return search_results

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
        escaped_term = misc.escape_sql_like_special_characters(term, escape='\\')
        q = q.filter(model.Tag.name.ilike('%' + escaped_term + '%'))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    results = [r for r in q]
    return {'count': count, 'results': results}

def task_status_show(context, data_dict):
    model = context['model']
    id = data_dict.get('id')

    if id:
        task_status = model.TaskStatus.get(id)
    else:
        query = model.Session.query(model.TaskStatus)\
            .filter(and_(
                model.TaskStatus.entity_id == data_dict['entity_id'],
                model.TaskStatus.task_type == data_dict['task_type'],
                model.TaskStatus.key == data_dict['key']
            ))
        task_status = query.first()

    context['task_status'] = task_status

    if task_status is None:
        raise NotFound

    check_access('task_status_show', context, data_dict)

    task_status_dict = task_status_dictize(task_status, context)
    return task_status_dict

def get_site_user(context, data_dict):
    check_access('get_site_user', context, data_dict)
    model = context['model']
    site_id = config.get('ckan.site_id', 'ckan_site_user')
    user = model.User.get(site_id)
    if not user:
        apikey = str(uuid.uuid4())
        user = model.User(name=site_id,
                          password=apikey,
                          apikey=apikey)
        model.add_user_to_role(user, model.Role.ADMIN, model.System())
        model.Session.add(user)
        model.Session.flush()
        if not context.get('defer_commit'):
            model.Session.commit()
    return {'name': user.name,
            'apikey': user.apikey}

def roles_show(context, data_dict):
    '''Returns the roles that users (and authorization groups) have on a
    particular domain_object.
    
    If you specify a user (or authorization group) then the resulting roles
    will be filtered by those of that user (or authorization group).

    domain_object can be a package/group/authorization_group name or id.
    '''
    model = context['model']
    session = context['session']
    domain_object_ref = data_dict['domain_object']
    user_ref = data_dict.get('user')
    authgroup_ref = data_dict.get('authorization_group')

    domain_object = get_domain_object(model, domain_object_ref)
    if isinstance(domain_object, model.Package):
        query = session.query(model.PackageRole).join('package')
    elif isinstance(domain_object, model.Group):
        query = session.query(model.GroupRole).join('group')
    elif isinstance(domain_object, model.AuthorizationGroup):
        query = session.query(model.AuthorizationGroupRole).join('authorization_group')
    else:
        raise NotFound(_('Cannot list entity of this type: %s') % type(domain_object).__name__)
    # Filter by the domain_obj
    query = query.filter_by(id=domain_object.id)

    # Filter by the user / authorized_group
    if user_ref:
        user = model.User.get(user_ref)
        if not user:
            raise NotFound(_('unknown user:') + repr(user_ref))
        query = query.join('user').filter_by(id=user.id)
    if authgroup_ref:
        authgroup = model.AuthorizationGroup.get(authgroup_ref)
        if not authgroup:
            raise NotFound('unknown authorization group:' + repr(authgroup_ref))
        # we need an alias as we join to model.AuthorizationGroup table twice
        ag = aliased(model.AuthorizationGroup)
        query = query.join(ag, model.AuthorizationGroupRole.authorized_group) \
                .filter_by(id=authgroup.id)

    uors = query.all()

    uors_dictized = [table_dictize(uor, context) for uor in uors]

    result = {'domain_object_type': type(domain_object).__name__,
              'domain_object_id': domain_object.id,
              'roles': uors_dictized}
    if user_ref:
        result['user'] = user.id
    if authgroup_ref:
        result['authorization_group'] = authgroup.id

    return result

def status_show(context, data_dict):
    '''Provides information about the operation of this CKAN instance.'''
    return {
        'site_title': config.get('ckan.site_title'),
        'site_description': config.get('ckan.site_description'),
        'site_url': config.get('ckan.site_url'),
        'ckan_version': ckan.__version__,
        'error_emails_to': config.get('email_to'),
        'locale_default': config.get('ckan.locale_default'),
        'extensions': config.get('ckan.plugins').split(),
        }

def user_activity_list(context, data_dict):
    '''Return a user\'s public activity stream as a list of dicts.'''
    model = context['model']
    user_id = data_dict['id']
    query = model.Session.query(model.Activity)
    query = query.filter_by(user_id=user_id)
    query = query.order_by(desc(model.Activity.timestamp))
    query = query.limit(15)
    activity_objects = query.all()
    return activity_list_dictize(activity_objects, context)

def package_activity_list(context, data_dict):
    '''Return a package\'s public activity stream as a list of dicts.'''
    model = context['model']
    package_id = data_dict['id']
    query = model.Session.query(model.Activity)
    query = query.filter_by(object_id=package_id)
    query = query.order_by(desc(model.Activity.timestamp))
    query = query.limit(15)
    activity_objects = query.all()
    return activity_list_dictize(activity_objects, context)

def group_activity_list(context, data_dict):
    '''Return a group\'s public activity stream as a list of dicts.'''
    model = context['model']
    group_id = data_dict['id']
    query = model.Session.query(model.Activity)
    query = query.filter_by(object_id=group_id)
    query = query.order_by(desc(model.Activity.timestamp))
    query = query.limit(15)
    activity_objects = query.all()
    return activity_list_dictize(activity_objects, context)

def activity_detail_list(context, data_dict):
    '''Return an activity\'s list of activity detail items, as a list of dicts.
    '''
    model = context['model']
    activity_id = data_dict['id']
    activity_detail_objects = model.Session.query(
        model.activity.ActivityDetail).filter_by(activity_id=activity_id).all()
    return activity_detail_list_dictize(activity_detail_objects, context)

def render_new_package_activity(context, activity):
    return render('activity_streams/new_package.html',
        extra_vars = {'activity': activity})

def render_deleted_package_activity(context, activity):
    return render('activity_streams/deleted_package.html',
        extra_vars = {'activity': activity})

def render_new_resource_activity(context, activity, detail):
    return render('activity_streams/new_resource.html',
        extra_vars = {'activity': activity, 'detail': detail})

def render_changed_resource_activity(context, activity, detail):
    return render('activity_streams/changed_resource.html',
        extra_vars = {'activity': activity, 'detail': detail})

def render_deleted_resource_activity(context, activity, detail):
    return render('activity_streams/deleted_resource.html',
        extra_vars = {'activity': activity, 'detail': detail})

def render_added_tag_activity(context, activity, detail):
    return render('activity_streams/added_tag.html',
            extra_vars = {'activity': activity, 'detail': detail})

def render_removed_tag_activity(context, activity, detail):
    return render('activity_streams/removed_tag.html',
            extra_vars = {'activity': activity, 'detail': detail})

def render_new_package_extra_activity(context, activity, detail):
    return render('activity_streams/new_package_extra.html',
        extra_vars = {'activity': activity, 'detail': detail})

def render_changed_package_extra_activity(context, activity, detail):
    return render('activity_streams/changed_package_extra.html',
        extra_vars = {'activity': activity, 'detail': detail})

def render_deleted_package_extra_activity(context, activity, detail):
    return render('activity_streams/deleted_package_extra.html',
        extra_vars = {'activity': activity, 'detail': detail})

def render_changed_package_activity(context, activity):
    details = activity_detail_list(context=context,
        data_dict={'id': activity['id']})

    if len(details) == 1:
        # If an activity has only one activity detail we try to find an
        # activity detail renderer to use instead of rendering the normal
        # 'changed package' template.
        detail = details[0]
        activity_detail_renderers = {
            'Resource': {
              'new': render_new_resource_activity,
              'changed': render_changed_resource_activity,
              'deleted': render_deleted_resource_activity
              },
            'tag': {
              'added': render_added_tag_activity,
              'removed': render_removed_tag_activity,
              },
            'PackageExtra': {
                'new': render_new_package_extra_activity,
                'changed': render_changed_package_extra_activity,
                'deleted': render_deleted_package_extra_activity
              },
            }
        object_type = detail['object_type']
        if activity_detail_renderers.has_key(object_type):
            activity_type = detail['activity_type']
            if activity_detail_renderers[object_type].has_key(activity_type):
                renderer = activity_detail_renderers[object_type][activity_type]
                return renderer(context, activity, detail)

    return render('activity_streams/changed_package.html',
        extra_vars = {'activity': activity})

def render_new_user_activity(context, activity):
    return render('activity_streams/new_user.html',
        extra_vars = {'activity': activity})

def render_changed_user_activity(context, activity):
    return render('activity_streams/changed_user.html',
        extra_vars = {'activity': activity})

def render_new_group_activity(context, activity):
    return render('activity_streams/new_group.html',
        extra_vars = {'activity': activity})

def render_changed_group_activity(context, activity):
    return render('activity_streams/changed_group.html',
        extra_vars = {'activity': activity})

def render_deleted_group_activity(context, activity):
    return render('activity_streams/deleted_group.html',
        extra_vars = {'activity': activity})

# Global dictionary mapping activity types to functions that render activity
# dicts to HTML snippets for including in HTML pages.
activity_renderers = {
  'new package' : render_new_package_activity,
  'changed package' : render_changed_package_activity,
  'deleted package' : render_deleted_package_activity,
  'new user' : render_new_user_activity,
  'changed user' : render_changed_user_activity,
  'new group' : render_new_group_activity,
  'changed group' : render_changed_group_activity,
  'deleted group' : render_deleted_group_activity,
  }

def _activity_list_to_html(context, activity_stream):
    html = []
    for activity in activity_stream:
        activity_type = activity['activity_type']
        if not activity_renderers.has_key(activity_type):
            raise NotImplementedError, ("No activity renderer for activity "
                "type '%s'" % str(activity_type))
        activity_html = activity_renderers[activity_type](context, activity)
        html.append(activity_html)
    return literal('\n'.join(html))

def user_activity_list_html(context, data_dict):
    '''Return an HTML rendering of a user\'s public activity stream.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page.

    '''
    activity_stream = user_activity_list(context, data_dict)
    return _activity_list_to_html(context, activity_stream)

def package_activity_list_html(context, data_dict):
    '''Return an HTML rendering of a package\'s public activity stream.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page.

    '''
    activity_stream = package_activity_list(context, data_dict)
    return _activity_list_to_html(context, activity_stream)

def group_activity_list_html(context, data_dict):
    '''Return an HTML rendering of a group\'s public activity stream.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page.

    '''
    activity_stream = group_activity_list(context, data_dict)
    return _activity_list_to_html(context, activity_stream)
