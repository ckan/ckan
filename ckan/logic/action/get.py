# encoding: utf-8

'''API functions for searching for and getting data from CKAN.'''

import uuid
import logging
import json
import datetime
import socket

from ckan.common import config
import sqlalchemy
from paste.deploy.converters import asbool
from six import string_types, text_type

import ckan.lib.dictization
import ckan.logic as logic
import ckan.logic.action
import ckan.logic.schema
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.jobs as jobs
import ckan.lib.navl.dictization_functions
import ckan.model as model
import ckan.model.misc as misc
import ckan.plugins as plugins
import ckan.lib.search as search
import ckan.lib.plugins as lib_plugins
import ckan.lib.activity_streams as activity_streams
import ckan.lib.datapreview as datapreview
import ckan.authz as authz

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


def _filter_activity_by_user(activity_list, users=[]):
    '''
    Return the given ``activity_list`` with activities from the specified
    users removed. The users parameters should be a list of ids.

    A *new* filtered list is returned, the given ``activity_list`` itself is
    not modified.
    '''
    if not len(users):
        return activity_list
    new_list = []
    for activity in activity_list:
        if activity.user_id not in users:
            new_list.append(activity)
    return new_list


def _activity_stream_get_filtered_users():
    '''
    Get the list of users from the :ref:`ckan.hide_activity_from_users` config
    option and return a list of their ids. If the config is not specified,
    returns the id of the site user.
    '''
    users = config.get('ckan.hide_activity_from_users')
    if users:
        users_list = users.split()
    else:
        context = {'model': model, 'ignore_auth': True}
        site_user = logic.get_action('get_site_user')(context)
        users_list = [site_user.get('name')]

    return model.User.user_ids_for_name_or_id(users_list)


def _package_list_with_resources(context, package_revision_list):
    package_list = []
    for package in package_revision_list:
        result_dict = model_dictize.package_dictize(package,context)
        package_list.append(result_dict)
    return package_list


def site_read(context, data_dict=None):
    '''Return ``True``.

    :rtype: bool
    '''
    _check_access('site_read', context, data_dict)
    return True


@logic.validate(logic.schema.default_pagination_schema)
def package_list(context, data_dict):
    '''Return a list of the names of the site's datasets (packages).

    :param limit: if given, the list of datasets will be broken into pages of
        at most ``limit`` datasets per page and only one page will be returned
        at a time (optional)
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start
        returning packages from
    :type offset: int

    :rtype: list of strings

    '''
    model = context["model"]
    api = context.get("api_version", 1)

    _check_access('package_list', context, data_dict)

    package_table = model.package_table
    col = (package_table.c.id
           if api == 2 else package_table.c.name)
    query = _select([col])
    query = query.where(_and_(
        package_table.c.state == 'active',
        package_table.c.private == False,
    ))
    query = query.order_by(col)

    limit = data_dict.get('limit')
    if limit:
        query = query.limit(limit)

    offset = data_dict.get('offset')
    if offset:
        query = query.offset(offset)

    ## Returns the first field in each result record
    return [r[0] for r in query.execute()]


@logic.validate(logic.schema.default_package_list_schema)
def current_package_list_with_resources(context, data_dict):
    '''Return a list of the site's datasets (packages) and their resources.

    The list is sorted most-recently-modified first.

    :param limit: if given, the list of datasets will be broken into pages of
        at most ``limit`` datasets per page and only one page will be returned
        at a time (optional)
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start
        returning packages from
    :type offset: int
    :param page: when ``limit`` is given, which page to return,
        Deprecated: use ``offset``
    :type page: int

    :rtype: list of dictionaries

    '''
    model = context["model"]
    limit = data_dict.get('limit')
    offset = data_dict.get('offset', 0)
    user = context['user']

    if not 'offset' in data_dict and 'page' in data_dict:
        log.warning('"page" parameter is deprecated.  '
                    'Use the "offset" parameter instead')
        page = data_dict['page']
        if limit:
            offset = (page - 1) * limit
        else:
            offset = 0

    _check_access('current_package_list_with_resources', context, data_dict)

    search = package_search(context, {
        'q': '', 'rows': limit, 'start': offset,
        'include_private': authz.is_sysadmin(user) })
    return search.get('results', [])


def revision_list(context, data_dict):
    '''Return a list of the IDs of the site's revisions. They are sorted with
    the newest first.

    Since the results are limited to 50 IDs, you can page through them using
    parameter ``since_id``.

    :param since_id: the revision ID after which you want the revisions
    :type since_id: string
    :param since_time: the timestamp after which you want the revisions
    :type since_time: string
    :param sort: the order to sort the related items in, possible values are
      'time_asc', 'time_desc' (default). (optional)
    :type sort: string
    :rtype: list of revision IDs, limited to 50

    '''
    model = context['model']
    since_id = data_dict.get('since_id')
    since_time_str = data_dict.get('since_time')
    sort_str = data_dict.get('sort')
    PAGE_LIMIT = 50

    _check_access('revision_list', context, data_dict)

    since_time = None
    if since_id:
        rev = model.Session.query(model.Revision).get(since_id)
        if rev is None:
            raise NotFound
        since_time = rev.timestamp
    elif since_time_str:
        try:
            from ckan.lib import helpers as h
            since_time = h.date_str_to_datetime(since_time_str)
        except ValueError:
            raise logic.ValidationError('Timestamp did not parse')
    revs = model.Session.query(model.Revision)
    if since_time:
        revs = revs.filter(model.Revision.timestamp > since_time)

    sortables = {
        'time_asc': model.Revision.timestamp.asc,
        'time_desc': model.Revision.timestamp.desc,
    }
    if sort_str and sort_str not in sortables:
        raise logic.ValidationError(
            'Invalid sort value. Allowable values: %r' % sortables.keys())
    sort_func = sortables.get(sort_str or 'time_desc')
    revs = revs.order_by(sort_func())

    revs = revs.limit(PAGE_LIMIT)
    return [rev_.id for rev_ in revs]


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

    _check_access('package_revision_list', context, data_dict)

    revision_dicts = []
    for revision, object_revisions in pkg.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False,
                                                     include_groups=False))
    return revision_dicts


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

    trans = authz.roles_trans()

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
    group_type = data_dict.get('type', 'group')
    ref_group_by = 'id' if api == 2 else 'name'
    pagination_dict = {}
    limit = data_dict.get('limit')
    if limit:
        pagination_dict['limit'] = data_dict['limit']
    offset = data_dict.get('offset')
    if offset:
        pagination_dict['offset'] = data_dict['offset']
    if pagination_dict:
        pagination_dict, errors = _validate(
            data_dict, logic.schema.default_pagination_schema(), context)
        if errors:
            raise ValidationError(errors)
    sort = data_dict.get('sort') or 'title'
    q = data_dict.get('q')

    all_fields = asbool(data_dict.get('all_fields', None))

    # order_by deprecated in ckan 1.8
    # if it is supplied and sort isn't use order_by and raise a warning
    order_by = data_dict.get('order_by', '')
    if order_by:
        log.warn('`order_by` deprecated please use `sort`')
        if not data_dict.get('sort'):
            sort = order_by

    # if the sort is packages and no sort direction is supplied we want to do a
    # reverse sort to maintain compatibility.
    if sort.strip() in ('packages', 'package_count'):
        sort = 'package_count desc'

    sort_info = _unpick_search(sort,
                               allowed_fields=['name', 'packages',
                                               'package_count', 'title'],
                               total=1)

    if sort_info and sort_info[0][0] == 'package_count':
        query = model.Session.query(model.Group.id,
                                    model.Group.name,
                                    sqlalchemy.func.count(model.Group.id))

        query = query.filter(model.Member.group_id == model.Group.id) \
                     .filter(model.Member.table_id == model.Package.id) \
                     .filter(model.Member.table_name == 'package') \
                     .filter(model.Package.state == 'active')
    else:
        query = model.Session.query(model.Group.id,
                                    model.Group.name)

    query = query.filter(model.Group.state == 'active')

    if groups:
        query = query.filter(model.Group.name.in_(groups))
    if q:
        q = u'%{0}%'.format(q)
        query = query.filter(_or_(
            model.Group.name.ilike(q),
            model.Group.title.ilike(q),
            model.Group.description.ilike(q),
        ))

    query = query.filter(model.Group.is_organization == is_org)
    query = query.filter(model.Group.type == group_type)

    if sort_info:
        sort_field = sort_info[0][0]
        sort_direction = sort_info[0][1]
        if sort_field == 'package_count':
            query = query.group_by(model.Group.id, model.Group.name)
            sort_model_field = sqlalchemy.func.count(model.Group.id)
        elif sort_field == 'name':
            sort_model_field = model.Group.name
        elif sort_field == 'title':
            sort_model_field = model.Group.title

        if sort_direction == 'asc':
            query = query.order_by(sqlalchemy.asc(sort_model_field))
        else:
            query = query.order_by(sqlalchemy.desc(sort_model_field))

    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)

    groups = query.all()

    if all_fields:
        action = 'organization_show' if is_org else 'group_show'
        group_list = []
        for group in groups:
            data_dict['id'] = group.id
            for key in ('include_extras', 'include_tags', 'include_users',
                        'include_groups', 'include_followers'):
                if key not in data_dict:
                    data_dict[key] = False

            group_list.append(logic.get_action(action)(context, data_dict))
    else:
        group_list = [getattr(group, ref_group_by) for group in groups]

    return group_list


