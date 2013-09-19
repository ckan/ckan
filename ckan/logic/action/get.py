'''API functions for searching for and getting data from CKAN.'''

import uuid
import logging
import json
import datetime
import socket

from pylons import config
import sqlalchemy

import ckan.lib.dictization
import ckan.logic as logic
import ckan.logic.action
import ckan.logic.schema
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.navl.dictization_functions
import ckan.model.misc as misc
import ckan.plugins as plugins
import ckan.lib.search as search
import ckan.lib.plugins as lib_plugins
import ckan.lib.activity_streams as activity_streams
import ckan.new_authz as new_authz

from ckan.common import _

log = logging.getLogger('ckan.logic')

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_validate = ckan.lib.navl.dictization_functions.validate
_table_dictize = ckan.lib.dictization.table_dictize
_check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust

_select = sqlalchemy.sql.select
_aliased = sqlalchemy.orm.aliased
_or_ = sqlalchemy.or_
_and_ = sqlalchemy.and_
_func = sqlalchemy.func
_desc = sqlalchemy.desc
_case = sqlalchemy.case
_text = sqlalchemy.text

def _package_list_with_resources(context, package_revision_list):
    package_list = []
    for package in package_revision_list:
        result_dict = model_dictize.package_dictize(package,context)
        package_list.append(result_dict)
    return package_list


def site_read(context,data_dict=None):
    '''Return ``True``.

    :rtype: boolean

    '''
    _check_access('site_read',context,data_dict)
    return True

def package_list(context, data_dict):
    '''Return a list of the names of the site's datasets (packages).

    :param limit: if given, the list of datasets will be broken into pages of
        at most ``limit`` datasets per page and only one page will be returned
        at a time (optional)
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning packages from
    :type offset: int

    :rtype: list of strings

    '''
    model = context["model"]
    api = context.get("api_version", 1)

    _check_access('package_list', context, data_dict)

    schema = context.get('schema', logic.schema.default_pagination_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)


    package_revision_table = model.package_revision_table
    col = (package_revision_table.c.id
        if api == 2 else package_revision_table.c.name)
    query = _select([col])
    query = query.where(_and_(package_revision_table.c.state=='active',
        package_revision_table.c.current==True))
    query = query.order_by(col)

    limit = data_dict.get('limit')
    if limit:
        query = query.limit(limit)

    offset = data_dict.get('offset')
    if offset:
        query = query.offset(offset)
    return list(zip(*query.execute())[0])

def current_package_list_with_resources(context, data_dict):
    '''Return a list of the site's datasets (packages) and their resources.

    The list is sorted most-recently-modified first.

    :param limit: if given, the list of datasets will be broken into pages of
        at most ``limit`` datasets per page and only one page will be returned
        at a time (optional)
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning packages from
    :type offset: int
    :param page: when ``limit`` is given, which page to return, Deprecated use ``offset``
    :type page: int

    :rtype: list of dictionaries

    '''
    model = context["model"]
    schema = context.get('schema', logic.schema.default_package_list_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    limit = data_dict.get('limit')
    offset = int(data_dict.get('offset', 0))

    if not 'offset' in data_dict and 'page' in data_dict:
        log.warning('"page" parameter is deprecated.  '
                    'Use the "offset" parameter instead')
        page = int(data_dict['page'])
        if page < 1:
            raise ValidationError(_('Must be larger than 0'))
        if limit:
            offset = (page - 1) * limit
        else:
            offset = 0

    _check_access('current_package_list_with_resources', context, data_dict)

    query = model.Session.query(model.PackageRevision)
    query = query.filter(model.PackageRevision.state=='active')
    query = query.filter(model.PackageRevision.current==True)

    query = query.order_by(model.package_revision_table.c.revision_timestamp.desc())
    if limit is not None:
        query = query.limit(limit)
    query = query.offset(offset)
    pack_rev = query.all()
    return _package_list_with_resources(context, pack_rev)

def revision_list(context, data_dict):
    '''Return a list of the IDs of the site's revisions.

    :rtype: list of strings

    '''
    model = context['model']

    _check_access('revision_list', context, data_dict)

    revs = model.Session.query(model.Revision).all()
    return [rev.id for rev in revs]

def package_revision_list(context, data_dict):
    '''Return a dataset (package)'s revisions as a list of dictionaries.

    :param id: the id or name of the dataset
    :type id: string

    '''
    model = context["model"]
    id = _get_or_bust(data_dict, "id")
    pkg = model.Package.get(id)
    if pkg is None:
        raise NotFound

    _check_access('package_revision_list',context, data_dict)

    revision_dicts = []
    for revision, object_revisions in pkg.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False,
                                                     include_groups=False))
    return revision_dicts


