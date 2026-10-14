
from __future__ import annotations

import datetime
import json
import socket
import logging
from copy import deepcopy
from typing import Any, cast

import ckan
import ckan.authz as authz
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions as dfunc
import ckan.logic.schema as schema_
import ckan.lib.plugins as lib_plugins
import ckan.lib.search as search
import ckan.lib.uploader as uploader
import ckan.logic as logic
import ckan.model as model
import ckan.model as model_
import ckan.plugins as plugins
import six
from ckan.common import _, asbool, config
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.lib.search.query import solr_literal
from ckan.logic import (
    NotAuthorized,
    NotFound,
    ValidationError,
    check_access as _check_access,
    fresh_context,
    get_action as _get_action,
    get_or_bust as _get_or_bust,
    side_effect_free,
)
from ckan.types import ActionResult, Context, DataDict, Schema
from sqlalchemy import and_ as _and_
from sqlalchemy.sql import select as _select

log = logging.getLogger('ckan.logic')


def package_create(
        context: Context, data_dict: DataDict) -> ActionResult.PackageCreate:
    '''Create a new dataset (package).

    You must be authorized to create new datasets. If you specify any groups
    for the new dataset, you must also be authorized to edit these groups.

    Plugins may change the parameters of this function depending on the value
    of the ``type`` parameter, see the
    :py:class:`~ckan.plugins.interfaces.IDatasetForm` plugin interface.

    :param name: the name of the new dataset, must be between 2 and 100
        characters long and contain only lowercase alphanumeric characters,
        ``-`` and ``_``, e.g. ``'warandpeace'``
    :type name: string
    :param title: the title of the dataset (optional, default: same as
        ``name``)
    :type title: string
    :param private: If ``True`` creates a private dataset
    :type private: bool
    :param author: the name of the dataset's author (optional)
    :type author: string
    :param author_email: the email address of the dataset's author (optional)
    :type author_email: string
    :param maintainer: the name of the dataset's maintainer (optional)
    :type maintainer: string
    :param maintainer_email: the email address of the dataset's maintainer
        (optional)
    :type maintainer_email: string
    :param license_id: the id of the dataset's license, see
        :py:func:`~ckan.logic.action.get.license_list` for available values
        (optional)
    :type license_id: license id string
    :param notes: a description of the dataset (optional)
    :type notes: string
    :param url: a URL for the dataset's source (optional)
    :type url: string
    :param version: (optional)
    :type version: string, no longer than 100 characters
    :param state: the current state of the dataset, e.g. ``'active'`` or
        ``'deleted'``, only active datasets show up in search results and
        other lists of datasets, this parameter will be ignored if you are not
        authorized to change the state of the dataset (optional, default:
        ``'active'``)
    :type state: string
    :param type: the type of the dataset (optional),
        :py:class:`~ckan.plugins.interfaces.IDatasetForm` plugins
        associate themselves with different dataset types and provide custom
        dataset handling behaviour for these types
    :type type: string
    :param resources: the dataset's resources, see
        :py:func:`resource_create` for the format of resource dictionaries
        (optional)
    :type resources: list of resource dictionaries
    :param tags: the dataset's tags, see :py:func:`tag_create` for the format
        of tag dictionaries (optional)
    :type tags: list of tag dictionaries
    :param extras: the dataset's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to datasets, each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string)
    :type extras: list of dataset extra dictionaries
    :param plugin_data: private package data belonging to plugins.
        Only sysadmin users may set this value. It should be a dict that can
        be dumped into JSON, and plugins should namespace their data with the
        plugin name to avoid collisions with other plugins, eg::

            {
                "name": "test-dataset",
                "plugin_data": {
                    "plugin1": {"key1": "value1"},
                    "plugin2": {"key2": "value2"}
                }
            }
    :type plugin_data: dict
    :param relationships_as_object: see :py:func:`package_relationship_create`
        for the format of relationship dictionaries (optional)
    :type relationships_as_object: list of relationship dictionaries
    :param relationships_as_subject: see :py:func:`package_relationship_create`
        for the format of relationship dictionaries (optional)
    :type relationships_as_subject: list of relationship dictionaries
    :param groups: the groups to which the dataset belongs (optional), each
        group dictionary should have one or more of the following keys which
        identify an existing group:
        ``'id'`` (the id of the group, string), or ``'name'`` (the name of the
        group, string),  to see which groups exist
        call :py:func:`~ckan.logic.action.get.group_list`
    :type groups: list of dictionaries
    :param owner_org: the id of the dataset's owning organization, see
        :py:func:`~ckan.logic.action.get.organization_list` or
        :py:func:`~ckan.logic.action.get.organization_list_for_user` for
        available values. This parameter can be made optional if the config
        option :ref:`ckan.auth.create_unowned_dataset` is set to ``True``.
    :type owner_org: string

    :returns: the newly created dataset (unless 'return_id_only' is set to True
              in the context, in which case just the dataset id will
              be returned)
    :rtype: dictionary

    '''
    user = context['user']

    if 'type' not in data_dict:
        package_plugin = lib_plugins.lookup_package_plugin()
        try:
            # use first type as default if user didn't provide type
            package_type = package_plugin.package_types()[0]
        except (AttributeError, IndexError):
            package_type = 'dataset'
            # in case a 'dataset' plugin was registered w/o fallback
            package_plugin = lib_plugins.lookup_package_plugin(package_type)
        data_dict['type'] = package_type
    else:
        package_plugin = lib_plugins.lookup_package_plugin(data_dict['type'])

    schema: Schema = context.get(
        'schema') or package_plugin.create_package_schema()

    _check_access('package_create', context, data_dict)

    data, errors = lib_plugins.plugin_validate(
        package_plugin, context, data_dict, schema, 'package_create')
    log.debug('package_create validate_errs=%r user=%s package=%s data=%r',
              errors, context.get('user'),
              data.get('name'), data_dict)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    plugin_data = data.get('plugin_data', False)
    include_plugin_data = False
    if user:
        user_obj = model.User.by_name(six.ensure_text(user))
        if user_obj:
            data['creator_user_id'] = user_obj.id
            include_plugin_data = user_obj.sysadmin and plugin_data

    pkg, _change = model_save.package_dict_save(
        data, context, include_plugin_data)

    # Needed to let extensions know the package and resources ids
    model.Session.flush()
    data['id'] = pkg.id
    if data.get('resources'):
        for index, resource in enumerate(data['resources']):
            resource['id'] = pkg.resources[index].id

    if not data.get('metadata_modified'):
        pkg.metadata_modified = datetime.datetime.utcnow()

    context_org_update = context.copy()
    context_org_update['ignore_auth'] = True
    context_org_update['defer_commit'] = True
    _get_action('package_owner_org_update')(context_org_update,
                                            {'id': pkg.id,
                                             'organization_id': pkg.owner_org})

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.create(pkg)

        item.after_dataset_create(context, data)

    # Create default views for resources if necessary
    if data.get('resources'):
        logic.get_action('package_create_default_resource_views')(
            fresh_context(context, ignore_auth=True),
            {'package': data})

    return_id_only = context.get('return_id_only', False)

    if return_id_only and context.get('defer_commit'):
        return pkg.id

    pkg_default, pkg_custom = logic.package_show_default_and_custom_schemas(
        context, pkg.id)

    if not context.get('defer_commit'):
        logic.index_insert_package_dicts((pkg_default, pkg_custom))
        model.repo.commit()

    if return_id_only:
        return pkg.id

    return pkg_custom