def group_list(context, data_dict):
    '''Return a list of the names of the site's groups.

    :param order_by: the field to sort the list by, must be ``'name'`` or
      ``'packages'`` (optional, default: ``'name'``) Deprecated use sort.
    :type order_by: string
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name', 'package_count' and 'title'
    :type sort: string
    :param limit: if given, the list of groups will be broken into pages of
        at most ``limit`` groups per page and only one page will be returned
        at a time (optional)
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start
        returning groups from
    :type offset: int
    :param groups: a list of names of the groups to return, if given only
        groups whose names are in this list will be returned (optional)
    :type groups: list of strings
    :param all_fields: return group dictionaries instead of just names. Only
        core fields are returned - get some more using the include_* options.
        Returning a list of packages is too expensive, so the `packages`
        property for each group is deprecated, but there is a count of the
        packages in the `package_count` property.
        (optional, default: ``False``)
    :type all_fields: bool
    :param include_dataset_count: if all_fields, include the full package_count
        (optional, default: ``True``)
    :type include_dataset_count: bool
    :param include_extras: if all_fields, include the group extra fields
        (optional, default: ``False``)
    :type include_extras: bool
    :param include_tags: if all_fields, include the group tags
        (optional, default: ``False``)
    :type include_tags: bool
    :param include_groups: if all_fields, include the groups the groups are in
        (optional, default: ``False``).
    :type include_groups: bool
    :param include_users: if all_fields, include the group users
        (optional, default: ``False``).
    :type include_users: bool

    :rtype: list of strings
    '''
    _check_access('group_list', context, data_dict)
    return _group_or_org_list(context, data_dict)


def organization_list(context, data_dict):
    '''Return a list of the names of the site's organizations.

    :param order_by: the field to sort the list by, must be ``'name'`` or
      ``'packages'`` (optional, default: ``'name'``) Deprecated use sort.
    :type order_by: string
    :param sort: sorting of the search results.  Optional.  Default:
        "name asc" string of field name and sort-order. The allowed fields are
        'name', 'package_count' and 'title'
    :type sort: string
    :param limit: if given, the list of organizations will be broken into pages
        of at most ``limit`` organizations per page and only one page will be
        returned at a time (optional)
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start
        returning organizations from
    :type offset: int
    :param organizations: a list of names of the groups to return,
        if given only groups whose names are in this list will be
        returned (optional)
    :type organizations: list of strings
    :param all_fields: return group dictionaries instead of just names. Only
        core fields are returned - get some more using the include_* options.
        Returning a list of packages is too expensive, so the `packages`
        property for each group is deprecated, but there is a count of the
        packages in the `package_count` property.
        (optional, default: ``False``)
    :type all_fields: bool
    :param include_dataset_count: if all_fields, include the full package_count
        (optional, default: ``True``)
    :type include_dataset_count: bool
    :param include_extras: if all_fields, include the organization extra fields
        (optional, default: ``False``)
    :type include_extras: bool
    :param include_tags: if all_fields, include the organization tags
        (optional, default: ``False``)
    :type include_tags: bool
    :param include_groups: if all_fields, include the organizations the
        organizations are in
        (optional, default: ``False``)
    :type include_groups: bool
    :param include_users: if all_fields, include the organization users
        (optional, default: ``False``).
    :type include_users: bool

    :rtype: list of strings

    '''
    _check_access('organization_list', context, data_dict)
    data_dict['groups'] = data_dict.pop('organizations', [])
    data_dict.setdefault('type', 'organization')
    return _group_or_org_list(context, data_dict, is_org=True)


def group_list_authz(context, data_dict):
    '''Return the list of groups that the user is authorized to edit.

    :param available_only: remove the existing groups in the package
      (optional, default: ``False``)
    :type available_only: bool

    :param am_member: if ``True`` return only the groups the logged-in user is
      a member of, otherwise return all groups that the user is authorized to
      edit (for example, sysadmin users are authorized to edit all groups)
      (optional, default: ``False``)
    :type am_member: bool

    :returns: list of dictized groups that the user is authorized to edit
    :rtype: list of dicts

    '''
    model = context['model']
    user = context['user']
    available_only = data_dict.get('available_only', False)
    am_member = data_dict.get('am_member', False)

    _check_access('group_list_authz', context, data_dict)

    sysadmin = authz.is_sysadmin(user)
    roles = authz.get_roles_with_permission('manage_group')
    if not roles:
        return []
    user_id = authz.get_user_id_for_username(user, allow_none=True)
    if not user_id:
        return []

    if not sysadmin or am_member:
        q = model.Session.query(model.Member) \
            .filter(model.Member.table_name == 'user') \
            .filter(model.Member.capacity.in_(roles)) \
            .filter(model.Member.table_id == user_id) \
            .filter(model.Member.state == 'active')
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
    '''Return the organizations that the user has a given permission for.

    Specifically it returns the list of organizations that the currently
    authorized user has a given permission (for example: "manage_group")
    against.

    By default this returns the list of organizations that the currently
    authorized user is member of, in any capacity.

    When a user becomes a member of an organization in CKAN they're given a
    "capacity" (sometimes called a "role"), for example "member", "editor" or
    "admin".

    Each of these roles has certain permissions associated with it. For example
    the admin role has the "admin" permission (which means they have permission
    to do anything). The editor role has permissions like "create_dataset",
    "update_dataset" and "delete_dataset".  The member role has the "read"
    permission.

    This function returns the list of organizations that the authorized user
    has a given permission for. For example the list of organizations that the
    user is an admin of, or the list of organizations that the user can create
    datasets in. This takes account of when permissions cascade down an
    organization hierarchy.

    :param id: the name or id of the user to get the organization list for
        (optional, defaults to the currently authorized user (logged in or via
        API key))
    :type id: string

    :param permission: the permission the user has against the
        returned organizations, for example ``"read"`` or ``"create_dataset"``
        (optional, default: ``"manage_group"``)
    :type permission: string
    :param include_dataset_count: include the package_count in each org
        (optional, default: ``False``)
    :type include_dataset_count: bool

    :returns: list of organizations that the user has the given permission for
    :rtype: list of dicts

    '''
    model = context['model']
    if data_dict.get('id'):
        user_obj = model.User.get(data_dict['id'])
        if not user_obj:
            raise NotFound
        user = user_obj.name
    else:
        user = context['user']

    _check_access('organization_list_for_user', context, data_dict)
    sysadmin = authz.is_sysadmin(user)

    orgs_q = model.Session.query(model.Group) \
        .filter(model.Group.is_organization == True) \
        .filter(model.Group.state == 'active')

    if sysadmin:
        orgs_and_capacities = [(org, 'admin') for org in orgs_q.all()]
    else:
        # for non-Sysadmins check they have the required permission

        permission = data_dict.get('permission', 'manage_group')

        roles = authz.get_roles_with_permission(permission)

        if not roles:
            return []
        user_id = authz.get_user_id_for_username(user, allow_none=True)
        if not user_id:
            return []

        q = model.Session.query(model.Member, model.Group) \
            .filter(model.Member.table_name == 'user') \
            .filter(model.Member.capacity.in_(roles)) \
            .filter(model.Member.table_id == user_id) \
            .filter(model.Member.state == 'active') \
            .join(model.Group)

        group_ids = set()
        roles_that_cascade = \
            authz.check_config_permission('roles_that_cascade_to_sub_groups')
        group_ids_to_capacities = {}
        for member, group in q.all():
            if member.capacity in roles_that_cascade:
                children_group_ids = [
                    grp_tuple[0] for grp_tuple
                    in group.get_children_group_hierarchy(type='organization')
                ]
                for group_id in children_group_ids:
                    group_ids_to_capacities[group_id] = member.capacity
                group_ids |= set(children_group_ids)

            group_ids_to_capacities[group.id] = member.capacity
            group_ids.add(group.id)

        if not group_ids:
            return []

        orgs_q = orgs_q.filter(model.Group.id.in_(group_ids))
        orgs_and_capacities = [
            (org, group_ids_to_capacities[org.id]) for org in orgs_q.all()]

    context['with_capacity'] = True
    orgs_list = model_dictize.group_list_dictize(orgs_and_capacities, context,
        with_package_counts=asbool(data_dict.get('include_dataset_count')))
    return orgs_list