def related_show(context, data_dict=None):
    '''Return a single related item.

    :param id: the id of the related item to show
    :type id: string

    :rtype: dictionary

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    related = model.Related.get(id)
    context['related'] = related

    if related is None:
        raise NotFound

    _check_access('related_show',context, data_dict)

    schema = context.get('schema') or ckan.logic.schema.default_related_schema()
    related_dict = model_dictize.related_dictize(related, context)
    related_dict, errors = _validate(related_dict, schema, context=context)

    return related_dict


def related_list(context, data_dict=None):
    '''Return a dataset's related items.

    Either the ``id`` or the ``dataset`` parameter must be given.

    :param id: id or name of the dataset (optional)
    :type id: string
    :param dataset: dataset dictionary of the dataset (optional)
    :type dataset: dictionary
    :param type_filter: the type of related item to show (optional,
      default: None, show all items)
    :type type_filter: string
    :param sort: the order to sort the related items in, possible values are
      'view_count_asc', 'view_count_desc', 'created_asc' or 'created_desc'
      (optional)
    :type sort: string
    :param featured: whether or not to restrict the results to only featured
      related items (optional, default: False)
    :type featured: bool

    :rtype: list of dictionaries

    '''
    model = context['model']
    dataset = data_dict.get('dataset', None)

    if not dataset:
        dataset = model.Package.get(data_dict.get('id'))

    _check_access('related_show',context, data_dict)

    related_list = []
    if not dataset:
        related_list = model.Session.query(model.Related)

        filter_on_type = data_dict.get('type_filter', None)
        if filter_on_type:
            related_list = related_list.filter(model.Related.type == filter_on_type)

        sort = data_dict.get('sort', None)
        if sort:
            sortables = {
                'view_count_asc' : model.Related.view_count.asc,
                'view_count_desc': model.Related.view_count.desc,
                'created_asc' : model.Related.created.asc,
                'created_desc': model.Related.created.desc,
            }
            s = sortables.get(sort, None)
            if s:
                related_list = related_list.order_by( s() )

        if data_dict.get('featured', False):
            related_list = related_list.filter(model.Related.featured == 1)
    else:
        relateds = model.Related.get_for_dataset(dataset, status='active')
        related_items = (r.related for r in relateds)
        related_list = model_dictize.related_list_dictize( related_items, context)
    return related_list


def member_list(context, data_dict=None):
    '''Return the members of a group.

    The user must have permission to 'get' the group.

    :param id: the id or name of the group
    :type id: string
    :param object_type: restrict the members returned to those of a given type,
      e.g. ``'user'`` or ``'package'`` (optional, default: ``None``)
    :type object_type: string
    :param capacity: restrict the members returned to those with a given
      capacity, e.g. ``'member'``, ``'editor'``, ``'admin'``, ``'public'``,
      ``'private'`` (optional, default: ``None``)
    :type capacity: string

    :rtype: list of (id, type, capacity) tuples

    :raises: :class:`ckan.logic.NotFound`: if the group doesn't exist

    '''
    model = context['model']

    group = model.Group.get(_get_or_bust(data_dict, 'id'))
    if not group:
        raise NotFound

    obj_type = data_dict.get('object_type', None)
    capacity = data_dict.get('capacity', None)

    # User must be able to update the group to remove a member from it
    _check_access('group_show', context, data_dict)

    q = model.Session.query(model.Member).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == "active")

    if obj_type:
        q = q.filter(model.Member.table_name == obj_type)
    if capacity:
        q = q.filter(model.Member.capacity == capacity)

    trans = new_authz.roles_trans()

    def translated_capacity(capacity):
        try:
            return trans[capacity]
        except KeyError:
            return capacity

    return [(m.table_id, m.table_name, translated_capacity(m.capacity))
            for m in q.all()]

def _group_or_org_list(context, data_dict, is_org=False):

    model = context['model']
    api = context.get('api_version')
    groups = data_dict.get('groups')
    ref_group_by = 'id' if api == 2 else 'name'

    sort = data_dict.get('sort', 'name')
    q = data_dict.get('q')

    # order_by deprecated in ckan 1.8
    # if it is supplied and sort isn't use order_by and raise a warning
    order_by = data_dict.get('order_by', '')
    if order_by:
        log.warn('`order_by` deprecated please use `sort`')
        if not data_dict.get('sort'):
            sort = order_by
    # if the sort is packages and no sort direction is supplied we want to do a
    # reverse sort to maintain compatibility.
    if sort.strip() == 'packages':
        sort = 'packages desc'

    sort_info = _unpick_search(sort,
                               allowed_fields=['name', 'packages'],
                               total=1)

    all_fields = data_dict.get('all_fields', None)


    query = model.Session.query(model.Group).join(model.GroupRevision)
    query = query.filter(model.GroupRevision.state=='active')
    query = query.filter(model.GroupRevision.current==True)
    if groups:
        query = query.filter(model.GroupRevision.name.in_(groups))
    if q:
        q = u'%{0}%'.format(q)
        query = query.filter(_or_(
            model.GroupRevision.name.ilike(q),
            model.GroupRevision.title.ilike(q),
            model.GroupRevision.description.ilike(q),
        ))


    query = query.filter(model.GroupRevision.is_organization==is_org)

    groups = query.all()
    group_list = model_dictize.group_list_dictize(groups, context,
                                                  lambda x:x[sort_info[0][0]],
                                                  sort_info[0][1] == 'desc')

    if not all_fields:
        group_list = [group[ref_group_by] for group in group_list]

    return group_list


def group_list(context, data_dict):
    '''Return a list of the names of the site's groups.

    :param order_by: the field to sort the list by, must be ``'name'`` or
      ``'packages'`` (optional, default: ``'name'``) Deprecated use sort.
    :type order_by: string
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name' and 'packages'
    :type sort: string
    :param groups: a list of names of the groups to return, if given only
        groups whose names are in this list will be returned (optional)
    :type groups: list of strings
    :param all_fields: return full group dictionaries instead of  just names
        (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings

    '''
    _check_access('group_list', context, data_dict)
    data_dict['type'] = 'group'
    return _group_or_org_list(context, data_dict)


def organization_list(context, data_dict):
    '''Return a list of the names of the site's organizations.

    :param order_by: the field to sort the list by, must be ``'name'`` or
      ``'packages'`` (optional, default: ``'name'``) Deprecated use sort.
    :type order_by: string
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name' and 'packages'
    :type sort: string
    :param organizations: a list of names of the groups to return, if given only
        groups whose names are in this list will be returned (optional)
    :type organizations: list of strings
    :param all_fields: return full group dictionaries instead of  just names
        (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of strings

    '''
    _check_access('organization_list', context, data_dict)
    data_dict['groups'] = data_dict.pop('organizations', [])
    data_dict['type'] = 'organization'
    return _group_or_org_list(context, data_dict, is_org=True)


def group_list_authz(context, data_dict):
    '''Return the list of groups that the user is authorized to edit.

    :param available_only: remove the existing groups in the package
      (optional, default: ``False``)
    :type available_only: boolean

    :param am_member: if True return only the groups the logged-in user is a
      member of, otherwise return all groups that the user is authorized to
      edit (for example, sysadmin users are authorized to edit all groups)
      (optional, default: False)
    :type am-member: boolean

    :returns: list of dictized groups that the user is authorized to edit
    :rtype: list of dicts

    '''
    model = context['model']
    user = context['user']
    available_only = data_dict.get('available_only', False)
    am_member = data_dict.get('am_member', False)

    _check_access('group_list_authz',context, data_dict)

    sysadmin = new_authz.is_sysadmin(user)
    roles = ckan.new_authz.get_roles_with_permission('edit_group')
    if not roles:
        return []
    user_id = new_authz.get_user_id_for_username(user, allow_none=True)
    if not user_id:
        return []

    if not sysadmin or am_member:
        q = model.Session.query(model.Member) \
            .filter(model.Member.table_name == 'user') \
            .filter(model.Member.capacity.in_(roles)) \
            .filter(model.Member.table_id == user_id)
        group_ids = []
        for row in q.all():
            group_ids.append(row.group_id)

        if not group_ids:
            return []

    q = model.Session.query(model.Group) \
        .filter(model.Group.is_organization == False) \
        .filter(model.Group.state == 'active')

    if not sysadmin or am_member:
        q = q.filter(model.Group.id.in_(group_ids))

    groups = q.all()

    if available_only:
        package = context.get('package')
        if package:
            groups = set(groups) - set(package.get_groups())

    group_list = model_dictize.group_list_dictize(groups, context)
    return group_list

def organization_list_for_user(context, data_dict):
    '''Return the list of organizations that the user is a member of.

    :param permission: the permission the user has against the returned organizations
      (optional, default: ``edit_group``)
    :type permission: string

    :returns: list of dictized organizations that the user is authorized to edit
    :rtype: list of dicts

    '''
    model = context['model']
    user = context['user']

    _check_access('organization_list_for_user',context, data_dict)
    sysadmin = new_authz.is_sysadmin(user)

    orgs_q = model.Session.query(model.Group) \
        .filter(model.Group.is_organization == True) \
        .filter(model.Group.state == 'active')

    if not sysadmin:
        # for non-Sysadmins check they have the required permission

        permission = data_dict.get('permission', 'edit_group')

        roles = ckan.new_authz.get_roles_with_permission(permission)

        if not roles:
            return []
        user_id = new_authz.get_user_id_for_username(user, allow_none=True)
        if not user_id:
            return []

        q = model.Session.query(model.Member) \
            .filter(model.Member.table_name == 'user') \
            .filter(model.Member.capacity.in_(roles)) \
            .filter(model.Member.table_id == user_id)

        group_ids = []
        for row in q.all():
            group_ids.append(row.group_id)

        if not group_ids:
            return []

        orgs_q = orgs_q.filter(model.Group.id.in_(group_ids))

    orgs_list = model_dictize.group_list_dictize(orgs_q.all(), context)
    return orgs_list

def group_revision_list(context, data_dict):
    '''Return a group's revisions.

    :param id: the name or id of the group
    :type id: string

    :rtype: list of dictionaries

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')
    group = model.Group.get(id)
    if group is None:
        raise NotFound

    _check_access('group_revision_list',context, data_dict)

    revision_dicts = []
    for revision, object_revisions in group.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False,
                                                     include_groups=False))
    return revision_dicts

def license_list(context, data_dict):
    '''Return the list of licenses available for datasets on the site.

    :rtype: list of dictionaries

    '''
    model = context["model"]

    _check_access('license_list',context, data_dict)

    license_register = model.Package.get_license_register()
    licenses = license_register.values()
    licenses = [l.as_dict() for l in licenses]
    return licenses

def tag_list(context, data_dict):
    '''Return a list of the site's tags.

    By default only free tags (tags that don't belong to a vocabulary) are
    returned. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be returned instead.

    :param query: a tag name query to search for, if given only tags whose
        names contain this string will be returned (optional)
    :type query: string
    :param vocabulary_id: the id or name of a vocabulary, if give only tags
        that belong to this vocabulary will be returned (optional)
    :type vocabulary_id: string
    :param all_fields: return full tag dictionaries instead of just names
        (optional, default: ``False``)
    :type all_fields: boolean

    :rtype: list of dictionaries

    '''
    model = context['model']

    vocab_id_or_name = data_dict.get('vocabulary_id')
    query = data_dict.get('query') or data_dict.get('q')
    if query:
        query = query.strip()
    all_fields = data_dict.get('all_fields', None)

    _check_access('tag_list', context, data_dict)

    if query:
        tags, count = _tag_search(context, data_dict)
    else:
        tags = model.Tag.all(vocab_id_or_name)

    if tags:
        if all_fields:
            tag_list = model_dictize.tag_list_dictize(tags, context)
        else:
            tag_list = [tag.name for tag in tags]
    else:
        tag_list = []

    return tag_list

def user_list(context, data_dict):
    '''Return a list of the site's user accounts.

    :param q: restrict the users returned to those whose names contain a string
      (optional)
    :type q: string
    :param order_by: which field to sort the list by (optional, default:
      ``'name'``)
    :type order_by: string

    :rtype: list of dictionaries

    '''
    model = context['model']

    _check_access('user_list',context, data_dict)

    q = data_dict.get('q','')
    order_by = data_dict.get('order_by','name')

    query = model.Session.query(
        model.User,
        model.User.name.label('name'),
        model.User.fullname.label('fullname'),
        model.User.about.label('about'),
        model.User.about.label('email'),
        model.User.created.label('created'),
        _select([_func.count(model.Revision.id)], _or_(
                model.Revision.author==model.User.name,
                model.Revision.author==model.User.openid
                )
        ).label('number_of_edits'),
        _select([_func.count(model.UserObjectRole.id)], _and_(
            model.UserObjectRole.user_id==model.User.id,
            model.UserObjectRole.context=='Package',
            model.UserObjectRole.role=='admin'
            )
        ).label('number_administered_packages')
    )

    if q:
        query = model.User.search(q, query, user_name=context.get('user'))

    if order_by == 'edits':
        query = query.order_by(_desc(
            _select([_func.count(model.Revision.id)], _or_(
                model.Revision.author==model.User.name,
                model.Revision.author==model.User.openid
                ))
        ))
    else:
        query = query.order_by(
            _case([(_or_(model.User.fullname == None, model.User.fullname == ''),
                   model.User.name)],
                 else_=model.User.fullname)
        )

    ## hack for pagination
    if context.get('return_query'):
        return query

    users_list = []

    for user in query.all():
        result_dict = model_dictize.user_dictize(user[0], context)
        users_list.append(result_dict)

    return users_list