def package_relationship_create(
        context: Context,
        data_dict: DataDict) -> ActionResult.PackageRelationshipCreate:
    '''Create a relationship between two datasets (packages).

    You must be authorized to edit both the subject and the object datasets.

    :param subject: the id or name of the dataset that is the subject of the
        relationship
    :type subject: string
    :param object: the id or name of the dataset that is the object of the
        relationship
    :param type: the type of the relationship, one of ``'depends_on'``,
        ``'dependency_of'``, ``'derives_from'``, ``'has_derivation'``,
        ``'links_to'``, ``'linked_from'``, ``'child_of'`` or ``'parent_of'``
    :type type: string
    :param comment: a comment about the relationship (optional)
    :type comment: string

    :returns: the newly created package relationship
    :rtype: dictionary

    '''
    schema = context.get('schema') \
        or ckan.logic.schema.default_create_relationship_schema()
    api = context.get('api_version')
    ref_package_by = 'id' if api == 2 else 'name'

    id, id2, rel_type = _get_or_bust(data_dict, ['subject', 'object', 'type'])
    comment = data_dict.get('comment', u'')

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('Subject package %r was not found.' % id)
    if not pkg2:
        raise NotFound('Object package %r was not found.' % id2)

    _data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    _check_access('package_relationship_create', context, data_dict)

    # Create a Package Relationship.
    existing_rels = pkg1.get_relationships_with(pkg2, rel_type)
    if existing_rels:
        return _update_package_relationship(existing_rels[0],
                                            comment, context)
    rel = pkg1.add_relationship(rel_type, pkg2, comment=comment)
    if not context.get('defer_commit'):
        model.repo.commit_and_remove()
    context['relationship'] = rel

    relationship_dicts = rel.as_dict(ref_package_by=ref_package_by)
    return relationship_dicts


def package_collaborator_create(
        context: Context,
        data_dict: DataDict) -> ActionResult.PackageCollaboratorCreate:
    '''Make a user a collaborator in a dataset.

    If the user is already a collaborator in the dataset then their
    capacity will be updated.

    Currently you must be an Admin on the dataset owner organization to
    manage collaborators.

    Note: This action requires the collaborators feature to be enabled with
    the :ref:`ckan.auth.allow_dataset_collaborators` configuration option.

    :param id: the id or name of the dataset
    :type id: string
    :param user_id: the id or name of the user to add or edit
    :type user_id: string
    :param capacity: the capacity or role of the membership. Must be one of
        "editor" or "member". Additionally
        if :ref:`ckan.auth.allow_admin_collaborators` is set to True, "admin"
        is also allowed.
    :type capacity: string

    :returns: the newly created (or updated) collaborator
    :rtype: dictionary
    '''
    package_id, user_id, capacity = _get_or_bust(
        data_dict,
        ['id', 'user_id', 'capacity']
    )

    allowed_capacities = authz.get_collaborator_capacities()
    if capacity not in allowed_capacities:
        raise ValidationError({
            'message': _('Role must be one of "{}"').format(', '.join(
                allowed_capacities))})

    _check_access('package_collaborator_create', context, data_dict)

    package = model.Package.get(package_id)
    if not package:
        raise NotFound(_('Dataset not found'))

    user = model.User.get(user_id)
    if not user:
        raise NotFound(_('User not found'))

    if not authz.check_config_permission('allow_dataset_collaborators'):
        raise ValidationError({
            'message': _('Dataset collaborators not enabled')})

    # Check if collaborator already exists
    collaborator = model.Session.query(model.PackageMember). \
        filter(model.PackageMember.package_id == package.id). \
        filter(model.PackageMember.user_id == user.id).one_or_none()
    if not collaborator:
        collaborator = model.PackageMember(
            package_id=package.id,
            user_id=user.id)
    collaborator.capacity = capacity
    collaborator.modified = datetime.datetime.utcnow()
    model.Session.add(collaborator)
    model.repo.commit()

    log.info('User %s added as collaborator in package %s (%s)',
             user.name, package.id, capacity)

    return model_dictize.member_dictize(collaborator, context)


@side_effect_free
@logic.validate(ckan.logic.schema.default_pagination_schema)
def package_list(context: Context, data_dict: DataDict) -> ActionResult.PackageList:
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
    api = context.get("api_version", 1)

    _check_access('package_list', context, data_dict)

    package_table = model.package_table
    col = (package_table.c["id"]
           if api == 2 else package_table.c["name"])
    query = _select(col)
    query = query.where(_and_(
        package_table.c["state"] == 'active',
        package_table.c["private"] == False,
    ))
    query = query.order_by(col)

    limit = data_dict.get('limit')
    if limit:
        query = query.limit(limit)

    offset = data_dict.get('offset')
    if offset:
        query = query.offset(offset)

    ## Returns the first field in each result record
    return context["session"].scalars(
        query
    ).all()