def _group_or_org_revision_list(context, data_dict):
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

    revision_dicts = []
    for revision, object_revisions in group.all_related_revisions:
        revision_dicts.append(model.revision_as_dict(revision,
                                                     include_packages=False,
                                                     include_groups=False))
    return revision_dicts


def group_revision_list(context, data_dict):
    '''Return a group's revisions.

    :param id: the name or id of the group
    :type id: string

    :rtype: list of dictionaries

    '''

    _check_access('group_revision_list', context, data_dict)
    return _group_or_org_revision_list(context, data_dict)


def organization_revision_list(context, data_dict):
    '''Return an organization's revisions.

    :param id: the name or id of the organization
    :type id: string

    :rtype: list of dictionaries

    '''

    _check_access('organization_revision_list', context, data_dict)
    return _group_or_org_revision_list(context, data_dict)


def license_list(context, data_dict):
    '''Return the list of licenses available for datasets on the site.

    :rtype: list of dictionaries

    '''
    model = context["model"]

    _check_access('license_list', context, data_dict)

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
    :type all_fields: bool

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
      ``'name'``). Can be any user field or ``edits`` (i.e. number_of_edits).
    :type order_by: string
    :param all_fields: return full user dictionaries instead of just names.
      (optional, default: ``True``)
    :type all_fields: bool

    :rtype: list of user dictionaries. User properties include:
      ``number_of_edits`` which counts the revisions by the user and
      ``number_created_packages`` which excludes datasets which are private
      or draft state.

    '''
    model = context['model']

    _check_access('user_list', context, data_dict)

    q = data_dict.get('q', '')
    order_by = data_dict.get('order_by', 'name')
    all_fields = asbool(data_dict.get('all_fields', True))

    if all_fields:
        query = model.Session.query(
            model.User,
            model.User.name.label('name'),
            model.User.fullname.label('fullname'),
            model.User.about.label('about'),
            model.User.about.label('email'),
            model.User.created.label('created'),
            _select(
                [_func.count(model.Revision.id)],
                model.Revision.author == model.User.name
            ).label('number_of_edits'),
            _select([_func.count(model.Package.id)],
                    _and_(
                        model.Package.creator_user_id == model.User.id,
                        model.Package.state == 'active',
                        model.Package.private == False,
                    )).label('number_created_packages')
        )
    else:
        query = model.Session.query(model.User.name)

    if q:
        query = model.User.search(q, query, user_name=context.get('user'))

    if order_by == 'edits':
        query = query.order_by(_desc(
            _select([_func.count(model.Revision.id)],
                    model.Revision.author == model.User.name)))
    else:
        query = query.order_by(
            _case([(
                _or_(model.User.fullname == None,
                     model.User.fullname == ''),
                model.User.name)],
                else_=model.User.fullname))

    # Filter deleted users
    query = query.filter(model.User.state != model.State.DELETED)

    ## hack for pagination
    if context.get('return_query'):
        return query

    users_list = []

    if all_fields:
        for user in query.all():
            result_dict = model_dictize.user_dictize(user[0], context)
            users_list.append(result_dict)
    else:
        for user in query.all():
            users_list.append(user[0])

    return users_list


def package_relationships_list(context, data_dict):
    '''Return a dataset (package)'s relationships.

    :param id: the id or name of the first package
    :type id: string
    :param id2: the id or name of the second package
    :type id2: string
    :param rel: relationship as string see
        :py:func:`~ckan.logic.action.create.package_relationship_create` for
        the relationship types (optional)

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

    _check_access('package_relationships_list', context, data_dict)

    # TODO: How to handle this object level authz?
    # Currently we don't care
    relationships = pkg1.get_relationships(with_package=pkg2, type=rel)

    if rel and not relationships:
        raise NotFound('Relationship "%s %s %s" not found.'
                       % (id, rel, id2))

    relationship_dicts = [
        rel.as_dict(pkg1, ref_package_by=ref_package_by)
        for rel in relationships]

    return relationship_dicts


def package_show(context, data_dict):
    '''Return the metadata of a dataset (package) and its resources.

    :param id: the id or name of the dataset
    :type id: string
    :param use_default_schema: use default package schema instead of
        a custom schema defined with an IDatasetForm plugin (default: ``False``)
    :type use_default_schema: bool
    :param include_tracking: add tracking information to dataset and
        resources (default: ``False``)
    :type include_tracking: bool
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

    if data_dict.get('use_default_schema', False):
        context['schema'] = ckan.logic.schema.default_show_package_schema()
    include_tracking = asbool(data_dict.get('include_tracking', False))

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
                package_json = search_result['validated_data_dict']
                package_dict = json.loads(package_json)
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

    if include_tracking:
        # page-view tracking summary data
        package_dict['tracking_summary'] = (
            model.TrackingSummary.get_for_package(package_dict['id']))

        for resource_dict in package_dict['resources']:
            _add_tracking_summary_to_resource_dict(resource_dict, model)

    if context.get('for_view'):
        for item in plugins.PluginImplementations(plugins.IPackageController):
            package_dict = item.before_view(package_dict)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.read(pkg)

    for item in plugins.PluginImplementations(plugins.IResourceController):
        for resource_dict in package_dict['resources']:
            item.before_show(resource_dict)

    if not package_dict_validated:
        package_plugin = lib_plugins.lookup_package_plugin(
            package_dict['type'])
        if 'schema' in context:
            schema = context['schema']
        else:
            schema = package_plugin.show_package_schema()
        if schema and context.get('validate', True):
            package_dict, errors = lib_plugins.plugin_validate(
                package_plugin, context, package_dict, schema,
                'package_show')

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
    :param include_tracking: add tracking information to dataset and
        resources (default: ``False``)
    :type include_tracking: bool

    :rtype: dictionary

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    resource = model.Resource.get(id)
    resource_context = dict(context, resource=resource)

    if not resource:
        raise NotFound

    _check_access('resource_show', resource_context, data_dict)

    pkg_dict = logic.get_action('package_show')(
        dict(context),
        {'id': resource.package.id,
        'include_tracking': asbool(data_dict.get('include_tracking', False))})

    for resource_dict in pkg_dict['resources']:
        if resource_dict['id'] == id:
            break
    else:
        log.error('Could not find resource %s after all', id)
        raise NotFound(_('Resource was not found.'))

    return resource_dict


def resource_view_show(context, data_dict):
    '''
    Return the metadata of a resource_view.

    :param id: the id of the resource_view
    :type id: string

    :rtype: dictionary
    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    resource_view = model.ResourceView.get(id)
    if not resource_view:
        _check_access('resource_view_show', context, data_dict)
        raise NotFound

    context['resource_view'] = resource_view
    context['resource'] = model.Resource.get(resource_view.resource_id)

    _check_access('resource_view_show', context, data_dict)
    return model_dictize.resource_view_dictize(resource_view, context)