def package_relationships_list(context, data_dict):
    '''Return a dataset (package)'s relationships.

    :param id: the id or name of the first package
    :type id: string
    :param id2: the id or name of the second package
    :type id: string
    :param rel: relationship as string see
        :func:`ckan.logic.action.create.package_relationship_create()` for the
        relationship types (optional)

    :rtype: list of dictionaries

    '''
    ##TODO needs to work with dictization layer
    model = context['model']
    api = context.get('api_version')

    id = _get_or_bust(data_dict, "id")
    id2 = data_dict.get("id2")
    rel = data_dict.get("rel")
    ref_package_by = 'id' if api == 2 else 'name'
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

    _check_access('package_relationships_list',context, data_dict)

    # TODO: How to handle this object level authz?
    # Currently we don't care
    relationships = pkg1.get_relationships(with_package=pkg2, type=rel)

    if rel and not relationships:
        raise NotFound('Relationship "%s %s %s" not found.'
                                 % (id, rel, id2))

    relationship_dicts = [rel.as_dict(pkg1, ref_package_by=ref_package_by)
                          for rel in relationships]

    return relationship_dicts

def package_show(context, data_dict):
    '''Return the metadata of a dataset (package) and its resources.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: dictionary

    '''
    model = context['model']
    context['session'] = model.Session
    name_or_id = data_dict.get("id") or _get_or_bust(data_dict, 'name_or_id')

    pkg = model.Package.get(name_or_id)

    if pkg is None:
        raise NotFound

    context['package'] = pkg

    _check_access('package_show', context, data_dict)

    package_dict = None
    use_cache = (context.get('use_cache', True)
        and not 'revision_id' in context
        and not 'revision_date' in context)
    if use_cache:
        try:
            search_result = search.show(name_or_id)
        except (search.SearchError, socket.error):
            pass
        else:
            use_validated_cache = 'schema' not in context
            if use_validated_cache and 'validated_data_dict' in search_result:
                package_dict = json.loads(search_result['validated_data_dict'])
                package_dict_validated = True
            else:
                package_dict = json.loads(search_result['data_dict'])
                package_dict_validated = False
            metadata_modified = pkg.metadata_modified.isoformat()
            search_metadata_modified = search_result['metadata_modified']
            # solr stores less precice datetime,
            # truncate to 22 charactors to get good enough match
            if metadata_modified[:22] != search_metadata_modified[:22]:
                package_dict = None

    if not package_dict:
        package_dict = model_dictize.package_dictize(pkg, context)
        package_dict_validated = False

    # Add page-view tracking summary data to the package dict.
    # If the package_dict came from the Solr cache then it will already have a
    # potentially outdated tracking_summary, this will overwrite it with a
    # current one.
    package_dict['tracking_summary'] = model.TrackingSummary.get_for_package(
        package_dict['id'])

    # Add page-view tracking summary data to the package's resource dicts.
    # If the package_dict came from the Solr cache then each resource dict will
    # already have a potentially outdated tracking_summary, this will overwrite
    # it with a current one.
    for resource_dict in package_dict['resources']:
        _add_tracking_summary_to_resource_dict(resource_dict, model)

    if context.get('for_view'):
        for item in plugins.PluginImplementations(plugins.IPackageController):
            package_dict = item.before_view(package_dict)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.read(pkg)

    for resource_dict in package_dict['resources']:
        for item in plugins.PluginImplementations(plugins.IResourceController):
            resource_dict = item.before_show(resource_dict)

    if not package_dict_validated:
        package_plugin = lib_plugins.lookup_package_plugin(package_dict['type'])
        if 'schema' in context:
            schema = context['schema']
        else:
            schema = package_plugin.show_package_schema()
            if schema and context.get('validate', True):
                package_dict, errors = _validate(package_dict, schema,
                    context=context)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.after_show(context, package_dict)

    return package_dict


def _add_tracking_summary_to_resource_dict(resource_dict, model):
    '''Add page-view tracking summary data to the given resource dict.

    '''
    tracking_summary = model.TrackingSummary.get_for_resource(
        resource_dict['url'])
    resource_dict['tracking_summary'] = tracking_summary


def resource_show(context, data_dict):
    '''Return the metadata of a resource.

    :param id: the id of the resource
    :type id: string

    :rtype: dictionary

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    resource = model.Resource.get(id)
    context['resource'] = resource

    if not resource:
        raise NotFound

    _check_access('resource_show', context, data_dict)
    resource_dict = model_dictize.resource_dictize(resource, context)

    _add_tracking_summary_to_resource_dict(resource_dict, model)

    for item in plugins.PluginImplementations(plugins.IResourceController):
        resource_dict = item.before_show(resource_dict)

    return resource_dict

def resource_status_show(context, data_dict):
    '''Return the statuses of a resource's tasks.

    :param id: the id of the resource
    :type id: string

    :rtype: list of (status, date_done, traceback, task_status) dictionaries

    '''
    try:
        import ckan.lib.celery_app as celery_app
    except ImportError:
        return {'message': 'queue is not installed on this instance'}

    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    _check_access('resource_status_show', context, data_dict)

    # needs to be text query as celery tables are not in our model
    q = _text("""select status, date_done, traceback, task_status.*
                from task_status left join celery_taskmeta
                on task_status.value = celery_taskmeta.task_id and key = 'celery_task_id'
                where entity_id = :entity_id """)

    result = model.Session.connection().execute(q, entity_id=id)
    result_list = [_table_dictize(row, context) for row in result]

    return result_list


@logic.auth_audit_exempt
def revision_show(context, data_dict):
    '''Return the details of a revision.

    :param id: the id of the revision
    :type id: string

    :rtype: dictionary

    '''
    model = context['model']
    api = context.get('api_version')
    id = _get_or_bust(data_dict, 'id')
    ref_package_by = 'id' if api == 2 else 'name'

    rev = model.Session.query(model.Revision).get(id)
    if rev is None:
        raise NotFound
    rev_dict = model.revision_as_dict(rev, include_packages=True,
                                      ref_package_by=ref_package_by)
    return rev_dict

def _group_or_org_show(context, data_dict, is_org=False):
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    group = model.Group.get(id)
    context['group'] = group

    if group is None:
        raise NotFound
    if is_org and not group.is_organization:
        raise NotFound
    if not is_org and group.is_organization:
        raise NotFound

    if is_org:
        _check_access('organization_show',context, data_dict)
    else:
        _check_access('group_show',context, data_dict)


    group_dict = model_dictize.group_dictize(group, context)

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.read(group)

    group_plugin = lib_plugins.lookup_group_plugin(group_dict['type'])
    try:
        schema = group_plugin.db_to_form_schema_options({
            'type':'show',
            'api': 'api_version' in context,
            'context': context })
    except AttributeError:
        schema = group_plugin.db_to_form_schema()

    group_dict['num_followers'] = logic.get_action('group_follower_count')(
            {'model': model, 'session': model.Session},
            {'id': group_dict['id']})

    if schema:
        group_dict, errors = _validate(group_dict, schema, context=context)
    return group_dict


def group_show(context, data_dict):
    '''Return the details of a group.

    :param id: the id or name of the group
    :type id: string

    :rtype: dictionary

    '''
    return _group_or_org_show(context, data_dict)

def organization_show(context, data_dict):
    '''Return the details of a organization.

    :param id: the id or name of the organization
    :type id: string

    :rtype: dictionary

    '''
    return _group_or_org_show(context, data_dict, is_org=True)


def group_package_show(context, data_dict):
    '''Return the datasets (packages) of a group.

    :param id: the id or name of the group
    :type id: string
    :param limit: the maximum number of datasets to return (optional)
    :type limit: int

    :rtype: list of dictionaries

    '''
    model = context['model']
    group_id = _get_or_bust(data_dict, 'id')

    # FIXME: What if limit is not an int? Schema and validation needed.
    limit = data_dict.get('limit')

    group = model.Group.get(group_id)
    context['group'] = group
    if group is None:
        raise NotFound

    _check_access('group_show', context, data_dict)

    result = []
    for pkg_rev in group.packages(limit=limit,
            return_query=context.get('return_query')):
        result.append(model_dictize.package_dictize(pkg_rev, context))

    return result

def tag_show(context, data_dict):
    '''Return the details of a tag and all its datasets.

    :param id: the name or id of the tag
    :type id: string

    :returns: the details of the tag, including a list of all of the tag's
        datasets and their details
    :rtype: dictionary

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    tag = model.Tag.get(id)
    context['tag'] = tag

    if tag is None:
        raise NotFound

    _check_access('tag_show',context, data_dict)

    return model_dictize.tag_dictize(tag,context)