@side_effect_free
@logic.validate(ckan.logic.schema.default_package_list_schema)
def current_package_list_with_resources(
        context: Context, data_dict: DataDict) -> ActionResult.CurrentPackageListWithResources:
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


@side_effect_free
def package_collaborator_list(context: Context,
                              data_dict: DataDict) -> ActionResult.PackageCollaboratorList:
    '''Return the list of all collaborators for a given package.

    Currently you must be an Admin on the package owner organization to
    manage collaborators.

    Note: This action requires the collaborators feature to be enabled with
    the :ref:`ckan.auth.allow_dataset_collaborators` configuration option.

    :param id: the id or name of the package
    :type id: string
    :param capacity: (optional) If provided, only users with this capacity are
        returned
    :type capacity: string

    :returns: a list of collaborators, each a dict including the package and
        user id, the capacity and the last modified date
    :rtype: list of dictionaries

    '''
    package_id = _get_or_bust(data_dict, 'id')

    package = model.Package.get(package_id)
    if not package:
        raise NotFound(_('Package not found'))

    _check_access('package_collaborator_list', context, data_dict)

    if not authz.check_config_permission('allow_dataset_collaborators'):
        raise ValidationError({
            'message': _('Dataset collaborators not enabled')
        })

    capacity = data_dict.get('capacity')

    allowed_capacities = authz.get_collaborator_capacities()
    if capacity and capacity not in allowed_capacities:
        raise ValidationError(
            {'message': _('Capacity must be one of "{}"').format(', '.join(
                allowed_capacities))})
    q = model.Session.query(model.PackageMember).\
        filter(model.PackageMember.package_id == package.id)

    if capacity:
        q = q.filter(model.PackageMember.capacity == capacity)

    collaborators = q.all()

    return [collaborator.as_dict() for collaborator in collaborators]


@side_effect_free
def package_collaborator_list_for_user(
        context: Context, data_dict: DataDict) -> ActionResult.PackageCollaboratorListForUser:
    '''Return a list of all package the user is a collaborator in

    Note: This action requires the collaborators feature to be enabled with
    the :ref:`ckan.auth.allow_dataset_collaborators` configuration option.

    :param id: the id or name of the user
    :type id: string
    :param capacity: (optional) If provided, only packages where the user
        has this capacity are returned
    :type capacity: string

    :returns: a list of packages, each a dict including the package id, the
        capacity and the last modified date
    :rtype: list of dictionaries

    '''
    user_id = _get_or_bust(data_dict, 'id')

    if not authz.check_config_permission('allow_dataset_collaborators'):
        raise ValidationError({
            'message': _('Dataset collaborators not enabled')})

    _check_access('package_collaborator_list_for_user', context, data_dict)

    user = model.User.get(user_id)
    if not user:
        raise NotAuthorized(_('Not allowed to retrieve collaborators'))

    capacity = data_dict.get('capacity')
    allowed_capacities = authz.get_collaborator_capacities()
    if capacity and capacity not in allowed_capacities:
        raise ValidationError(
            {'message': _('Capacity must be one of "{}"').format(', '.join(
            allowed_capacities))})

    q = model.Session.query(model.PackageMember).\
        filter(model.PackageMember.user_id == user.id)

    if capacity:
        q = q.filter(model.PackageMember.capacity == capacity)

    collaborators = q.all()

    out: list[dict[str, str]] = []
    for collaborator in collaborators:
        out.append({
            'package_id': collaborator.package_id,
            'capacity': collaborator.capacity,
            'modified': collaborator.modified.isoformat(),
        })

    return out


@side_effect_free
def license_list(context: Context, data_dict: DataDict) -> ActionResult.LicenseList:
    '''Return the list of licenses available for datasets on the site.

    :rtype: list of dictionaries

    '''
    _check_access('license_list', context, data_dict)

    license_register = model.Package.get_license_register()
    licenses = license_register.values()
    licenses = [l.license_dictize() for l in licenses]
    return licenses


@side_effect_free
def package_relationships_list(context: Context,
                               data_dict: DataDict) -> ActionResult.PackageRelationshipsList:
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


@side_effect_free
def package_show(context: Context, data_dict: DataDict) -> ActionResult.PackageShow:
    '''Return the metadata of a dataset (package) and its resources.

    :param id: the id or name of the dataset
    :type id: string
    :param use_default_schema: use default package schema instead of
        a custom schema defined with an IDatasetForm plugin (default: ``False``)
    :param include_plugin_data: Include the internal plugin data object
        (sysadmin only, optional, default:``False``)
    :type: include_plugin_data: bool
    :rtype: dictionary

    '''
    user_obj = context.get('auth_user_obj')
    context['session'] = model.Session
    name_or_id = data_dict.get("id") or _get_or_bust(data_dict, 'name_or_id')

    include_plugin_data = asbool(data_dict.get('include_plugin_data', False))
    if user_obj and user_obj.is_authenticated:
        include_plugin_data = (
            user_obj.sysadmin  # type: ignore
            and include_plugin_data
        )

        if include_plugin_data:
            context['use_cache'] = False

    pkg = model.Package.get(
        name_or_id,
        for_update=context.get('for_update', False))

    if pkg is None:
        raise NotFound

    context['package'] = pkg
    _check_access('package_show', context, data_dict)

    if asbool(data_dict.get('use_default_schema', False)):
        context['schema'] = ckan.logic.schema.default_show_package_schema()

    package_dict = None
    use_cache = (context.get('use_cache', True))
    package_dict_validated = False

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
            # solr stores less precise datetime,
            # truncate to 22 characters to get good enough match
            if metadata_modified[:22] != search_metadata_modified[:22]:
                package_dict = None

    if not package_dict:
        package_dict = model_dictize.package_dictize(
            pkg, context, include_plugin_data
        )
        package_dict_validated = False

    if context.get('for_view'):
        for item in plugins.PluginImplementations(plugins.IPackageController):
            package_dict = item.before_dataset_view(package_dict)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.read(pkg)

    for item in plugins.PluginImplementations(plugins.IResourceController):
        for resource_dict in package_dict['resources']:
            item.before_resource_show(resource_dict)

    if not package_dict_validated:
        package_plugin = lib_plugins.lookup_package_plugin(
            package_dict['type'])
        schema = context.get('schema') or package_plugin.show_package_schema()

        if bool(schema) and context.get('validate', True):
            package_dict, _errors = lib_plugins.plugin_validate(
                package_plugin, context, package_dict, schema,
                'package_show')
        else:
            # up to caller to apply after_dataset_show plugins
            return package_dict

    logic.apply_after_dataset_show_plugins(context, package_dict)
    return package_dict