def resource_view_list(context, data_dict):
    '''
    Return the list of resource views for a particular resource.

    :param id: the id of the resource
    :type id: string

    :rtype: list of dictionaries.
    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')
    resource = model.Resource.get(id)
    if not resource:
        raise NotFound
    context['resource'] = resource
    _check_access('resource_view_list', context, data_dict)
    q = model.Session.query(model.ResourceView).filter_by(resource_id=id)
    ## only show views when there is the correct plugin enabled
    resource_views = [
        resource_view for resource_view
        in q.order_by(model.ResourceView.order).all()
        if datapreview.get_view_plugin(resource_view.view_type)
    ]
    return model_dictize.resource_view_list_dictize(resource_views, context)


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

    if asbool(data_dict.get('include_datasets', False)):
        packages_field = 'datasets'
    elif asbool(data_dict.get('include_dataset_count', True)):
        packages_field = 'dataset_count'
    else:
        packages_field = None

    try:
        include_tags = asbool(data_dict.get('include_tags', True))
        if asbool(config.get('ckan.auth.public_user_details', True)):
            include_users = asbool(data_dict.get('include_users', True))
        else:
            include_users = asbool(data_dict.get('include_users', False))
        include_groups = asbool(data_dict.get('include_groups', True))
        include_extras = asbool(data_dict.get('include_extras', True))
        include_followers = asbool(data_dict.get('include_followers', True))
    except ValueError:
        raise logic.ValidationError(_('Parameter is not an bool'))

    if group is None:
        raise NotFound
    if is_org and not group.is_organization:
        raise NotFound
    if not is_org and group.is_organization:
        raise NotFound

    if is_org:
        _check_access('organization_show', context, data_dict)
    else:
        _check_access('group_show', context, data_dict)

    group_dict = model_dictize.group_dictize(group, context,
                                             packages_field=packages_field,
                                             include_tags=include_tags,
                                             include_extras=include_extras,
                                             include_groups=include_groups,
                                             include_users=include_users,)

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.read(group)

    group_plugin = lib_plugins.lookup_group_plugin(group_dict['type'])
    try:
        schema = group_plugin.db_to_form_schema_options({
            'type': 'show',
            'api': 'api_version' in context,
            'context': context})
    except AttributeError:
        schema = group_plugin.db_to_form_schema()

    if include_followers:
        group_dict['num_followers'] = logic.get_action('group_follower_count')(
            {'model': model, 'session': model.Session},
            {'id': group_dict['id']})
    else:
        group_dict['num_followers'] = 0

    if schema is None:
        schema = logic.schema.default_show_group_schema()
    group_dict, errors = lib_plugins.plugin_validate(
        group_plugin, context, group_dict, schema,
        'organization_show' if is_org else 'group_show')
    return group_dict


def group_show(context, data_dict):
    '''Return the details of a group.

    :param id: the id or name of the group
    :type id: string
    :param include_datasets: include a truncated list of the group's datasets
         (optional, default: ``False``)
    :type include_datasets: bool
    :param include_dataset_count: include the full package_count
         (optional, default: ``True``)
    :type include_dataset_count: bool
    :param include_extras: include the group's extra fields
         (optional, default: ``True``)
    :type include_extras: bool
    :param include_users: include the group's users
         (optional, default: ``True``)
    :type include_users: bool
    :param include_groups: include the group's sub groups
         (optional, default: ``True``)
    :type include_groups: bool
    :param include_tags: include the group's tags
         (optional, default: ``True``)
    :type include_tags: bool
    :param include_followers: include the group's number of followers
         (optional, default: ``True``)
    :type include_followers: bool

    :rtype: dictionary

    .. note:: Only its first 1000 datasets are returned

    '''
    return _group_or_org_show(context, data_dict)


def organization_show(context, data_dict):
    '''Return the details of a organization.

    :param id: the id or name of the organization
    :type id: string
    :param include_datasets: include a truncated list of the org's datasets
         (optional, default: ``False``)
    :type include_datasets: bool
    :param include_dataset_count: include the full package_count
         (optional, default: ``True``)
    :type include_dataset_count: bool
    :param include_extras: include the organization's extra fields
         (optional, default: ``True``)
    :type include_extras: bool
    :param include_users: include the organization's users
         (optional, default: ``True``)
    :type include_users: bool
    :param include_groups: include the organization's sub groups
         (optional, default: ``True``)
    :type include_groups: bool
    :param include_tags: include the organization's tags
         (optional, default: ``True``)
    :type include_tags: bool
    :param include_followers: include the organization's number of followers
         (optional, default: ``True``)
    :type include_followers: bool


    :rtype: dictionary

    .. note:: Only its first 1000 datasets are returned
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

    limit = data_dict.get('limit')
    if limit:
        try:
            limit = int(data_dict.get('limit'))
            if limit < 0:
                raise logic.ValidationError('Limit must be a positive integer')
        except ValueError:
            raise logic.ValidationError('Limit must be a positive integer')

    group = model.Group.get(group_id)
    context['group'] = group
    if group is None:
        raise NotFound

    _check_access('group_show', context, data_dict)

    result = logic.get_action('package_search')(context, {
        'fq': 'groups:{0}'.format(group.name),
        'rows': limit,
    })

    return result['results']


def tag_show(context, data_dict):
    '''Return the details of a tag and all its datasets.

    :param id: the name or id of the tag
    :type id: string
    :param vocabulary_id: the id or name of the tag vocabulary that the tag is
        in - if it is not specified it will assume it is a free tag.
        (optional)
    :type vocabulary_id: string
    :param include_datasets: include a list of the tag's datasets. (Up to a
        limit of 1000 - for more flexibility, use package_search - see
        :py:func:`package_search` for an example.)
        (optional, default: ``False``)
    :type include_datasets: bool

    :returns: the details of the tag, including a list of all of the tag's
        datasets and their details
    :rtype: dictionary
    '''

    model = context['model']
    id = _get_or_bust(data_dict, 'id')
    include_datasets = asbool(data_dict.get('include_datasets', False))

    tag = model.Tag.get(id, vocab_id_or_name=data_dict.get('vocabulary_id'))
    context['tag'] = tag

    if tag is None:
        raise NotFound

    _check_access('tag_show', context, data_dict)
    return model_dictize.tag_dictize(tag, context,
                                     include_datasets=include_datasets)