def user_show(context, data_dict):
    '''Return a user account.

    Either the ``id`` or the ``user_obj`` parameter must be given.

    :param id: the id or name of the user (optional)
    :type id: string
    :param user_obj: the user dictionary of the user (optional)
    :type user_obj: user dictionary

    :rtype: dictionary

    '''
    model = context['model']

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

    _check_access('user_show',context, data_dict)

    user_dict = model_dictize.user_dictize(user_obj,context)

    if context.get('return_minimal'):
        return user_dict

    revisions_q = model.Session.query(model.Revision
            ).filter_by(author=user_obj.name)

    revisions_list = []
    for revision in revisions_q.limit(20).all():
        revision_dict = logic.get_action('revision_show')(context,{'id':revision.id})
        revision_dict['state'] = revision.state
        revisions_list.append(revision_dict)
    user_dict['activity'] = revisions_list

    user_dict['datasets'] = []
    dataset_q = model.Session.query(model.Package).join(model.PackageRole
            ).filter_by(user=user_obj, role=model.Role.ADMIN
            ).limit(50)

    for dataset in dataset_q:
        try:
            dataset_dict = logic.get_action('package_show')(context, {'id': dataset.id})
        except logic.NotAuthorized:
            continue
        user_dict['datasets'].append(dataset_dict)

    user_dict['num_followers'] = logic.get_action('user_follower_count')(
            {'model': model, 'session': model.Session},
            {'id': user_dict['id']})

    return user_dict

def package_show_rest(context, data_dict):
    _check_access('package_show_rest',context, data_dict)

    logic.get_action('package_show')(context, data_dict)

    pkg = context['package']

    package_dict = model_dictize.package_to_api(pkg, context)

    return package_dict

def group_show_rest(context, data_dict):
    _check_access('group_show_rest',context, data_dict)

    logic.get_action('group_show')(context, data_dict)
    group = context['group']

    group_dict = model_dictize.group_to_api(group, context)

    return group_dict

def tag_show_rest(context, data_dict):
    _check_access('tag_show_rest',context, data_dict)

    logic.get_action('tag_show')(context, data_dict)
    tag = context['tag']

    tag_dict = model_dictize.tag_to_api(tag, context)

    return tag_dict