@side_effect_free
@logic.validate(ckan.logic.schema.default_autocomplete_schema)
def package_autocomplete(
        context: Context, data_dict: DataDict) -> ActionResult.PackageAutocomplete:
    '''Return a list of datasets (packages) that match a string.

    Datasets with names or titles that contain the query string will be
    returned.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of datasets to return (optional,
        default: ``10``)
    :type limit: int

    :rtype: list of dictionaries

    '''
    _check_access('package_autocomplete', context, data_dict)
    user = context.get('user')

    limit = data_dict.get('limit', 10)
    q = data_dict['q']

    # enforce permission filter based on user
    if context.get('ignore_auth') or (user and authz.is_sysadmin(user)):
        labels = None
    else:
        labels = lib_plugins.get_permission_labels().get_user_dataset_labels(
            context['auth_user_obj']
        )

    data_dict = {
        'q': ' OR '.join([
            'name_ngram:{0}',
            'title_ngram:{0}',
            'name:{0}',
            'title:{0}',
        ]).format(solr_literal(q)),
        'fl': 'name,title',
        'rows': limit
    }
    query = search.query_for(model.Package)

    results = query.run(data_dict, permission_labels=labels)['results']

    q_lower = q.lower()
    pkg_list: ActionResult.PackageAutocomplete = []
    for package in results:
        if q_lower in package['name']:
            match_field = 'name'
            match_displayed = package['name']
        else:
            match_field = 'title'
            match_displayed = '%s (%s)' % (package['title'], package['name'])
        result_dict: dict[str, Any] = {
            'name': package['name'],
            'title': package['title'],
            'match_field': match_field,
            'match_displayed': match_displayed}
        pkg_list.append(result_dict)

    return pkg_list