def user_show(context, data_dict):
    '''Return a user account.

    Either the ``id`` or the ``user_obj`` parameter must be given.

    :param id: the id or name of the user (optional)
    :type id: string
    :param user_obj: the user dictionary of the user (optional)
    :type user_obj: user dictionary
    :param include_datasets: Include a list of datasets the user has created.
        If it is the same user or a sysadmin requesting, it includes datasets
        that are draft or private.
        (optional, default:``False``, limit:50)
    :type include_datasets: bool
    :param include_num_followers: Include the number of followers the user has
        (optional, default:``False``)
    :type include_num_followers: bool
    :param include_password_hash: Include the stored password hash
        (sysadmin only, optional, default:``False``)
    :type include_password_hash: bool

    :returns: the details of the user. Includes email_hash, number_of_edits and
        number_created_packages (which excludes draft or private datasets
        unless it is the same user or sysadmin making the request). Excludes
        the password (hash) and reset_key. If it is the same user or a
        sysadmin requesting, the email and apikey are included.
    :rtype: dictionary

    '''
    model = context['model']

    id = data_dict.get('id', None)
    provided_user = data_dict.get('user_obj', None)
    if id:
        user_obj = model.User.get(id)
        context['user_obj'] = user_obj
        if user_obj is None:
            raise NotFound
    elif provided_user:
        context['user_obj'] = user_obj = provided_user
    else:
        raise NotFound

    _check_access('user_show', context, data_dict)

    # include private and draft datasets?
    requester = context.get('user')
    sysadmin = False
    if requester:
        sysadmin = authz.is_sysadmin(requester)
        requester_looking_at_own_account = requester == user_obj.name
        include_private_and_draft_datasets = (
            sysadmin or requester_looking_at_own_account)
    else:
        include_private_and_draft_datasets = False
    context['count_private_and_draft_datasets'] = \
        include_private_and_draft_datasets

    include_password_hash = sysadmin and asbool(
        data_dict.get('include_password_hash', False))

    user_dict = model_dictize.user_dictize(
        user_obj, context, include_password_hash)

    if context.get('return_minimal'):
        log.warning('Use of the "return_minimal" in user_show is '
                    'deprecated.')
        return user_dict

    if asbool(data_dict.get('include_datasets', False)):
        user_dict['datasets'] = []

        fq = "+creator_user_id:{0}".format(user_dict['id'])

        search_dict = {'rows': 50}

        if include_private_and_draft_datasets:
            search_dict.update({
                'include_private': True,
                'include_drafts': True})

        search_dict.update({'fq': fq})

        user_dict['datasets'] = \
            logic.get_action('package_search')(context=context,
                                               data_dict=search_dict) \
            .get('results')

    if asbool(data_dict.get('include_num_followers', False)):
        user_dict['num_followers'] = logic.get_action('user_follower_count')(
            {'model': model, 'session': model.Session},
            {'id': user_dict['id']})

    return user_dict


@logic.validate(logic.schema.default_autocomplete_schema)
def package_autocomplete(context, data_dict):
    '''Return a list of datasets (packages) that match a string.

    Datasets with names or titles that contain the query string will be
    returned.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of resource formats to return (optional,
        default: ``10``)
    :type limit: int

    :rtype: list of dictionaries

    '''
    model = context['model']

    _check_access('package_autocomplete', context, data_dict)

    limit = data_dict.get('limit', 10)
    q = data_dict['q']

    like_q = u"%s%%" % q

    query = model.Session.query(model.Package)
    query = query.filter(model.Package.state == 'active')
    query = query.filter(model.Package.private == False)
    query = query.filter(_or_(model.Package.name.ilike(like_q),
                              model.Package.title.ilike(like_q)))
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
        result_dict = {
            'name': package.name,
            'title': package.title,
            'match_field': match_field,
            'match_displayed': match_displayed}
        pkg_list.append(result_dict)

    return pkg_list


@logic.validate(logic.schema.default_autocomplete_schema)
def format_autocomplete(context, data_dict):
    '''Return a list of resource formats whose names contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of resource formats to return (optional,
        default: ``5``)
    :type limit: int

    :rtype: list of strings

    '''
    model = context['model']
    session = context['session']

    _check_access('format_autocomplete', context, data_dict)

    q = data_dict['q']
    limit = data_dict.get('limit', 5)

    like_q = u'%' + q + u'%'

    query = (session.query(
        model.Resource.format,
        _func.count(model.Resource.format).label('total'))
        .filter(_and_(
            model.Resource.state == 'active',
        ))
        .filter(model.Resource.format.ilike(like_q))
        .group_by(model.Resource.format)
        .order_by('total DESC')
        .limit(limit))

    return [resource.format.lower() for resource in query]


@logic.validate(logic.schema.default_autocomplete_schema)
def user_autocomplete(context, data_dict):
    '''Return a list of user names that contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of user names to return (optional,
        default: ``20``)
    :type limit: int

    :rtype: a list of user dictionaries each with keys ``'name'``,
        ``'fullname'``, and ``'id'``

    '''
    model = context['model']
    user = context['user']

    _check_access('user_autocomplete', context, data_dict)

    q = data_dict['q']
    limit = data_dict.get('limit', 20)

    query = model.User.search(q)
    query = query.filter(model.User.state != model.State.DELETED)
    query = query.limit(limit)

    user_list = []
    for user in query.all():
        result_dict = {}
        for k in ['id', 'name', 'fullname']:
            result_dict[k] = getattr(user, k)

        user_list.append(result_dict)

    return user_list


def _group_or_org_autocomplete(context, data_dict, is_org):

    q = data_dict['q']
    limit = data_dict.get('limit', 20)
    model = context['model']

    query = model.Group.search_by_name_or_title(q, group_type=None,
                                                is_org=is_org, limit=limit)

    group_list = []
    for group in query.all():
        result_dict = {}
        for k in ['id', 'name', 'title']:
            result_dict[k] = getattr(group, k)
        group_list.append(result_dict)

    return group_list


def group_autocomplete(context, data_dict):
    '''
    Return a list of group names that contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of groups to return (optional,
        default: 20)
    :type limit: int

    :rtype: a list of group dictionaries each with keys ``'name'``,
        ``'title'``, and ``'id'``
    '''

    _check_access('group_autocomplete', context, data_dict)

    return _group_or_org_autocomplete(context, data_dict, is_org=False)