def package_autocomplete(context, data_dict):
    '''Return a list of datasets (packages) that match a string.

    Datasets with names or titles that contain the query string will be
    returned.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of resource formats to return (optional,
        default: 10)
    :type limit: int

    :rtype: list of dictionaries

    '''
    schema = context.get('schema', logic.schema.default_autocomplete_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    model = context['model']

    _check_access('package_autocomplete', context, data_dict)

    limit = data_dict.get('limit', 10)
    q = data_dict['q']

    like_q = u"%s%%" % q

    query = model.Session.query(model.PackageRevision)
    query = query.filter(model.PackageRevision.state=='active')
    query = query.filter(model.PackageRevision.current==True)
    query = query.filter(_or_(model.PackageRevision.name.ilike(like_q),
                                model.PackageRevision.title.ilike(like_q)))
    query = query.limit(limit)

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

def format_autocomplete(context, data_dict):
    '''Return a list of resource formats whose names contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of resource formats to return (optional,
        default: 5)
    :type limit: int

    :rtype: list of strings

    '''
    schema = context.get('schema', logic.schema.default_autocomplete_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    model = context['model']
    session = context['session']

    _check_access('format_autocomplete', context, data_dict)

    q = data_dict['q']
    limit = data_dict.get('limit', 5)

    like_q = u'%' + q + u'%'

    query = session.query(model.ResourceRevision.format,
        _func.count(model.ResourceRevision.format).label('total'))\
        .filter(_and_(
            model.ResourceRevision.state == 'active',
            model.ResourceRevision.current == True
        ))\
        .filter(model.ResourceRevision.format.ilike(like_q))\
        .group_by(model.ResourceRevision.format)\
        .order_by('total DESC')\
        .limit(limit)

    return [resource.format.lower() for resource in query]

def user_autocomplete(context, data_dict):
    '''Return a list of user names that contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of user names to return (optional,
        default: 20)
    :type limit: int

    :rtype: a list of user dictionaries each with keys ``'name'``,
        ``'fullname'``, and ``'id'``

    '''
    schema = context.get('schema', logic.schema.default_autocomplete_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    model = context['model']
    user = context['user']

    _check_access('user_autocomplete', context, data_dict)

    q = data_dict['q']
    limit = data_dict.get('limit', 20)

    query = model.User.search(q).limit(limit)

    user_list = []
    for user in query.all():
        result_dict = {}
        for k in ['id', 'name', 'fullname']:
                result_dict[k] = getattr(user,k)

        user_list.append(result_dict)

    return user_list

def package_search(context, data_dict):
    '''
    Searches for packages satisfying a given search criteria.

    This action accepts solr search query parameters (details below), and
    returns a dictionary of results, including dictized datasets that match
    the search criteria, a search count and also facet information.

    **Solr Parameters:**

    For more in depth treatment of each paramter, please read the `Solr
    Documentation <http://wiki.apache.org/solr/CommonQueryParameters>`_.

    This action accepts a *subset* of solr's search query parameters:


    :param q: the solr query.  Optional.  Default: `"*:*"`
    :type q: string
    :param fq: any filter queries to apply.  Note: `+site_id:{ckan_site_id}`
        is added to this string prior to the query being executed.
    :type fq: string
    :param sort: sorting of the search results.  Optional.  Default:
        'relevance asc, metadata_modified desc'.  As per the solr
        documentation, this is a comma-separated string of field names and
        sort-orderings.
    :type sort: string
    :param rows: the number of matching rows to return.
    :type rows: int
    :param start: the offset in the complete result for where the set of
        returned datasets should begin.
    :type start: int
    :param facet: whether to enable faceted results.  Default: "true".
    :type facet: string
    :param facet.mincount: the minimum counts for facet fields should be
        included in the results.
    :type facet.mincount: int
    :param facet.limit: the maximum number of constraint counts that should be
        returned for the facet fields. A negative value means unlimited
    :type facet.limit: int
    :param facet.field: the fields to facet upon.  Default empty.  If empty,
        then the returned facet information is empty.
    :type facet.field: list of strings


    The following advanced Solr parameters are supported as well. Note that
    some of these are only available on particular Solr versions. See Solr's
    `dismax`_ and `edismax`_ documentation for further details on them:

    ``qf``, ``wt``, ``bf``, ``boost``, ``tie``, ``defType``, ``mm``


    .. _dismax: http://wiki.apache.org/solr/DisMaxQParserPlugin
    .. _edismax: http://wiki.apache.org/solr/ExtendedDisMax


    **Results:**

    The result of this action is a dict with the following keys:

    :rtype: A dictionary with the following keys
    :param count: the number of results found.  Note, this is the total number
        of results found, not the total number of results returned (which is
        affected by limit and row parameters used in the input).
    :type count: int
    :param results: ordered list of datasets matching the query, where the
        ordering defined by the sort parameter used in the query.
    :type results: list of dictized datasets.
    :param facets: DEPRECATED.  Aggregated information about facet counts.
    :type facets: DEPRECATED dict
    :param search_facets: aggregated information about facet counts.  The outer
        dict is keyed by the facet field name (as used in the search query).
        Each entry of the outer dict is itself a dict, with a "title" key, and
        an "items" key.  The "items" key's value is a list of dicts, each with
        "count", "display_name" and "name" entries.  The display_name is a
        form of the name that can be used in titles.
    :type search_facets: nested dict of dicts.

    An example result: ::

     {'count': 2,
      'results': [ { <snip> }, { <snip> }],
      'search_facets': {u'tags': {'items': [{'count': 1,
                                             'display_name': u'tolstoy',
                                             'name': u'tolstoy'},
                                            {'count': 2,
                                             'display_name': u'russian',
                                             'name': u'russian'}
                                           ]
                                 }
                       }
     }

    **Limitations:**

    The full solr query language is not exposed, including.

    fl
        The parameter that controls which fields are returned in the solr
        query cannot be changed.  CKAN always returns the matched datasets as
        dictionary objects.
    '''
    # sometimes context['schema'] is None
    schema = (context.get('schema') or
              logic.schema.default_package_search_schema())
    if isinstance(data_dict.get('facet.field'), basestring):
        data_dict['facet.field'] = json.loads(data_dict['facet.field'])
    data_dict, errors = _validate(data_dict, schema, context)
    # put the extras back into the data_dict so that the search can
    # report needless parameters
    data_dict.update(data_dict.get('__extras', {}))
    data_dict.pop('__extras', None)
    if errors:
        raise ValidationError(errors)

    model = context['model']
    session = context['session']

    _check_access('package_search', context, data_dict)

    # Move ext_ params to extras and remove them from the root of the search
    # params, so they don't cause and error
    data_dict['extras'] = data_dict.get('extras', {})
    for key in [key for key in data_dict.keys() if key.startswith('ext_')]:
        data_dict['extras'][key] = data_dict.pop(key)

    # check if some extension needs to modify the search params
    for item in plugins.PluginImplementations(plugins.IPackageController):
        data_dict = item.before_search(data_dict)

    # the extension may have decided that it is not necessary to perform
    # the query
    abort = data_dict.get('abort_search', False)

    if data_dict.get('sort') in (None, 'rank'):
        data_dict['sort'] = 'score desc, metadata_modified desc'

    if data_dict.get('sort') in (None, 'rank'):
        data_dict['sort'] = 'score desc, metadata_modified desc'

    results = []
    if not abort:
        # return a list of package ids
        data_dict['fl'] = 'id data_dict'

        # If this query hasn't come from a controller that has set this flag
        # then we should remove any mention of capacity from the fq and
        # instead set it to only retrieve public datasets
        fq = data_dict.get('fq', '')
        if not context.get('ignore_capacity_check', False):
            fq = ' '.join(p for p in fq.split(' ')
                            if not 'capacity:' in p)
            data_dict['fq'] = fq + ' capacity:"public"'

        # Pop these ones as Solr does not need them
        extras = data_dict.pop('extras', None)

        query = search.query_for(model.Package)
        query.run(data_dict)

        # Add them back so extensions can use them on after_search
        data_dict['extras'] = extras

        for package in query.results:
            # get the package object
            package, package_dict = package['id'], package.get('data_dict')
            pkg_query = session.query(model.PackageRevision)\
                .filter(model.PackageRevision.id == package)\
                .filter(_and_(
                    model.PackageRevision.state == u'active',
                    model.PackageRevision.current == True
                ))
            pkg = pkg_query.first()

            ## if the index has got a package that is not in ckan then
            ## ignore it.
            if not pkg:
                log.warning('package %s in index but not in database' % package)
                continue
            ## use data in search index if there
            if package_dict:
                ## the package_dict still needs translating when being viewed
                package_dict = json.loads(package_dict)
                if context.get('for_view'):
                    for item in plugins.PluginImplementations( plugins.IPackageController):
                        package_dict = item.before_view(package_dict)
                results.append(package_dict)
            else:
                results.append(model_dictize.package_dictize(pkg,context))

        count = query.count
        facets = query.facets
    else:
        count = 0
        facets = {}
        results = []

    search_results = {
        'count': count,
        'facets': facets,
        'results': results,
        'sort': data_dict['sort']
    }

    # Transform facets into a more useful data structure.
    restructured_facets = {}
    for key, value in facets.items():
        restructured_facets[key] = {
                'title': key,
                'items': []
                }
        for key_, value_ in value.items():
            new_facet_dict = {}
            new_facet_dict['name'] = key_
            if key in ('groups', 'organization'):
                group = model.Group.get(key_)
                if group:
                    new_facet_dict['display_name'] = group.display_name
                else:
                    new_facet_dict['display_name'] = key_
            elif key == 'license_id':
                license = model.Package.get_license_register().get(key_)
                if license:
                    new_facet_dict['display_name'] = license.title
                else:
                    new_facet_dict['display_name'] = key_
            else:
                new_facet_dict['display_name'] = key_
            new_facet_dict['count'] = value_
            restructured_facets[key]['items'].append(new_facet_dict)
    search_results['search_facets'] = restructured_facets

    # check if some extension needs to modify the search results
    for item in plugins.PluginImplementations(plugins.IPackageController):
        search_results = item.after_search(search_results,data_dict)

    # After extensions have had a chance to modify the facets, sort them by
    # display name.
    for facet in search_results['search_facets']:
        search_results['search_facets'][facet]['items'] = sorted(
                search_results['search_facets'][facet]['items'],
                key=lambda facet: facet['display_name'], reverse=True)

    return search_results

def resource_search(context, data_dict):
    '''
    Searches for resources satisfying a given search criteria.

    It returns a dictionary with 2 fields: ``count`` and ``results``.  The
    ``count`` field contains the total number of Resources found without the
    limit or query parameters having an effect.  The ``results`` field is a
    list of dictized Resource objects.

    The 'query' parameter is a required field.  It is a string of the form
    ``{field}:{term}`` or a list of strings, each of the same form.  Within
    each string, ``{field}`` is a field or extra field on the Resource domain
    object.

    If ``{field}`` is ``"hash"``, then an attempt is made to match the
    `{term}` as a *prefix* of the ``Resource.hash`` field.

    If ``{field}`` is an extra field, then an attempt is made to match against
    the extra fields stored against the Resource.

    Note: The search is limited to search against extra fields declared in
    the config setting ``ckan.extra_resource_fields``.

    Note: Due to a Resource's extra fields being stored as a json blob, the
    match is made against the json string representation.  As such, false
    positives may occur:

    If the search criteria is: ::

        query = "field1:term1"

    Then a json blob with the string representation of: ::

        {"field1": "foo", "field2": "term1"}

    will match the search criteria!  This is a known short-coming of this
    approach.

    All matches are made ignoring case; and apart from the ``"hash"`` field,
    a term matches if it is a substring of the field's value.

    Finally, when specifying more than one search criteria, the criteria are
    AND-ed together.

    The ``order`` parameter is used to control the ordering of the results.
    Currently only ordering one field is available, and in ascending order
    only.

    The ``fields`` parameter is deprecated as it is not compatible with calling
    this action with a GET request to the action API.

    The context may contain a flag, `search_query`, which if True will make
    this action behave as if being used by the internal search api.  ie - the
    results will not be dictized, and SearchErrors are thrown for bad search
    queries (rather than ValidationErrors).

    :param query: The search criteria.  See above for description.
    :type query: string or list of strings of the form "{field}:{term1}"
    :param fields: Deprecated
    :type fields: dict of fields to search terms.
    :param order_by: A field on the Resource model that orders the results.
    :type order_by: string
    :param offset: Apply an offset to the query.
    :type offset: int
    :param limit: Apply a limit to the query.
    :type limit: int

    :returns:  A dictionary with a ``count`` field, and a ``results`` field.
    :rtype: dict

    '''
    schema = context.get('schema', logic.schema.default_resource_search_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    model = context['model']

    # Allow either the `query` or `fields` parameter to be given, but not both.
    # Once `fields` parameter is dropped, this can be made simpler.
    # The result of all this gumpf is to populate the local `fields` variable
    # with mappings from field names to list of search terms, or a single
    # search-term string.
    query = data_dict.get('query')
    fields = data_dict.get('fields')

    if query is None and fields is None:
        raise ValidationError({'query': _('Missing value')})

    elif query is not None and fields is not None:
        raise ValidationError(
            {'fields': _('Do not specify if using "query" parameter')})

    elif query is not None:
        if isinstance(query, basestring):
            query = [query]
        try:
            fields = dict(pair.split(":", 1) for pair in query)
        except ValueError:
            raise ValidationError(
                {'query': _('Must be <field>:<value> pair(s)')})

    else:
        log.warning('Use of the "fields" parameter in resource_search is '
                            'deprecated.  Use the "query" parameter instead')

        # The legacy fields paramter splits string terms.
        # So maintain that behaviour
        split_terms = {}
        for field, terms in fields.items():
            if isinstance(terms, basestring):
                terms = terms.split()
            split_terms[field] = terms
        fields = split_terms

    order_by = data_dict.get('order_by')
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    q = model.Session.query(model.Resource).join(model.ResourceGroup).join(model.Package)
    q = q.filter(model.Package.state == 'active')
    q = q.filter(model.Package.private == False)
    q = q.filter(model.Resource.state == 'active')

    resource_fields = model.Resource.get_columns()
    for field, terms in fields.items():

        if isinstance(terms, basestring):
            terms = [terms]

        if field not in resource_fields:
            msg = _('Field "{field}" not recognised in resource_search.')\
                    .format(field=field)

            # Running in the context of the internal search api.
            if context.get('search_query', False):
                raise search.SearchError(msg)

            # Otherwise, assume we're in the context of an external api
            # and need to provide meaningful external error messages.
            raise ValidationError({'query': msg})

        for term in terms:

            # prevent pattern injection
            term = misc.escape_sql_like_special_characters(term)

            model_attr = getattr(model.Resource, field)

            # Treat the has field separately, see docstring.
            if field == 'hash':
                q = q.filter(model_attr.ilike(unicode(term) + '%'))

            # Resource extras are stored in a json blob.  So searching for
            # matching fields is a bit trickier.  See the docstring.
            elif field in model.Resource.get_extra_columns():
                model_attr = getattr(model.Resource, 'extras')

                like = _or_(
                    model_attr.ilike(u'''%%"%s": "%%%s%%",%%''' % (field, term)),
                    model_attr.ilike(u'''%%"%s": "%%%s%%"}''' % (field, term))
                )
                q = q.filter(like)

            # Just a regular field
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

    # If run in the context of a search query, then don't dictize the results.
    if not context.get('search_query', False):
        results = model_dictize.resource_list_dictize(results, context)

    return {'count': count,
            'results': results}

def _tag_search(context, data_dict):
    model = context['model']

    terms = data_dict.get('query') or data_dict.get('q') or []
    if isinstance(terms, basestring):
        terms = [terms]
    terms = [ t.strip() for t in terms if t.strip() ]

    if 'fields' in data_dict:
        log.warning('"fields" parameter is deprecated.  '
                    'Use the "query" parameter instead')

    fields = data_dict.get('fields', {})
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    # TODO: should we check for user authentication first?
    q = model.Session.query(model.Tag)

    if 'vocabulary_id' in data_dict:
        # Filter by vocabulary.
        vocab = model.Vocabulary.get(_get_or_bust(data_dict, 'vocabulary_id'))
        if not vocab:
            raise NotFound
        q = q.filter(model.Tag.vocabulary_id == vocab.id)
    else:
        # If no vocabulary_name in data dict then show free tags only.
        q = q.filter(model.Tag.vocabulary_id == None)
        # If we're searching free tags, limit results to tags that are
        # currently applied to a package.
        q = q.distinct().join(model.Tag.package_tags)

    for field, value in fields.items():
        if field in ('tag', 'tags'):
            terms.append(value)

    if not len(terms):
        return [], 0

    for term in terms:
        escaped_term = misc.escape_sql_like_special_characters(term, escape='\\')
        q = q.filter(model.Tag.name.ilike('%' + escaped_term + '%'))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)
    return q.all(), count

def tag_search(context, data_dict):
    '''Return a list of tags whose names contain a given string.

    By default only free tags (tags that don't belong to any vocabulary) are
    searched. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be searched instead.

    :param query: the string(s) to search for
    :type query: string or list of strings
    :param vocabulary_id: the id or name of the tag vocabulary to search in
      (optional)
    :type vocabulary_id: string
    :param fields: deprecated
    :type fields: dictionary
    :param limit: the maximum number of tags to return
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning tags
        from
    :type offset: int

    :returns: A dictionary with the following keys:

      ``'count'``
        The number of tags in the result.

      ``'results'``
        The list of tags whose names contain the given string, a list of
        dictionaries.

    :rtype: dictionary

    '''
    tags, count = _tag_search(context, data_dict)
    return {'count': count,
            'results': [_table_dictize(tag, context) for tag in tags]}

def tag_autocomplete(context, data_dict):
    '''Return a list of tag names that contain a given string.

    By default only free tags (tags that don't belong to any vocabulary) are
    searched. If the ``vocabulary_id`` argument is given then only tags
    belonging to that vocabulary will be searched instead.

    :param query: the string to search for
    :type query: string
    :param vocabulary_id: the id or name of the tag vocabulary to search in
      (optional)
    :type vocabulary_id: string
    :param fields: deprecated
    :type fields: dictionary
    :param limit: the maximum number of tags to return
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start returning tags
        from
    :type offset: int

    :rtype: list of strings

    '''
    _check_access('tag_autocomplete', context, data_dict)
    matching_tags, count = _tag_search(context, data_dict)
    if matching_tags:
        return [tag.name for tag in matching_tags]
    else:
        return []

def task_status_show(context, data_dict):
    '''Return a task status.

    Either the ``id`` parameter *or* the ``entity_id``, ``task_type`` *and*
    ``key`` parameters must be given.

    :param id: the id of the task status (optional)
    :type id: string
    :param entity_id: the entity_id of the task status (optional)
    :type entity_id: string
    :param task_type: the task_type of the task status (optional)
    :type tast_type: string
    :param key: the key of the task status (optional)
    :type key: string

    :rtype: dictionary

    '''
    model = context['model']
    id = data_dict.get('id')

    if id:
        task_status = model.TaskStatus.get(id)
    else:
        query = model.Session.query(model.TaskStatus)\
            .filter(_and_(
                model.TaskStatus.entity_id == _get_or_bust(data_dict, 'entity_id'),
                model.TaskStatus.task_type == _get_or_bust(data_dict, 'task_type'),
                model.TaskStatus.key == _get_or_bust(data_dict, 'key')
            ))
        task_status = query.first()

    context['task_status'] = task_status

    if task_status is None:
        raise NotFound

    _check_access('task_status_show', context, data_dict)

    task_status_dict = model_dictize.task_status_dictize(task_status, context)
    return task_status_dict

def term_translation_show(context, data_dict):
    '''Return the translations for the given term(s) and language(s).

    :param terms: the terms to search for translations of, e.g. ``'Russian'``,
        ``'romantic novel'``
    :type terms: list of strings
    :param lang_codes: the language codes of the languages to search for
        translations into, e.g. ``'en'``, ``'de'`` (optional, default is to
        search for translations into any language)
    :type lang_codes: list of language code strings

    :rtype: a list of term translation dictionaries each with keys ``'term'``
        (the term searched for, in the source language), ``'term_translation'``
        (the translation of the term into the target language) and
        ``'lang_code'`` (the language code of the target language)

    '''
    model = context['model']

    trans_table = model.term_translation_table

    q = _select([trans_table])

    if 'terms' not in data_dict:
        raise ValidationError({'terms': 'terms not in data'})

    # This action accepts `terms` as either a list of strings, or a single
    # string.
    terms = _get_or_bust(data_dict, 'terms')
    if isinstance(terms, basestring):
        terms = [terms]
    if terms:
        q = q.where(trans_table.c.term.in_(terms))

    # This action accepts `lang_codes` as either a list of strings, or a single
    # string.
    if 'lang_codes' in data_dict:
        lang_codes = _get_or_bust(data_dict, 'lang_codes')
        if isinstance(lang_codes, basestring):
            lang_codes = [lang_codes]
        q = q.where(trans_table.c.lang_code.in_(lang_codes))

    conn = model.Session.connection()
    cursor = conn.execute(q)

    results = []

    for row in cursor:
        results.append(_table_dictize(row, context))

    return results

# Only internal services are allowed to call get_site_user.
def get_site_user(context, data_dict):
    _check_access('get_site_user', context, data_dict)
    model = context['model']
    site_id = config.get('ckan.site_id', 'ckan_site_user')
    user = model.User.get(site_id)
    if not user:
        apikey = str(uuid.uuid4())
        user = model.User(name=site_id,
                          password=apikey,
                          apikey=apikey)
        # make sysadmin
        user.sysadmin = True
        model.Session.add(user)
        model.Session.flush()
    if not context.get('defer_commit'):
        model.repo.commit_and_remove()

    return {'name': user.name,
            'apikey': user.apikey}

def roles_show(context, data_dict):
    '''Return the roles of all users and authorization groups for an object.

    :param domain_object: a package or group name or id
        to filter the results by
    :type domain_object: string
    :param user: a user name or id
    :type user: string

    :rtype: list of dictionaries

    '''
    model = context['model']
    session = context['session']
    domain_object_ref = _get_or_bust(data_dict, 'domain_object')
    user_ref = data_dict.get('user')

    domain_object = ckan.logic.action.get_domain_object(model, domain_object_ref)
    if isinstance(domain_object, model.Package):
        query = session.query(model.PackageRole).join('package')
    elif isinstance(domain_object, model.Group):
        query = session.query(model.GroupRole).join('group')
    elif domain_object is model.System:
        query = session.query(model.SystemRole)
    else:
        raise NotFound(_('Cannot list entity of this type: %s') % type(domain_object).__name__)
    # Filter by the domain_obj (apart from if it is the system object)
    if not isinstance(domain_object, type):
        query = query.filter_by(id=domain_object.id)

    # Filter by the user
    if user_ref:
        user = model.User.get(user_ref)
        if not user:
            raise NotFound(_('unknown user:') + repr(user_ref))
        query = query.join('user').filter_by(id=user.id)

    uors = query.all()

    uors_dictized = [_table_dictize(uor, context) for uor in uors]

    result = {'domain_object_type': type(domain_object).__name__,
              'domain_object_id': domain_object.id if domain_object != model.System else None,
              'roles': uors_dictized}
    if user_ref:
        result['user'] = user.id

    return result

def status_show(context, data_dict):
    '''Return a dictionary with information about the site's configuration.

    :rtype: dictionary

    '''
    return {
        'site_title': config.get('ckan.site_title'),
        'site_description': config.get('ckan.site_description'),
        'site_url': config.get('ckan.site_url'),
        'ckan_version': ckan.__version__,
        'error_emails_to': config.get('email_to'),
        'locale_default': config.get('ckan.locale_default'),
        'extensions': config.get('ckan.plugins').split(),
        }

def vocabulary_list(context, data_dict):
    '''Return a list of all the site's tag vocabularies.

    :rtype: list of dictionaries

    '''
    model = context['model']
    vocabulary_objects = model.Session.query(model.Vocabulary).all()
    return model_dictize.vocabulary_list_dictize(vocabulary_objects, context)

def vocabulary_show(context, data_dict):
    '''Return a single tag vocabulary.

    :param id: the id or name of the vocabulary
    :type id: string
    :return: the vocabulary.
    :rtype: dictionary

    '''
    model = context['model']
    vocab_id = data_dict.get('id')
    if not vocab_id:
        raise ValidationError({'id': _('id not in data')})
    vocabulary = model.vocabulary.Vocabulary.get(vocab_id)
    if vocabulary is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)
    vocabulary_dict = model_dictize.vocabulary_dictize(vocabulary, context)
    return vocabulary_dict

def user_activity_list(context, data_dict):
    '''Return a user's public activity stream.

    You must be authorized to view the user's profile.


    :param id: the id or name of the user
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _check_access('user_show', context, data_dict)

    model = context['model']

    user_ref = _get_or_bust(data_dict, 'id')  # May be user name or id.
    user = model.User.get(user_ref)
    if user is None:
        raise logic.NotFound

    offset = int(data_dict.get('offset', 0))
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    activity_objects = model.activity.user_activity_list(user.id, limit=limit,
            offset=offset)
    return model_dictize.activity_list_dictize(activity_objects, context)

def package_activity_list(context, data_dict):
    '''Return a package's activity stream.

    You must be authorized to view the package.

    :param id: the id or name of the package
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _check_access('package_show', context, data_dict)

    model = context['model']

    package_ref = _get_or_bust(data_dict, 'id')  # May be name or ID.
    package = model.Package.get(package_ref)
    if package is None:
        raise logic.NotFound

    offset = int(data_dict.get('offset', 0))
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    activity_objects = model.activity.package_activity_list(package.id,
            limit=limit, offset=offset)
    return model_dictize.activity_list_dictize(activity_objects, context)

def group_activity_list(context, data_dict):
    '''Return a group's activity stream.

    You must be authorized to view the group.

    :param id: the id or name of the group
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _check_access('group_show', context, data_dict)

    model = context['model']
    group_id = _get_or_bust(data_dict, 'id')
    offset = int(data_dict.get('offset', 0))
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    # Convert group_id (could be id or name) into id.
    group_show = logic.get_action('group_show')
    group_id = group_show(context, {'id': group_id})['id']

    activity_objects = model.activity.group_activity_list(group_id,
            limit=limit, offset=offset)
    return model_dictize.activity_list_dictize(activity_objects, context)

def organization_activity_list(context, data_dict):
    '''Return a organization's activity stream.

    :param id: the id or name of the organization
    :type id: string

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _check_access('organization_show', context, data_dict)

    model = context['model']
    org_id = _get_or_bust(data_dict, 'id')
    offset = int(data_dict.get('offset', 0))
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    # Convert org_id (could be id or name) into id.
    org_show = logic.get_action('organization_show')
    org_id = org_show(context, {'id': org_id})['id']

    activity_objects = model.activity.group_activity_list(org_id,
            limit=limit, offset=offset)
    return model_dictize.activity_list_dictize(activity_objects, context)

def recently_changed_packages_activity_list(context, data_dict):
    '''Return the activity stream of all recently added or changed packages.

    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    model = context['model']
    offset = int(data_dict.get('offset', 0))
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    activity_objects = model.activity.recently_changed_packages_activity_list(
            limit=limit, offset=offset)

    return model_dictize.activity_list_dictize(activity_objects, context)

def activity_detail_list(context, data_dict):
    '''Return an activity's list of activity detail items.

    :param id: the id of the activity
    :type id: string
    :rtype: list of dictionaries.

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    model = context['model']
    activity_id = _get_or_bust(data_dict, 'id')
    activity_detail_objects = model.ActivityDetail.by_activity_id(activity_id)
    return model_dictize.activity_detail_list_dictize(activity_detail_objects, context)


def user_activity_list_html(context, data_dict):
    '''Return a user's public activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: The id or name of the user.
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: string

    '''
    activity_stream = user_activity_list(context, data_dict)
    offset = int(data_dict.get('offset', 0))
    extra_vars = {
        'controller': 'user',
        'action': 'activity',
        'id': data_dict['id'],
        'offset': offset,
        }
    return activity_streams.activity_list_to_html(context, activity_stream,
            extra_vars)

def package_activity_list_html(context, data_dict):
    '''Return a package's activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: the id or name of the package
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: string

    '''
    activity_stream = package_activity_list(context, data_dict)
    offset = int(data_dict.get('offset', 0))
    extra_vars = {
        'controller': 'package',
        'action': 'activity',
        'id': data_dict['id'],
        'offset': offset,
        }
    return activity_streams.activity_list_to_html(context, activity_stream,
            extra_vars)

def group_activity_list_html(context, data_dict):
    '''Return a group's activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: the id or name of the group
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: string

    '''
    activity_stream = group_activity_list(context, data_dict)
    offset = int(data_dict.get('offset', 0))
    extra_vars = {
        'controller': 'group',
        'action': 'activity',
        'id': data_dict['id'],
        'offset': offset,
        }
    return activity_streams.activity_list_to_html(context, activity_stream,
            extra_vars)

def organization_activity_list_html(context, data_dict):
    '''Return a organization's activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: the id or name of the organization
    :type id: string

    :rtype: string

    '''
    activity_stream = organization_activity_list(context, data_dict)
    return activity_streams.activity_list_to_html(context, activity_stream)

def recently_changed_packages_activity_list_html(context, data_dict):
    '''Return the activity stream of all recently changed packages as HTML.

    The activity stream includes all recently added or changed packages. It is
    rendered as a snippet of HTML meant to be included in an HTML page, i.e. it
    doesn't have any HTML header or footer.

    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: string

    '''
    activity_stream = recently_changed_packages_activity_list(context,
            data_dict)
    offset = int(data_dict.get('offset', 0))
    extra_vars = {
        'controller': 'package',
        'action': 'activity',
        'offset': offset,
        }
    return activity_streams.activity_list_to_html(context, activity_stream,
            extra_vars)


def _follower_count(context, data_dict, default_schema, ModelClass):
    schema = context.get('schema', default_schema)
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)
    return ModelClass.follower_count(data_dict['id'])


def user_follower_count(context, data_dict):
    '''Return the number of followers of a user.

    :param id: the id or name of the user
    :type id: string

    :rtype: int

    '''
    return _follower_count(context, data_dict,
            ckan.logic.schema.default_follow_user_schema(),
            context['model'].UserFollowingUser)


def dataset_follower_count(context, data_dict):
    '''Return the number of followers of a dataset.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: int

    '''
    return _follower_count(context, data_dict,
            ckan.logic.schema.default_follow_dataset_schema(),
            context['model'].UserFollowingDataset)


def group_follower_count(context, data_dict):
    '''Return the number of followers of a group.

    :param id: the id or name of the group
    :type id: string

    :rtype: int

    '''
    return _follower_count(context, data_dict,
            ckan.logic.schema.default_follow_group_schema(),
            context['model'].UserFollowingGroup)


def _follower_list(context, data_dict, default_schema, FollowerClass):
    schema = context.get('schema', default_schema)
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    # Get the list of Follower objects.
    model = context['model']
    object_id = data_dict.get('id')
    followers = FollowerClass.follower_list(object_id)

    # Convert the list of Follower objects to a list of User objects.
    users = [model.User.get(follower.follower_id) for follower in followers]
    users = [user for user in users if user is not None]

    # Dictize the list of User objects.
    return model_dictize.user_list_dictize(users, context)


def user_follower_list(context, data_dict):
    '''Return the list of users that are following the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('user_follower_list', context, data_dict)
    return _follower_list(context, data_dict,
            ckan.logic.schema.default_follow_user_schema(),
            context['model'].UserFollowingUser)


def dataset_follower_list(context, data_dict):
    '''Return the list of users that are following the given dataset.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('dataset_follower_list', context, data_dict)
    return _follower_list(context, data_dict,
            ckan.logic.schema.default_follow_dataset_schema(),
            context['model'].UserFollowingDataset)


def group_follower_list(context, data_dict):
    '''Return the list of users that are following the given group.

    :param id: the id or name of the group
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('group_follower_list', context, data_dict)
    return _follower_list(context, data_dict,
            ckan.logic.schema.default_follow_group_schema(),
            context['model'].UserFollowingGroup)


def _am_following(context, data_dict, default_schema, FollowerClass):
    schema = context.get('schema', default_schema)
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    if 'user' not in context:
        raise logic.NotAuthorized

    model = context['model']

    userobj = model.User.get(context['user'])
    if not userobj:
        raise logic.NotAuthorized

    object_id = data_dict.get('id')

    return FollowerClass.is_following(userobj.id, object_id)


def am_following_user(context, data_dict):
    '''Return ``True`` if you're following the given user, ``False`` if not.

    :param id: the id or name of the user
    :type id: string

    :rtype: boolean

    '''
    return _am_following(context, data_dict,
            ckan.logic.schema.default_follow_user_schema(),
            context['model'].UserFollowingUser)


def am_following_dataset(context, data_dict):
    '''Return ``True`` if you're following the given dataset, ``False`` if not.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: boolean

    '''
    return _am_following(context, data_dict,
            ckan.logic.schema.default_follow_dataset_schema(),
            context['model'].UserFollowingDataset)


def am_following_group(context, data_dict):
    '''Return ``True`` if you're following the given group, ``False`` if not.

    :param id: the id or name of the group
    :type id: string

    :rtype: boolean

    '''
    return _am_following(context, data_dict,
            ckan.logic.schema.default_follow_group_schema(),
            context['model'].UserFollowingGroup)


def _followee_count(context, data_dict, FollowerClass):
    if not context.get('skip_validation'):
        schema = context.get('schema',
                ckan.logic.schema.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)
    return FollowerClass.followee_count(data_dict['id'])


def followee_count(context, data_dict):
    '''Return the number of objects that are followed by the given user.

    Counts all objects, of any type, that the given user is following
    (e.g. followed users, followed datasets, followed groups).

    :param id: the id of the user
    :type id: string

    :rtype: int

    '''
    model = context['model']
    followee_users = _followee_count(context, data_dict,
            model.UserFollowingUser)

    # followee_users has validated data_dict so the following functions don't
    # need to validate it again.
    context['skip_validation'] = True

    followee_datasets = _followee_count(context, data_dict,
            model.UserFollowingDataset)
    followee_groups = _followee_count(context, data_dict,
            model.UserFollowingGroup)

    return sum((followee_users, followee_datasets, followee_groups))


def user_followee_count(context, data_dict):
    '''Return the number of users that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    '''
    return _followee_count(context, data_dict,
            context['model'].UserFollowingUser)


def dataset_followee_count(context, data_dict):
    '''Return the number of datasets that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    '''
    return _followee_count(context, data_dict,
            context['model'].UserFollowingDataset)


def group_followee_count(context, data_dict):
    '''Return the number of groups that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    '''
    return _followee_count(context, data_dict,
            context['model'].UserFollowingGroup)


def followee_list(context, data_dict):
    '''Return the list of objects that are followed by the given user.

    Returns all objects, of any type, that the given user is following
    (e.g. followed users, followed datasets, followed groups.. ).

    :param id: the id of the user
    :type id: string

    :param q: a query string to limit results by, only objects whose display
        name begins with the given string (case-insensitive) wil be returned
        (optional)
    :type q: string

    :rtype: list of dictionaries, each with keys 'type' (e.g. 'user',
        'dataset' or 'group'), 'display_name' (e.g. a user's display name,
        or a package's title) and 'dict' (e.g. a dict representing the
        followed user, package or group, the same as the dict that would be
        returned by user_show, package_show or group_show)

    '''
    _check_access('followee_list', context, data_dict)
    schema = context.get('schema') or (
            ckan.logic.schema.default_follow_user_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    def display_name(followee):
        '''Return a display name for the given user, group or dataset dict.'''
        display_name = followee.get('display_name')
        fullname = followee.get('fullname')
        title = followee.get('title')
        name = followee.get('name')
        return display_name or fullname or title or name

    # Get the followed objects.
    # TODO: Catch exceptions raised by these *_followee_list() functions?
    # FIXME should we be changing the context like this it seems dangerous
    followee_dicts = []
    context['skip_validation'] = True
    context['ignore_auth'] = True
    for followee_list_function, followee_type in (
            (user_followee_list, 'user'),
            (dataset_followee_list, 'dataset'),
            (group_followee_list, 'group')):
        dicts = followee_list_function(context, data_dict)
        for d in dicts:
            followee_dicts.append(
                    {'type': followee_type,
                    'display_name': display_name(d),
                    'dict': d})

    followee_dicts.sort(key=lambda d: d['display_name'])

    q = data_dict.get('q')
    if q:
        q = q.strip().lower()
        matching_followee_dicts = []
        for followee_dict in followee_dicts:
            if followee_dict['display_name'].strip().lower().startswith(q):
                matching_followee_dicts.append(followee_dict)
        followee_dicts = matching_followee_dicts

    return followee_dicts


def user_followee_list(context, data_dict):
    '''Return the list of users that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('user_followee_list', context, data_dict)

    if not context.get('skip_validation'):
        schema = context.get('schema') or (
                ckan.logic.schema.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)

    # Get the list of Follower objects.
    model = context['model']
    user_id = _get_or_bust(data_dict, 'id')
    followees = model.UserFollowingUser.followee_list(user_id)

    # Convert the list of Follower objects to a list of User objects.
    users = [model.User.get(followee.object_id) for followee in followees]
    users = [user for user in users if user is not None]

    # Dictize the list of User objects.
    return model_dictize.user_list_dictize(users, context)

def dataset_followee_list(context, data_dict):
    '''Return the list of datasets that are followed by the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('dataset_followee_list', context, data_dict)

    if not context.get('skip_validation'):
        schema = context.get('schema') or (
                ckan.logic.schema.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)

    # Get the list of Follower objects.
    model = context['model']
    user_id = _get_or_bust(data_dict, 'id')
    followees = model.UserFollowingDataset.followee_list(user_id)

    # Convert the list of Follower objects to a list of Package objects.
    datasets = [model.Package.get(followee.object_id) for followee in followees]
    datasets = [dataset for dataset in datasets if dataset is not None]

    # Dictize the list of Package objects.
    return [model_dictize.package_dictize(dataset, context) for dataset in datasets]


def group_followee_list(context, data_dict):
    '''Return the list of groups that are followed by the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('group_followee_list', context, data_dict)

    if not context.get('skip_validation'):
        schema = context.get('schema',
                ckan.logic.schema.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)

    # Get the list of UserFollowingGroup objects.
    model = context['model']
    user_id = _get_or_bust(data_dict, 'id')
    followees = model.UserFollowingGroup.followee_list(user_id)

    # Convert the UserFollowingGroup objects to a list of Group objects.
    groups = [model.Group.get(followee.object_id) for followee in followees]
    groups = [group for group in groups if group is not None]

    # Dictize the list of Group objects.
    return [model_dictize.group_dictize(group, context) for group in groups]


def dashboard_activity_list(context, data_dict):
    '''Return the authorized user's dashboard activity stream.

    Unlike the activity dictionaries returned by other ``*_activity_list``
    actions, these activity dictionaries have an extra boolean value with key
    ``is_new`` that tells you whether the activity happened since the user last
    viewed her dashboard (``'is_new': True``) or not (``'is_new': False``).

    The user's own activities are always marked ``'is_new': False``.

    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ``ckan.activity_list_limit`` setting)

    :rtype: list of activity dictionaries

    '''
    schema = context.get('schema',
                         ckan.logic.schema.default_pagination_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    _check_access('dashboard_activity_list', context, data_dict)

    model = context['model']
    user_id = model.User.get(context['user']).id
    offset = int(data_dict.get('offset', 0))
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    activity_objects = model.activity.dashboard_activity_list(user_id,
            limit=limit, offset=offset)

    activity_dicts = model_dictize.activity_list_dictize(
            activity_objects, context)

    # Mark the new (not yet seen by user) activities.
    strptime = datetime.datetime.strptime
    fmt = '%Y-%m-%dT%H:%M:%S.%f'
    last_viewed = model.Dashboard.get(user_id).activity_stream_last_viewed
    for activity in activity_dicts:
        if activity['user_id'] == user_id:
            # Never mark the user's own activities as new.
            activity['is_new'] = False
        else:
            activity['is_new'] = (strptime(activity['timestamp'], fmt)
                    > last_viewed)

    return activity_dicts


def dashboard_activity_list_html(context, data_dict):
    '''Return the authorized user's dashboard activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: the id or name of the user
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: 0)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: 31, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: string

    '''
    schema = context.get(
        'schema', ckan.logic.schema.default_pagination_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    activity_stream = dashboard_activity_list(context, data_dict)
    model = context['model']
    offset = int(data_dict.get('offset', 0))
    extra_vars = {
        'controller': 'user',
        'action': 'dashboard',
        'offset': offset,
    }
    return activity_streams.activity_list_to_html(context, activity_stream,
                                                  extra_vars)


def dashboard_new_activities_count(context, data_dict):
    '''Return the number of new activities in the user's dashboard.

    Return the number of new activities in the authorized user's dashboard
    activity stream.

    Activities from the user herself are not counted by this function even
    though they appear in the dashboard (users don't want to be notified about
    things they did themselves).

    :rtype: int

    '''
    _check_access('dashboard_new_activities_count', context, data_dict)
    activities = logic.get_action('dashboard_activity_list')(
            context, data_dict)
    return len([activity for activity in activities if activity['is_new']])


def _unpick_search(sort, allowed_fields=None, total=None):
    ''' This is a helper function that takes a sort string
    eg 'name asc, last_modified desc' and returns a list of
    split field order eg [('name', 'asc'), ('last_modified', 'desc')]
    allowed_fields can limit which field names are ok.
    total controls how many sorts can be specifed '''
    sorts = []
    split_sort = sort.split(',')
    for part in split_sort:
        split_part = part.strip().split()
        field = split_part[0]
        if len(split_part) > 1:
            order = split_part[1].lower()
        else:
            order = 'asc'
        if allowed_fields:
            if field not in allowed_fields:
                raise ValidationError('Cannot sort by field `%s`' % field)
        if order not in ['asc', 'desc']:
            raise ValidationError('Invalid sort direction `%s`' % order)
        sorts.append((field, order))
    if total and len(sorts) > total:
        raise ValidationError(
            'Too many sort criteria provided only %s allowed' % total)
    return sorts


def member_roles_list(context, data_dict):
    '''Return the possible roles for members of groups and organizations.

    :returns: a list of dictionaries each with two keys: "text" (the display
        name of the role, e.g. "Admin") and "value" (the internal name of the
        role, e.g. "admin")
    :rtype: list of dictionaries

    '''
    _check_access('member_roles_list', context, data_dict)
    return new_authz.roles_list()