@side_effect_free
def package_search(context: Context, data_dict: DataDict) -> ActionResult.PackageSearch:
    '''
    Searches for packages satisfying a given search criteria.

    This action accepts solr search query parameters (details below), and
    returns a dictionary of results, including dictized datasets that match
    the search criteria, a search count and also facet information.

    **Solr Parameters:**

    For more in depth treatment of each parameter, please read the
    `Solr Documentation
    <https://lucene.apache.org/solr/guide/6_6/common-query-parameters.html>`_.

    This action accepts a *subset* of solr's search query parameters:


    :param q: the solr query.  Optional.  Default: ``"*:*"``
    :type q: string
    :param fq: any filter queries to apply.  Note: ``+site_id:{ckan_site_id}``
        is added to this string prior to the query being executed.
    :type fq: string
    :param fq_list: additional filter queries to apply.
    :type fq_list: list of strings
    :param sort: sorting of the search results.  Optional.  Default:
        ``'score desc, metadata_modified desc'``.  As per the solr
        documentation, this is a comma-separated string of field names and
        sort-orderings.
    :type sort: string
    :param rows: the maximum number of matching rows (datasets) to return.
        (optional, default: ``10``, upper limit: ``1000`` unless set in
        site's configuration ``ckan.search.rows_max``)
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
    :param include_deleted: if ``True``, deleted datasets will be included in the
        results (site configuration "ckan.search.remove_deleted_packages" must
        be set to False). Optional, the default is ``False``.
    :type include_deleted: bool
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
        fl can be  None or a list of result fields, such as
        ['id', 'extras_custom_field'].
        if fl = None, datasets are returned as a list of full dictionary.
    '''
    # sometimes context['schema'] is None
    schema = (context.get('schema') or
              ckan.logic.schema.default_package_search_schema())
    data_dict, errors = _validate(data_dict, schema, context)
    # put the extras back into the data_dict so that the search can
    # report needless parameters
    data_dict.update(data_dict.get('__extras', {}))
    data_dict.pop('__extras', None)
    if errors:
        raise ValidationError(errors)

    session = context['session']
    user = context.get('user')

    _check_access('package_search', context, data_dict)

    # Move ext_ params to extras and remove them from the root of the search
    # params, so they don't cause and error
    data_dict['extras'] = data_dict.get('extras', {})
    for key in [key for key in data_dict.keys() if key.startswith('ext_')]:
        data_dict['extras'][key] = data_dict.pop(key)

    # set default search field
    data_dict['df'] = 'text'

    # check if some extension needs to modify the search params
    for item in plugins.PluginImplementations(plugins.IPackageController):
        data_dict = item.before_dataset_search(data_dict)

    # the extension may have decided that it is not necessary to perform
    # the query
    abort = data_dict.get('abort_search', False)

    if data_dict.get('sort') in (None, 'rank'):
        data_dict['sort'] = config.get('ckan.search.default_package_sort')

    results: list[dict[str, Any]] = []
    facets: dict[str, Any] = {}
    count = 0

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

        data_dict.setdefault('fq', '')

        # Remove before these hit solr FIXME: whitelist instead
        include_private = asbool(data_dict.pop('include_private', False))
        include_drafts = asbool(data_dict.pop('include_drafts', False))
        include_deleted = asbool(data_dict.pop('include_deleted', False))

        if not include_private:
            data_dict['fq'] = '+capacity:public ' + data_dict['fq']

        if '+state' not in data_dict['fq']:
            states = ['active']
            if include_drafts:
                states.append('draft')
            if include_deleted:
                states.append('deleted')
            data_dict['fq'] += ' +state:({})'.format(' OR '.join(states))

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
                if isinstance(package, str):
                    package = {result_fl[0]: package}
                extras = cast("dict[str, Any]", package.pop('extras', {}))
                package.update(extras)
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
                            package_dict = item.before_dataset_view(
                                package_dict)
                    results.append(package_dict)
                else:
                    log.error('No package_dict is coming from solr for package '
                              'id %s', package['id'])

        count = query.count
        facets = query.facets

    search_results: dict[str, Any] = {
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
    group_titles_by_name = {
        row[0]: row[1]
        for row in groups
    }

    # Transform facets into a more useful data structure.
    restructured_facets: dict[str, Any] = {}
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
                display_name = display_name \
                    if display_name and display_name.strip() else key_
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
        search_results = item.after_dataset_search(search_results, data_dict)

    # After extensions have had a chance to modify the facets, sort them by
    # display name.
    for facet in search_results['search_facets']:
        search_results['search_facets'][facet]['items'] = sorted(
            search_results['search_facets'][facet]['items'],
            key=lambda facet: facet['display_name'], reverse=True)

    return search_results


def package_reindex(
        context: Context, data_dict: DataDict) -> None:
    '''Rebuild the search index for a dataset (package).

    You must be authorized to edit the dataset
    and the group(s) it belongs to.

    :param id: the name or id of the dataset to reindex
    :type id: string
    '''
    name_or_id = data_dict.get('id') or data_dict.get('name')
    if name_or_id is None:
        raise ValidationError({'id': _('Missing value')})

    pkg = model.Package.get(name_or_id)
    if pkg is None:
        raise NotFound(_('Package was not found.'))

    data_dict = {"id": pkg.id}

    _check_access('package_reindex', context, data_dict)

    logic.index_update_package(context, pkg.id)


def package_update(
        context: Context, data_dict: DataDict) -> ActionResult.PackageUpdate:
    '''Update a dataset (package).

    You must be authorized to edit the dataset and the groups that it belongs
    to.

    .. note:: Update methods may delete parameters not explicitly provided.
        If you want to edit only a specific attribute use
        :py:func:`ckan.logic.action.get.package_patch` instead.

    If the ``resources`` list is omitted the current resources will be left
    unchanged.

    Plugins may change the parameters of this function depending on the value
    of the dataset's ``type`` attribute, see the
    :py:class:`~ckan.plugins.interfaces.IDatasetForm` plugin interface.

    For further parameters see
    :py:func:`~ckan.logic.action.create.package_create`.

    :param id: the name or id of the dataset to update
    :type id: string

    :returns: the updated dataset (if ``'return_id_only'`` is ``False`` in
              the context, which is the default. Otherwise returns just the
              dataset id)
    :rtype: dictionary

    '''
    name_or_id = data_dict.get('id') or data_dict.get('name')
    if name_or_id is None:
        raise ValidationError({'id': _('Missing value')})

    pkg = model.Package.get(name_or_id)
    if pkg is None:
        raise NotFound(_('Package was not found.'))
    context["package"] = pkg

    # immutable fields
    data_dict["id"] = pkg.id
    data_dict['type'] = pkg.type

    _check_access('package_update', context, data_dict)

    user = context['user']
    # get the schema

    package_plugin = lib_plugins.lookup_package_plugin(pkg.type)
    schema = context.get('schema') or package_plugin.update_package_schema()

    # try to do less work
    return_id_only = context.get('return_id_only', False)
    original_package = context.get('original_package')
    copy_resources = {}
    changed_resources = data_dict.get('resources')
    dataset_changed = True

    if not original_package or original_package.get('id') != pkg.id:
        show_context = logic.fresh_context(context, ignore_auth=True)
        original_package = _get_action('package_show')(show_context, {
            'id': data_dict['id'],
        })

    if data_dict.get('metadata_modified'):
        dataset_changed = original_package != data_dict
    else:
        dataset_changed = dict(
            original_package, metadata_modified=None, resources=None
            ) != dict(data_dict, metadata_modified=None, resources=None)
    if not dataset_changed and original_package.get('resources') \
            == data_dict.get('resources'):
        return pkg.id if return_id_only else original_package

    res_deps = []
    if hasattr(package_plugin, 'resource_validation_dependencies'):
        res_deps = package_plugin.resource_validation_dependencies(
            pkg.type)

    _missing = object()
    if 'resources' in data_dict and all(
            original_package.get(rd, _missing) == data_dict.get(rd, _missing)
            for rd in res_deps):
        oids = {r['id']: r for r in original_package['resources']}
        copy_resources = {
            i: r['position']
            for (i, r) in enumerate(data_dict['resources'])
            if r == oids.get(r.get('id'), ())
        }
        changed_resources = [
            r for i, r in enumerate(data_dict['resources'])
            if i not in copy_resources
        ]

    if 'resources' not in data_dict and any(
            original_package.get(rd, _missing) != data_dict.get(rd, _missing)
            for rd in res_deps):
        # re-validate resource fields even if not passed
        changed_resources = original_package['resources']

    resource_uploads = []
    for resource in changed_resources or []:
        # file uploads/clearing
        upload = uploader.get_resource_uploader(resource)

        if 'mimetype' not in resource:
            if hasattr(upload, 'mimetype'):
                resource['mimetype'] = upload.mimetype

        if 'url_type' in resource:
            if hasattr(upload, 'filesize'):
                resource['size'] = upload.filesize

        resource_uploads.append(upload)

    validate_data = dict(data_dict)
    if changed_resources is not None:
        validate_data['resources'] = changed_resources

    data, errors = lib_plugins.plugin_validate(
        package_plugin,
        context,
        validate_data,
        schema,
        'package_update'
    )
    # shift resource errors to the correct positions
    if copy_resources and 'resources' in errors:
        rerrs = []
        i = 0
        for e in errors['resources']:
            while i in copy_resources:
                rerrs.append({})
                i += 1
            rerrs.append(e)
            i += 1
        errors['resources'] = rerrs
    log.debug('package_update validate_errs=%r user=%s package=%s data=%r',
              errors, user, context['package'].name, data)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    # merge skipped resources back into validated data
    if copy_resources:
        assert original_package  # make pyright happy
        resources = []
        i = 0
        for r in data['resources']:
            while i in copy_resources:
                resources.append(
                    original_package['resources'][copy_resources[i]])
                i += 1
            resources.append(r)
            i += 1
        while i in copy_resources:
            resources.append(
                original_package['resources'][copy_resources[i]])
            i += 1
        data['resources'] = resources

    include_plugin_data = False
    user_obj = context.get('auth_user_obj')
    if user_obj:
        plugin_data = data.get('plugin_data', False)
        include_plugin_data = (
            user_obj.sysadmin  # type: ignore
            and plugin_data
        )

    nested = model.repo.session.begin_nested()
    pkg, change = model_save.package_dict_save(
        data, context, include_plugin_data, copy_resources)

    if change:
        if not data.get('metadata_modified'):
            pkg.metadata_modified = datetime.datetime.utcnow()

        context_org_update = logic.fresh_context(
            context, ignore_auth=True, defer_commit=True)
        _get_action('package_owner_org_update')(context_org_update,
                                                {'id': pkg.id,
                                                 'organization_id': pkg.owner_org})

        # Needed to let extensions know the new resources ids
        model.Session.flush()
        if changed_resources:
            resiter = iter(changed_resources)
            uploaditer = iter(resource_uploads)
            for i in range(len(pkg.resources)):
                if i in copy_resources:
                    continue
                resource = next(resiter)
                upload = next(uploaditer)
                resource['id'] = pkg.resources[i].id

                upload.upload(resource['id'], uploader.get_max_resource_size())

        for item in plugins.PluginImplementations(plugins.IPackageController):
            item.edit(pkg)

            item.after_dataset_update(context, data)

    return_id_only = context.get('return_id_only', False)

    if return_id_only and context.get('defer_commit'):
        return pkg.id

    pkg_default, pkg_custom = logic.package_show_default_and_custom_schemas(
        context, pkg.id)

    if not context.get('defer_commit'):
        logic.index_update_package_dicts((pkg_default, pkg_custom))

        nested.commit()
        if not context.get('defer_commit'):
            model.repo.commit()

        # return ids of changed entities via context because return value is
        # the action's "result" data
        context.setdefault(
            'changed_entities', {}
        ).setdefault(
            'packages', set()
        ).add(pkg.id)
        log.debug('Updated object %s', pkg.name)
    else:
        log.debug('No update for object %s', pkg.name)
        nested.rollback()

    if return_id_only:
        return pkg.id

    if not change and original_package:
        return original_package

    return pkg_custom


def package_revise(context: Context, data_dict: DataDict) -> ActionResult.PackageRevise:
    '''Revise a dataset (package) selectively with match, filter and
    update parameters.

    You must be authorized to edit the dataset and the groups that it belongs
    to.

    :param match: a dict containing "id" or "name" values of the dataset
                  to update, all values provided must match the current
                  dataset values or a ValidationError will be raised. e.g.
                  ``{"name": "my-data", "resources": {["name": "big.csv"]}}``
                  would abort if the my-data dataset's first resource name
                  is not "big.csv".
    :type match: dict
    :param filter: a list of string patterns of fields to remove from the
                   current dataset. e.g. ``"-resources__1"`` would remove the
                   second resource, ``"+title, +resources, -*"`` would
                   remove all fields at the dataset level except title and
                   all resources (default: ``[]``)
    :type filter: comma-separated string patterns or list of string patterns
    :param update: a dict with values to update/create after filtering
                   e.g. ``{"resources": [{"description": "file here"}]}`` would
                   update the description for the first resource
    :type update: dict
    :param include: a list of string pattern of fields to include in response
                    e.g. ``"-*"`` to return nothing (default: ``[]`` all
                    fields returned)
    :type include: comma-separated-string patterns or list of string patterns

    ``match`` and ``update`` parameters may also be passed as "flattened keys", using
    either the item numeric index or its unique id (with a minimum of 5 characters), e.g.
    ``update__resources__1f9ab__description="guidebook"`` would set the
    description of the resource with id starting with "1f9ab" to "guidebook", and
    ``update__resources__-1__description="guidebook"`` would do the same
    on the last resource in the dataset.

    The ``extend`` suffix can also be used on the update parameter to add
    a new item to a list, e.g. ``update__resources__extend=[{"name": "new resource", "url": "https://example.com"}]``
    will add a new resource to the dataset with the provided ``name`` and ``url``.

    Usage examples:

    * Change description in dataset, checking for old description::

        match={"notes": "old notes", "name": "xyz"}
        update={"notes": "new notes"}

    * Identical to above, but using flattened keys::

        match__name="xyz"
        match__notes="old notes"
        update__notes="new notes"

    * Replace all fields at dataset level only, keep resources (note: dataset id
      and type fields can't be deleted) ::

        match={"id": "1234abc-1420-cbad-1922"}
        filter=["+resources", "-*"]
        update={"name": "fresh-start", "title": "Fresh Start"}

    * Add a new resource (__extend on flattened key)::

        match={"id": "abc0123-1420-cbad-1922"}
        update__resources__extend=[{"name": "new resource", "url": "http://example.com"}]

    * Update a resource by its index::

        match={"name": "my-data"}
        update__resources__0={"name": "new name, first resource"}

    * Update a resource by its id (provide at least 5 characters)::

        match={"name": "their-data"}
        update__resources__19cfad={"description": "right one for sure"}

    * Replace all fields of a resource::

        match={"id": "34a12bc-1420-cbad-1922"}
        filter=["+resources__1492a__id", "-resources__1492a__*"]
        update__resources__1492a={"name": "edits here", "url": "http://example.com"}


    :returns: a dict containing 'package':the updated dataset with fields filtered by include parameter
    :rtype: dictionary

    '''
    schema = schema_.package_revise_schema()
    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    name_or_id = (
        data['match__'].get('id') or
        data.get('match', {}).get('id') or
        data['match__'].get('name') or
        data.get('match', {}).get('name'))
    if name_or_id is None:
        raise ValidationError({'match__id': _('Missing value')})

    package_show_context = Context(context)
    package_show_context['for_update'] = True
    orig = _get_action('package_show')(
        package_show_context,
        {'id': name_or_id})

    unmatched = []
    if 'match' in data:
        unmatched.extend(dfunc.check_dict(orig, data['match']))

    for k, v in sorted(data['match__'].items()):
        unmatched.extend(dfunc.check_string_key(orig, k, v))

    if unmatched:
        model.Session.rollback()
        raise ValidationError({'match': [
            '__'.join(str(p) for p in unm)
            for unm in unmatched
        ]})

    revised = deepcopy(orig)
    # allow metadata_modified to be updated if data has changed
    revised.pop('metadata_modified', None)

    if 'filter' in data:
        dfunc.filter_glob_match(revised, data['filter'])
        revised['id'] = orig['id']

    if 'update' in data:
        try:
            dfunc.update_merge_dict(revised, data['update'])
        except dfunc.DataError as de:
            model.Session.rollback()
            raise ValidationError({'update': [de.error]})

    # update __extend keys before __#__* so that files may be
    # attached to newly added resources in the same call
    for k, v in sorted(
            data['update__'].items(),
            key=lambda s: s[0][-6] if s[0].endswith('extend') else s[0]):
        try:
            dfunc.update_merge_string_key(revised, k, v)
        except dfunc.DataError as de:
            model.Session.rollback()
            raise ValidationError({k: [de.error]})

    _check_access('package_revise', context, {"update": revised})

    update_context = Context(context)
    update_context['original_package'] = orig

    # future-proof return dict by putting package data under
    # "package". We will want to return activity info
    # on update or "nothing changed" status once possible
    rval = {
        'package': _get_action('package_update')(update_context, revised)}
    if 'include' in data_dict:
        dfunc.filter_glob_match(rval, data_dict['include'])
    return rval


def package_patch(
        context: Context, data_dict: DataDict) -> ActionResult.PackagePatch:
    '''Patch a dataset (package).

    :param id: the id or name of the dataset
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict.

    To partially update resources or other metadata not at the top level
    of a package use
    :py:func:`~ckan.logic.action.update.package_revise` instead to maintain
    existing nested values.

    You must be authorized to edit the dataset and the groups that it belongs
    to.
    '''
    _check_access('package_patch', context, data_dict)

    show_context: Context = {
        'session': context['session'],
        'user': context['user'],
        'auth_user_obj': context['auth_user_obj'],
        'ignore_auth': context.get('ignore_auth', False),
        'for_update': True
    }

    package_dict = _get_action('package_show')(
        show_context,
        {'id': _get_or_bust(data_dict, 'id')})

    patched = dict(package_dict)
    # allow metadata_modified to be updated if data has changed
    patched.pop('metadata_modified', None)

    patched.update(data_dict)
    patched['id'] = package_dict['id']
    update_context = Context(context)
    update_context['original_package'] = package_dict
    return _get_action('package_update')(update_context, patched)
    

def _update_package_relationship(
        relationship: 'model_.PackageRelationship', comment: str,
        context: Context) -> dict[str, Any]:
    api = context.get('api_version')
    ref_package_by = 'id' if api == 2 else 'name'
    is_changed = relationship.comment != comment
    if is_changed:
        relationship.comment = comment
        if not context.get('defer_commit'):
            model.repo.commit_and_remove()
    rel_dict = relationship.as_dict(package=relationship.subject,
                                    ref_package_by=ref_package_by)
    return rel_dict


def package_relationship_update(
        context: Context, data_dict: DataDict) -> ActionResult.PackageRelationshipUpdate:
    '''Update a relationship between two datasets (packages).

    The subject, object and type parameters are required to identify the
    relationship. Only the comment can be updated.

    You must be authorized to edit both the subject and the object datasets.

    :param subject: the name or id of the dataset that is the subject of the
        relationship
    :type subject: string
    :param object: the name or id of the dataset that is the object of the
        relationship
    :type object: string
    :param type: the type of the relationship, one of ``'depends_on'``,
        ``'dependency_of'``, ``'derives_from'``, ``'has_derivation'``,
        ``'links_to'``, ``'linked_from'``, ``'child_of'`` or ``'parent_of'``
    :type type: string
    :param comment: a comment about the relationship (optional)
    :type comment: string

    :returns: the updated relationship
    :rtype: dictionary

    '''
    schema = context.get('schema') \
        or schema_.default_update_relationship_schema()

    id, id2, rel = _get_or_bust(data_dict, ['subject', 'object', 'type'])

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound(_('Subject package %s was not found.') % repr(id))
    if not pkg2:
        raise NotFound(_('Object package %s was not found.') % repr(id2))

    _data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    _check_access('package_relationship_update', context, data_dict)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound(_('This relationship between the packages was not found.'))
    entity = existing_rels[0]
    comment = data_dict.get('comment', u'')
    context['relationship'] = entity
    return _update_package_relationship(entity, comment, context)


def package_owner_org_update(context: Context, data_dict: DataDict) -> ActionResult.PackageOwnerOrgUpdate:
    '''Update the owning organization of a dataset

    :param id: the name or id of the dataset to update
    :type id: string

    :param organization_id: the name or id of the owning organization
    :type organization_id: string
    '''
    name_or_id = data_dict.get('id', '')
    organization_id = data_dict.get('organization_id')

    _check_access('package_owner_org_update', context, data_dict)

    pkg = model.Package.get(name_or_id)
    if pkg is None:
        raise NotFound(_('Package was not found.'))
    if organization_id:
        org = model.Group.get(organization_id)
        if org is None or not org.is_organization:
            raise NotFound(_('Organization was not found.'))

        # FIXME check we are in that org
        pkg.owner_org = org.id
    else:
        org = None
        pkg.owner_org = None

    members = model.Session.query(model.Member) \
        .filter(model.Member.table_id == pkg.id) \
        .filter(model.Member.capacity == 'organization')

    need_update = True
    for member_obj in members:
        if org and member_obj.group_id == org.id:
            need_update = False
        else:
            member_obj.state = 'deleted'
            model.Session.add(member_obj)

    # add the organization to member table
    if org and need_update:
        member_obj = model.Member(table_id=pkg.id,
                                  table_name='package',
                                  group=org,
                                  capacity='organization',
                                  group_id=org.id,
                                  state='active')
        model.Session.add(member_obj)

    if not context.get('defer_commit'):
        model.Session.commit()


def _bulk_update_dataset(
        context: Context, data_dict: DataDict, update_dict: dict[Any, Any]):
    ''' Bulk update shared code for organizations'''

    datasets = data_dict.get('datasets', [])
    org_id = data_dict.get('org_id')

    dataset_ids = model.Session.query(model.Package.id) \
        .filter(
            model.Package.id.in_(datasets)
        ) .filter(model.Package.owner_org == org_id)

    for d in dataset_ids:
        _get_action('package_patch')(
            logic.fresh_context(context),
            dict(update_dict, id=d),
        )


def bulk_update_private(context: Context, data_dict: DataDict) -> ActionResult.BulkUpdatePrivate:
    ''' Make a list of datasets private

    :param datasets: list of ids of the datasets to update
    :type datasets: list of strings

    :param org_id: id of the owning organization
    :type org_id: string
    '''

    _check_access('bulk_update_private', context, data_dict)
    _bulk_update_dataset(context, data_dict, {'private': True})


def bulk_update_public(context: Context, data_dict: DataDict) -> ActionResult.BulkUpdatePublic:
    ''' Make a list of datasets public

    :param datasets: list of ids of the datasets to update
    :type datasets: list of strings

    :param org_id: id of the owning organization
    :type org_id: string
    '''

    _check_access('bulk_update_public', context, data_dict)
    _bulk_update_dataset(context, data_dict, {'private': False})


def bulk_update_delete(context: Context, data_dict: DataDict) -> ActionResult.BulkUpdateDelete:
    ''' Make a list of datasets deleted

    :param datasets: list of ids of the datasets to update
    :type datasets: list of strings

    :param org_id: id of the owning organization
    :type org_id: string
    '''

    _check_access('bulk_update_delete', context, data_dict)
    _bulk_update_dataset(context, data_dict, {'state': 'deleted'})


def package_delete(context: Context, data_dict: DataDict) -> ActionResult.PackageDelete:
    '''Delete a dataset (package).

    This makes the dataset disappear from all web & API views, apart from the
    trash.

    You must be authorized to delete the dataset.

    :param id: the id or name of the dataset to delete
    :type id: string

    '''
    id = _get_or_bust(data_dict, 'id')

    entity = model.Package.get(id)

    if entity is None:
        raise NotFound

    _check_access('package_delete', context, data_dict)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.delete(entity)

        item.after_dataset_delete(context, data_dict)

    entity.delete()

    dataset_memberships = model.Session.query(model.Member).filter(
        model.Member.table_id == id).filter(
        model.Member.state == 'active').all()

    for membership in dataset_memberships:
        membership.delete()

    dataset_collaborators = model.Session.query(model.PackageMember).filter(
        model.PackageMember.package_id == id).all()
    for collaborator in dataset_collaborators:
        collaborator.delete()

    ckan.logic.index_update_package(context, id)
    model.repo.commit()


def dataset_purge(context: Context, data_dict: DataDict) -> ActionResult.DatasetPurge:
    '''Purge a dataset.

    .. warning:: Purging a dataset cannot be undone!

    Purging a dataset completely removes the dataset from the CKAN database,
    whereas deleting a dataset simply marks the dataset as deleted (it will no
    longer show up in the front-end, but is still in the db).

    You must be authorized to purge the dataset.

    :param id: the name or id of the dataset to be purged
    :type id: string

    '''
    from sqlalchemy import or_

    id = _get_or_bust(data_dict, 'id')

    pkg = model.Package.get(id)
    if pkg is None:
        raise NotFound('Dataset was not found')
    context['package'] = pkg

    _check_access('dataset_purge', context, data_dict)

    members = model.Session.query(model.Member) \
                   .filter(model.Member.table_id == pkg.id) \
                   .filter(model.Member.table_name == 'package')
    if members.count() > 0:
        for m in members.all():
            m.purge()

    for r in model.Session.query(model.PackageRelationship).filter(
            or_(model.PackageRelationship.subject_package_id == pkg.id,
                model.PackageRelationship.object_package_id == pkg.id)).all():
        r.purge()

    pkg = model.Package.get(id)
    assert pkg

    ckan.logic.index_remove_package(id)

    pkg.purge()
    model.repo.commit_and_remove()


def package_relationship_delete(context: Context, data_dict: DataDict) -> ActionResult.PackageRelationshipDelete:
    '''Delete a dataset (package) relationship.

    You must be authorised to delete dataset relationships, and to edit both
    the subject and the object datasets.

    :param subject: the id or name of the dataset that is the subject of the
        relationship
    :type subject: string
    :param object: the id or name of the dataset that is the object of the
        relationship
    :type object: string
    :param type: the type of the relationship
    :type type: string

    '''
    id, id2, rel = _get_or_bust(data_dict, ['subject', 'object', 'type'])

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('Subject package %r was not found.' % id)
    if not pkg2:
        raise NotFound('Object package %r was not found.' % id2)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound

    relationship = existing_rels[0]

    context['relationship'] = relationship
    _check_access('package_relationship_delete', context, data_dict)

    relationship.delete()
    model.repo.commit()


def package_collaborator_delete(context: Context, data_dict: DataDict) -> ActionResult.PackageCollaboratorDelete:
    '''Remove a collaborator from a dataset.

    Currently you must be an Admin on the dataset owner organization to
    manage collaborators.

    Note: This action requires the collaborators feature to be enabled with
    the :ref:`ckan.auth.allow_dataset_collaborators` configuration option.

    :param id: the id or name of the dataset
    :type id: string
    :param user_id: the id or name of the user to remove
    :type user_id: string

    '''
    package_id, user_id = _get_or_bust(
        data_dict,
        ['id', 'user_id']
    )

    _check_access('package_collaborator_delete', context, data_dict)

    if not authz.check_config_permission('allow_dataset_collaborators'):
        raise ValidationError({
            'message': _('Dataset collaborators not enabled')})

    package = model.Package.get(package_id)
    if not package:
        raise NotFound(_('Package not found'))

    user = model.User.get(user_id)
    if not user:
        raise NotFound(_('User not found'))

    collaborator = model.Session.query(model.PackageMember).\
        filter(model.PackageMember.package_id == package.id).\
        filter(model.PackageMember.user_id == user.id).one_or_none()
    if not collaborator:
        raise NotFound(
            'User {} is not a collaborator on this package'.format(user_id))

    model.Session.delete(collaborator)
    model.repo.commit()

    log.info('User %s removed as collaborator from package %s',
        user_id, package.id)