def organization_autocomplete(context, data_dict):
    '''
    Return a list of organization names that contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of organizations to return (optional,
        default: ``20``)
    :type limit: int

    :rtype: a list of organization dictionaries each with keys ``'name'``,
        ``'title'``, and ``'id'``
    '''

    _check_access('organization_autocomplete', context, data_dict)

    return _group_or_org_autocomplete(context, data_dict, is_org=True)


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


    :param q: the solr query.  Optional.  Default: ``"*:*"``
    :type q: string
    :param fq: any filter queries to apply.  Note: ``+site_id:{ckan_site_id}``
        is added to this string prior to the query being executed.
    :type fq: string
    :param sort: sorting of the search results.  Optional.  Default:
        ``'relevance asc, metadata_modified desc'``.  As per the solr
        documentation, this is a comma-separated string of field names and
        sort-orderings.
    :type sort: string
    :param rows: the number of matching rows to return. There is a hard limit
        of 1000 datasets per query.
    :type rows: int
    :param start: the offset in the complete result for where the set of
        returned datasets should begin.
    :type start: int
    :param facet: whether to enable faceted results.  Default: ``True``.
    :type facet: string
    :param facet.mincount: the minimum counts for facet fields should be
        included in the results.
    :type facet.mincount: int
    :param facet.limit: the maximum number of values the facet fields return.
        A negative value means unlimited. This can be set instance-wide with
        the :ref:`search.facets.limit` config option. Default is 50.
    :type facet.limit: int
    :param facet.field: the fields to facet upon.  Default empty.  If empty,
        then the returned facet information is empty.
    :type facet.field: list of strings
    :param include_drafts: if ``True``, draft datasets will be included in the
        results. A user will only be returned their own draft datasets, and a
        sysadmin will be returned all draft datasets. Optional, the default is
        ``False``.
    :type include_drafts: bool
    :param include_private: if ``True``, private datasets will be included in
        the results. Only private datasets from the user's organizations will
        be returned and sysadmins will be returned all private datasets.
        Optional, the default is ``False``.
    :type include_private: bool
    :param use_default_schema: use default package schema instead of
        a custom schema defined with an IDatasetForm plugin (default: ``False``)
    :type use_default_schema: bool


    The following advanced Solr parameters are supported as well. Note that
    some of these are only available on particular Solr versions. See Solr's
    `dismax`_ and `edismax`_ documentation for further details on them:

    ``qf``, ``wt``, ``bf``, ``boost``, ``tie``, ``defType``, ``mm``


    .. _dismax: http://wiki.apache.org/solr/DisMaxQParserPlugin
    .. _edismax: http://wiki.apache.org/solr/ExtendedDisMax


    **Examples:**

    ``q=flood`` datasets containing the word `flood`, `floods` or `flooding`
    ``fq=tags:economy`` datasets with the tag `economy`
    ``facet.field=["tags"] facet.limit=10 rows=0`` top 10 tags

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
        query.
        fl can be  None or a list of result fields, such as ['id', 'extras_custom_field'].
        if fl = None, datasets are returned as a list of full dictionary.
    '''
    # sometimes context['schema'] is None
    schema = (context.get('schema') or
              logic.schema.default_package_search_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    # put the extras back into the data_dict so that the search can
    # report needless parameters
    data_dict.update(data_dict.get('__extras', {}))
    data_dict.pop('__extras', None)
    if errors:
        raise ValidationError(errors)

    model = context['model']
    session = context['session']
    user = context.get('user')

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

    results = []
    if not abort:
        if asbool(data_dict.get('use_default_schema')):
            data_source = 'data_dict'
        else:
            data_source = 'validated_data_dict'
        data_dict.pop('use_default_schema', None)

        result_fl = data_dict.get('fl')
        if not result_fl:
            data_dict['fl'] = 'id {0}'.format(data_source)
        else:
            data_dict['fl'] = ' '.join(result_fl)

        # Remove before these hit solr FIXME: whitelist instead
        include_private = asbool(data_dict.pop('include_private', False))
        include_drafts = asbool(data_dict.pop('include_drafts', False))
        data_dict.setdefault('fq', '')
        if not include_private:
            data_dict['fq'] = '+capacity:public ' + data_dict['fq']
        if include_drafts:
            data_dict['fq'] += ' +state:(active OR draft)'

        # Pop these ones as Solr does not need them
        extras = data_dict.pop('extras', None)

        # enforce permission filter based on user
        if context.get('ignore_auth') or (user and authz.is_sysadmin(user)):
            labels = None
        else:
            labels = lib_plugins.get_permission_labels(
                ).get_user_dataset_labels(context['auth_user_obj'])

        query = search.query_for(model.Package)
        query.run(data_dict, permission_labels=labels)

        # Add them back so extensions can use them on after_search
        data_dict['extras'] = extras

        if result_fl:
            for package in query.results:
                if package.get('extras'):
                    package.update(package['extras'] )
                    package.pop('extras')
                results.append(package)
        else:
            for package in query.results:
                # get the package object
                package_dict = package.get(data_source)
                ## use data in search index if there
                if package_dict:
                    # the package_dict still needs translating when being viewed
                    package_dict = json.loads(package_dict)
                    if context.get('for_view'):
                        for item in plugins.PluginImplementations(
                                plugins.IPackageController):
                            package_dict = item.before_view(package_dict)
                    results.append(package_dict)
                else:
                    log.error('No package_dict is coming from solr for package '
                              'id %s', package['id'])

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

    # create a lookup table of group name to title for all the groups and
    # organizations in the current search's facets.
    group_names = []
    for field_name in ('groups', 'organization'):
        group_names.extend(facets.get(field_name, {}).keys())

    groups = (session.query(model.Group.name, model.Group.title)
                    .filter(model.Group.name.in_(group_names))
                    .all()
              if group_names else [])
    group_titles_by_name = dict(groups)

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
                display_name = group_titles_by_name.get(key_, key_)
                display_name = display_name if display_name and display_name.strip() else key_
                new_facet_dict['display_name'] = display_name
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
        search_results = item.after_search(search_results, data_dict)

    # After extensions have had a chance to modify the facets, sort them by
    # display name.
    for facet in search_results['search_facets']:
        search_results['search_facets'][facet]['items'] = sorted(
            search_results['search_facets'][facet]['items'],
            key=lambda facet: facet['display_name'], reverse=True)

    return search_results


@logic.validate(logic.schema.default_resource_search_schema)
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
    :type query: string or list of strings of the form ``{field}:{term1}``
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
        if isinstance(query, string_types):
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
            if isinstance(terms, string_types):
                terms = terms.split()
            split_terms[field] = terms
        fields = split_terms

    order_by = data_dict.get('order_by')
    offset = data_dict.get('offset')
    limit = data_dict.get('limit')

    q = model.Session.query(model.Resource) \
         .join(model.Package) \
         .filter(model.Package.state == 'active') \
         .filter(model.Package.private == False) \
         .filter(model.Resource.state == 'active') \

    resource_fields = model.Resource.get_columns()
    for field, terms in fields.items():

        if isinstance(terms, string_types):
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
                q = q.filter(model_attr.ilike(text_type(term) + '%'))

            # Resource extras are stored in a json blob.  So searching for
            # matching fields is a bit trickier.  See the docstring.
            elif field in model.Resource.get_extra_columns():
                model_attr = getattr(model.Resource, 'extras')

                like = _or_(
                    model_attr.ilike(
                        u'''%%"%s": "%%%s%%",%%''' % (field, term)),
                    model_attr.ilike(
                        u'''%%"%s": "%%%s%%"}''' % (field, term))
                )
                q = q.filter(like)

            # Just a regular field
            else:
                q = q.filter(model_attr.ilike('%' + text_type(term) + '%'))

    if order_by is not None:
        if hasattr(model.Resource, order_by):
            q = q.order_by(getattr(model.Resource, order_by))

    count = q.count()
    q = q.offset(offset)
    q = q.limit(limit)

    results = []
    for result in q:
        if isinstance(result, tuple) \
                and isinstance(result[0], model.DomainObject):
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
    if isinstance(terms, string_types):
        terms = [terms]
    terms = [t.strip() for t in terms if t.strip()]

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
        escaped_term = misc.escape_sql_like_special_characters(
            term, escape='\\')
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
    :type task_type: string
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
                model.TaskStatus.entity_id
                == _get_or_bust(data_dict, 'entity_id'),
                model.TaskStatus.task_type
                == _get_or_bust(data_dict, 'task_type'),
                model.TaskStatus.key
                == _get_or_bust(data_dict, 'key')
            ))
        task_status = query.first()

    context['task_status'] = task_status

    _check_access('task_status_show', context, data_dict)

    if task_status is None:
        raise NotFound

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
    if isinstance(terms, string_types):
        terms = [terms]
    if terms:
        q = q.where(trans_table.c.term.in_(terms))

    # This action accepts `lang_codes` as either a list of strings, or a single
    # string.
    if 'lang_codes' in data_dict:
        lang_codes = _get_or_bust(data_dict, 'lang_codes')
        if isinstance(lang_codes, string_types):
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
    '''Return the ckan site user

    :param defer_commit: by default (or if set to false) get_site_user will
        commit and clean up the current transaction. If set to true, caller
        is responsible for commiting transaction after get_site_user is
        called. Leaving open connections can cause cli commands to hang!
        (optional, default: ``False``)
    :type defer_commit: bool
    '''
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
            model.repo.commit()

    return {'name': user.name,
            'apikey': user.apikey}


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
    _check_access('vocabulary_list', context, data_dict)

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
    _check_access('vocabulary_show', context, data_dict)

    model = context['model']
    vocab_id = data_dict.get('id')
    if not vocab_id:
        raise ValidationError({'id': _('id not in data')})
    vocabulary = model.vocabulary.Vocabulary.get(vocab_id)
    if vocabulary is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)
    vocabulary_dict = model_dictize.vocabulary_dictize(vocabulary, context)
    return vocabulary_dict


@logic.validate(logic.schema.default_activity_list_schema)
def user_activity_list(context, data_dict):
    '''Return a user's public activity stream.

    You must be authorized to view the user's profile.


    :param id: the id or name of the user
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _check_access('user_show', context, data_dict)

    model = context['model']

    user_ref = data_dict.get('id')  # May be user name or id.
    user = model.User.get(user_ref)
    if user is None:
        raise logic.NotFound

    offset = data_dict.get('offset', 0)
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    _activity_objects = model.activity.user_activity_list(user.id, limit=limit,
            offset=offset)
    activity_objects = _filter_activity_by_user(_activity_objects,
            _activity_stream_get_filtered_users())

    return model_dictize.activity_list_dictize(activity_objects, context)


@logic.validate(logic.schema.default_activity_list_schema)
def package_activity_list(context, data_dict):
    '''Return a package's activity stream.

    You must be authorized to view the package.

    :param id: the id or name of the package
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _check_access('package_show', context, data_dict)

    model = context['model']

    package_ref = data_dict.get('id')  # May be name or ID.
    package = model.Package.get(package_ref)
    if package is None:
        raise logic.NotFound

    offset = int(data_dict.get('offset', 0))
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    _activity_objects = model.activity.package_activity_list(package.id,
            limit=limit, offset=offset)
    activity_objects = _filter_activity_by_user(_activity_objects,
            _activity_stream_get_filtered_users())

    return model_dictize.activity_list_dictize(activity_objects, context)


@logic.validate(logic.schema.default_activity_list_schema)
def group_activity_list(context, data_dict):
    '''Return a group's activity stream.

    You must be authorized to view the group.

    :param id: the id or name of the group
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _check_access('group_show', context, data_dict)

    model = context['model']
    group_id = data_dict.get('id')
    offset = data_dict.get('offset', 0)
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    # Convert group_id (could be id or name) into id.
    group_show = logic.get_action('group_show')
    group_id = group_show(context, {'id': group_id})['id']

    _activity_objects = model.activity.group_activity_list(group_id,
            limit=limit, offset=offset)
    activity_objects = _filter_activity_by_user(_activity_objects,
            _activity_stream_get_filtered_users())

    return model_dictize.activity_list_dictize(activity_objects, context)


@logic.validate(logic.schema.default_activity_list_schema)
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
    org_id = data_dict.get('id')
    offset = data_dict.get('offset', 0)
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    # Convert org_id (could be id or name) into id.
    org_show = logic.get_action('organization_show')
    org_id = org_show(context, {'id': org_id})['id']

    _activity_objects = model.activity.group_activity_list(org_id,
            limit=limit, offset=offset)
    activity_objects = _filter_activity_by_user(_activity_objects,
            _activity_stream_get_filtered_users())

    return model_dictize.activity_list_dictize(activity_objects, context)


@logic.validate(logic.schema.default_pagination_schema)
def recently_changed_packages_activity_list(context, data_dict):
    '''Return the activity stream of all recently added or changed packages.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: list of dictionaries

    '''
    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    model = context['model']
    offset = data_dict.get('offset', 0)
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    _activity_objects = model.activity.recently_changed_packages_activity_list(
            limit=limit, offset=offset)
    activity_objects = _filter_activity_by_user(_activity_objects,
            _activity_stream_get_filtered_users())

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
    return model_dictize.activity_detail_list_dictize(
        activity_detail_objects, context)


def user_activity_list_html(context, data_dict):
    '''Return a user's public activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: The id or name of the user.
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
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
    return activity_streams.activity_list_to_html(
        context, activity_stream, extra_vars)


def package_activity_list_html(context, data_dict):
    '''Return a package's activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: the id or name of the package
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
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
    return activity_streams.activity_list_to_html(
        context, activity_stream, extra_vars)


def group_activity_list_html(context, data_dict):
    '''Return a group's activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: the id or name of the group
    :type id: string
    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
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
    return activity_streams.activity_list_to_html(
        context, activity_stream, extra_vars)


def organization_activity_list_html(context, data_dict):
    '''Return a organization's activity stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param id: the id or name of the organization
    :type id: string

    :rtype: string

    '''
    activity_stream = organization_activity_list(context, data_dict)
    offset = int(data_dict.get('offset', 0))
    extra_vars = {
        'controller': 'organization',
        'action': 'activity',
        'id': data_dict['id'],
        'offset': offset,
    }

    return activity_streams.activity_list_to_html(
        context, activity_stream, extra_vars)


def recently_changed_packages_activity_list_html(context, data_dict):
    '''Return the activity stream of all recently changed packages as HTML.

    The activity stream includes all recently added or changed packages. It is
    rendered as a snippet of HTML meant to be included in an HTML page, i.e. it
    doesn't have any HTML header or footer.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: string

    '''
    activity_stream = recently_changed_packages_activity_list(
        context, data_dict)
    offset = int(data_dict.get('offset', 0))
    extra_vars = {
        'controller': 'package',
        'action': 'activity',
        'offset': offset,
    }
    return activity_streams.activity_list_to_html(
        context, activity_stream, extra_vars)


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
    return _follower_count(
        context, data_dict,
        ckan.logic.schema.default_follow_user_schema(),
        context['model'].UserFollowingUser)


def dataset_follower_count(context, data_dict):
    '''Return the number of followers of a dataset.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: int

    '''
    return _follower_count(
        context, data_dict,
        ckan.logic.schema.default_follow_dataset_schema(),
        context['model'].UserFollowingDataset)


def group_follower_count(context, data_dict):
    '''Return the number of followers of a group.

    :param id: the id or name of the group
    :type id: string

    :rtype: int

    '''
    return _follower_count(
        context, data_dict,
        ckan.logic.schema.default_follow_group_schema(),
        context['model'].UserFollowingGroup)


def organization_follower_count(context, data_dict):
    '''Return the number of followers of an organization.

    :param id: the id or name of the organization
    :type id: string

    :rtype: int

    '''
    return group_follower_count(context, data_dict)


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
    return _follower_list(
        context, data_dict,
        ckan.logic.schema.default_follow_user_schema(),
        context['model'].UserFollowingUser)


def dataset_follower_list(context, data_dict):
    '''Return the list of users that are following the given dataset.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('dataset_follower_list', context, data_dict)
    return _follower_list(
        context, data_dict,
        ckan.logic.schema.default_follow_dataset_schema(),
        context['model'].UserFollowingDataset)


def group_follower_list(context, data_dict):
    '''Return the list of users that are following the given group.

    :param id: the id or name of the group
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('group_follower_list', context, data_dict)
    return _follower_list(
        context, data_dict,
        ckan.logic.schema.default_follow_group_schema(),
        context['model'].UserFollowingGroup)


def organization_follower_list(context, data_dict):
    '''Return the list of users that are following the given organization.

    :param id: the id or name of the organization
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('organization_follower_list', context, data_dict)
    return _follower_list(
        context, data_dict,
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

    :rtype: bool

    '''
    return _am_following(
        context, data_dict,
        ckan.logic.schema.default_follow_user_schema(),
        context['model'].UserFollowingUser)


def am_following_dataset(context, data_dict):
    '''Return ``True`` if you're following the given dataset, ``False`` if not.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: bool

    '''
    return _am_following(
        context, data_dict,
        ckan.logic.schema.default_follow_dataset_schema(),
        context['model'].UserFollowingDataset)


def am_following_group(context, data_dict):
    '''Return ``True`` if you're following the given group, ``False`` if not.

    :param id: the id or name of the group
    :type id: string

    :rtype: bool

    '''
    return _am_following(
        context, data_dict,
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
    return _followee_count(
        context, data_dict,
        context['model'].UserFollowingUser)


def dataset_followee_count(context, data_dict):
    '''Return the number of datasets that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    '''
    return _followee_count(
        context, data_dict,
        context['model'].UserFollowingDataset)


def group_followee_count(context, data_dict):
    '''Return the number of groups that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    '''
    return _followee_count(
        context, data_dict,
        context['model'].UserFollowingGroup)


@logic.validate(logic.schema.default_follow_user_schema)
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

    :rtype: list of dictionaries, each with keys ``'type'`` (e.g. ``'user'``,
        ``'dataset'`` or ``'group'``), ``'display_name'`` (e.g. a user's
        display name, or a package's title) and ``'dict'`` (e.g. a dict
        representing the followed user, package or group, the same as the dict
        that would be returned by :py:func:`user_show`,
        :py:func:`package_show` or :py:func:`group_show`)

    '''
    _check_access('followee_list', context, data_dict)

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
            (group_followee_list, 'group'),
            (organization_followee_list, 'organization')):
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
    datasets = [model.Package.get(followee.object_id)
                for followee in followees]
    datasets = [dataset for dataset in datasets if dataset is not None]

    # Dictize the list of Package objects.
    return [model_dictize.package_dictize(dataset, context)
            for dataset in datasets]


def group_followee_list(context, data_dict):
    '''Return the list of groups that are followed by the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    '''
    _check_access('group_followee_list', context, data_dict)

    return _group_or_org_followee_list(context, data_dict, is_org=False)


def organization_followee_list(context, data_dict):
    '''Return the list of organizations that are followed by the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    '''

    _check_access('organization_followee_list', context, data_dict)

    return _group_or_org_followee_list(context, data_dict, is_org=True)


def _group_or_org_followee_list(context, data_dict, is_org=False):

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
    groups = [group for group in groups
              if group is not None and group.is_organization == is_org]

    # Dictize the list of Group objects.
    return [model_dictize.group_dictize(group, context) for group in groups]


@logic.validate(logic.schema.default_pagination_schema)
def dashboard_activity_list(context, data_dict):
    '''Return the authorized (via login or API key) user's dashboard activity
       stream.

    Unlike the activity dictionaries returned by other ``*_activity_list``
    actions, these activity dictionaries have an extra boolean value with key
    ``is_new`` that tells you whether the activity happened since the user last
    viewed her dashboard (``'is_new': True``) or not (``'is_new': False``).

    The user's own activities are always marked ``'is_new': False``.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
        :ref:`ckan.activity_list_limit` setting)
    :type limit: int

    :rtype: list of activity dictionaries

    '''
    _check_access('dashboard_activity_list', context, data_dict)

    model = context['model']
    user_id = model.User.get(context['user']).id
    offset = data_dict.get('offset', 0)
    limit = int(
        data_dict.get('limit', config.get('ckan.activity_list_limit', 31)))

    # FIXME: Filter out activities whose subject or object the user is not
    # authorized to read.
    _activity_objects = model.activity.dashboard_activity_list(user_id,
            limit=limit, offset=offset)

    activity_objects = _filter_activity_by_user(_activity_objects,
            _activity_stream_get_filtered_users())
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
            activity['is_new'] = (
                strptime(activity['timestamp'], fmt) > last_viewed)

    return activity_dicts


@logic.validate(ckan.logic.schema.default_pagination_schema)
def dashboard_activity_list_html(context, data_dict):
    '''Return the authorized (via login or API key) user's dashboard activity
       stream as HTML.

    The activity stream is rendered as a snippet of HTML meant to be included
    in an HTML page, i.e. it doesn't have any HTML header or footer.

    :param offset: where to start getting activity items from
        (optional, default: ``0``)
    :type offset: int
    :param limit: the maximum number of activities to return
        (optional, default: ``31``, the default value is configurable via the
        ckan.activity_list_limit setting)
    :type limit: int

    :rtype: string

    '''
    activity_stream = dashboard_activity_list(context, data_dict)
    model = context['model']
    user_id = context['user']
    offset = data_dict.get('offset', 0)
    extra_vars = {
        'controller': 'user',
        'action': 'dashboard',
        'offset': offset,
        'id': user_id
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

    :param group_type: the group type, either ``"group"`` or ``"organization"``
        (optional, default ``"organization"``)
    :type group_type: string
    :returns: a list of dictionaries each with two keys: ``"text"`` (the
        display name of the role, e.g. ``"Admin"``) and ``"value"`` (the
        internal name of the role, e.g. ``"admin"``)
    :rtype: list of dictionaries

    '''
    group_type = data_dict.get('group_type', 'organization')
    roles_list = authz.roles_list()
    if group_type == 'group':
        roles_list = [role for role in roles_list
                      if role['value'] != 'editor']

    _check_access('member_roles_list', context, data_dict)
    return roles_list


def help_show(context, data_dict):
    '''Return the help string for a particular API action.

    :param name: Action function name (eg `user_create`, `package_search`)
    :type name: string
    :returns: The help string for the action function, or None if the function
              does not have a docstring.
    :rtype: string

    :raises: :class:`ckan.logic.NotFound`: if the action function doesn't exist

    '''

    function_name = logic.get_or_bust(data_dict, 'name')

    _check_access('help_show', context, data_dict)

    try:
        function = logic.get_action(function_name)
    except KeyError:
        raise NotFound('Action function not found')

    return function.__doc__


def config_option_show(context, data_dict):
    '''Show the current value of a particular configuration option.

    Only returns runtime-editable config options (the ones returned by
    :py:func:`~ckan.logic.action.get.config_option_list`), which can be updated with the
    :py:func:`~ckan.logic.action.update.config_option_update` action.

    :param key: The configuration option key
    :type key: string

    :returns: The value of the config option from either the system_info table
        or ini file.
    :rtype: string

    :raises: :class:`ckan.logic.ValidationError`: if config option is not in
        the schema (whitelisted as editable).
    '''

    _check_access('config_option_show', context, data_dict)

    key = _get_or_bust(data_dict, 'key')

    schema = ckan.logic.schema.update_configuration_schema()

    # Only return whitelisted keys
    if key not in schema:
        raise ValidationError(
            'Configuration option \'{0}\' can not be shown'.format(key))

    # return the value from config
    return config.get(key, None)


def config_option_list(context, data_dict):
    '''Return a list of runtime-editable config options keys that can be
       updated with :py:func:`~ckan.logic.action.update.config_option_update`.

    :returns: A list of config option keys.
    :rtype: list
    '''

    _check_access('config_option_list', context, data_dict)

    schema = ckan.logic.schema.update_configuration_schema()

    return schema.keys()


@logic.validate(logic.schema.job_list_schema)
def job_list(context, data_dict):
    '''List enqueued background jobs.

    :param list queues: Queues to list jobs from. If not given then the
        jobs from all queues are listed.

    :returns: The currently enqueued background jobs.
    :rtype: list

    .. versionadded:: 2.7
    '''
    _check_access(u'job_list', context, data_dict)
    dictized_jobs = []
    queues = data_dict.get(u'queues')
    if queues:
        queues = [jobs.get_queue(q) for q in queues]
    else:
        queues = jobs.get_all_queues()
    for queue in queues:
        for job in queue.jobs:
            dictized_jobs.append(jobs.dictize_job(job))
    return dictized_jobs


def job_show(context, data_dict):
    '''Show details for a background job.

    :param string id: The ID of the background job.

    :returns: Details about the background job.
    :rtype: dict

    .. versionadded:: 2.7
    '''
    _check_access(u'job_show', context, data_dict)
    id = _get_or_bust(data_dict, u'id')
    try:
        return jobs.dictize_job(jobs.job_from_id(id))
    except KeyError:
        raise NotFound
