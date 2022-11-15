# encoding: utf-8

'''API functions for adding data to CKAN.'''

import logging
import random
import re
from socket import error as socket_error
import datetime

import six

import ckan.common
from sqlalchemy import func

import ckan.lib.plugins as lib_plugins
import ckan.logic as logic
import ckan.plugins as plugins
import ckan.lib.dictization
import ckan.logic.action
import ckan.logic.schema
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions
import ckan.lib.uploader as uploader
import ckan.lib.mailer as mailer
import ckan.lib.datapreview
import ckan.lib.api_token as api_token
import ckan.authz as authz

from ckan.common import _, config

# FIXME this looks nasty and should be shared better
from ckan.logic.action.update import _update_package_relationship

log = logging.getLogger(__name__)

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_validate = ckan.lib.navl.dictization_functions.validate
_check_access = logic.check_access
_get_action = logic.get_action
ValidationError = logic.ValidationError
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
_get_or_bust = logic.get_or_bust


def package_create(context, data_dict):
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
    model = context['model']
    session = context['session']
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

    if 'schema' in context:
        schema = context['schema']
    else:
        schema = package_plugin.create_package_schema()

    _check_access('package_create', context, data_dict)

    if 'api_version' not in context:
        # check_data_dict() is deprecated. If the package_plugin has a
        # check_data_dict() we'll call it, if it doesn't have the method we'll
        # do nothing.
        check_data_dict = getattr(package_plugin, 'check_data_dict', None)
        if check_data_dict:
            try:
                check_data_dict(data_dict, schema)
            except TypeError:
                # Old plugins do not support passing the schema so we need
                # to ensure they still work
                package_plugin.check_data_dict(data_dict)

    data, errors = lib_plugins.plugin_validate(
        package_plugin, context, data_dict, schema, 'package_create')
    log.debug('package_create validate_errs=%r user=%s package=%s data=%r',
              errors, context.get('user'),
              data.get('name'), data_dict)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    if user:

        user_obj = model.User.by_name(six.ensure_text(user))
        if user_obj:
            data['creator_user_id'] = user_obj.id

    pkg = model_save.package_dict_save(data, context)

    # Needed to let extensions know the package and resources ids
    model.Session.flush()
    data['id'] = pkg.id
    if data.get('resources'):
        for index, resource in enumerate(data['resources']):
            resource['id'] = pkg.resources[index].id

    context_org_update = context.copy()
    context_org_update['ignore_auth'] = True
    context_org_update['defer_commit'] = True
    _get_action('package_owner_org_update')(context_org_update,
                                            {'id': pkg.id,
                                             'organization_id': pkg.owner_org})

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.create(pkg)

        item.after_create(context, data)

    # Make sure that a user provided schema is not used in create_views
    # and on package_show
    context.pop('schema', None)

    # Create default views for resources if necessary
    if data.get('resources'):
        logic.get_action('package_create_default_resource_views')(
            {'model': context['model'], 'user': context['user'],
             'ignore_auth': True},
            {'package': data})

    # Create activity
    if not pkg.private:
        user_obj = model.User.by_name(user)
        if user_obj:
            user_id = user_obj.id
        else:
            user_id = 'not logged in'

        activity = pkg.activity_stream_item('new', user_id)
        session.add(activity)

    if not context.get('defer_commit'):
        model.repo.commit()

    return_id_only = context.get('return_id_only', False)

    if return_id_only:
        return pkg.id

    return _get_action('package_show')(
        context.copy(), {'id': pkg.id}
    )


def resource_create(context, data_dict):
    '''Appends a new resource to a datasets list of resources.

    :param package_id: id of package that the resource should be added to.

    :type package_id: string
    :param url: url of resource
    :type url: string
    :param description: (optional)
    :type description: string
    :param format: (optional)
    :type format: string
    :param hash: (optional)
    :type hash: string
    :param name: (optional)
    :type name: string
    :param resource_type: (optional)
    :type resource_type: string
    :param mimetype: (optional)
    :type mimetype: string
    :param mimetype_inner: (optional)
    :type mimetype_inner: string
    :param cache_url: (optional)
    :type cache_url: string
    :param size: (optional)
    :type size: int
    :param created: (optional)
    :type created: iso date string
    :param last_modified: (optional)
    :type last_modified: iso date string
    :param cache_last_updated: (optional)
    :type cache_last_updated: iso date string
    :param upload: (optional)
    :type upload: FieldStorage (optional) needs multipart/form-data

    :returns: the newly created resource
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    package_id = _get_or_bust(data_dict, 'package_id')
    if not data_dict.get('url'):
        data_dict['url'] = ''

    package_show_context = dict(context, for_update=True, return_type='dict')
    pkg_dict = _get_action('package_show')(
        package_show_context,
        {'id': package_id})

    _check_access('resource_create', context, data_dict)

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.before_create(context, data_dict)

    if 'resources' not in pkg_dict:
        pkg_dict['resources'] = []

    upload = uploader.get_resource_uploader(data_dict)

    if 'mimetype' not in data_dict:
        if hasattr(upload, 'mimetype'):
            data_dict['mimetype'] = upload.mimetype

    if 'size' not in data_dict:
        if hasattr(upload, 'filesize'):
            data_dict['size'] = upload.filesize

    pkg_dict['resources'].append(data_dict)

    try:
        context['defer_commit'] = True
        context['use_cache'] = False
        _get_action('package_update')(context, pkg_dict)
        context.pop('defer_commit')
    except ValidationError as e:
        try:
            raise ValidationError(e.error_dict['resources'][-1])
        except (KeyError, IndexError):
            raise ValidationError(e.error_dict)

    # Get out resource_id resource from model as it will not appear in
    # package_show until after commit
    upload.upload(context['package'].resources[-1].id,
                  uploader.get_max_resource_size())

    model.repo.commit()

    #  Run package show again to get out actual last_resource
    updated_pkg_dict = _get_action('package_show')(context, {'id': package_id})
    resource = updated_pkg_dict['resources'][-1]

    #  Add the default views to the new resource
    logic.get_action('resource_create_default_resource_views')(
        {'model': context['model'],
         'user': context['user'],
         'ignore_auth': True
         },
        {'resource': resource,
         'package': updated_pkg_dict
         })

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.after_create(context, resource)

    return resource


def resource_view_create(context, data_dict):
    '''Creates a new resource view.

    :param resource_id: id of the resource
    :type resource_id: string
    :param title: the title of the view
    :type title: string
    :param description: a description of the view (optional)
    :type description: string
    :param view_type: type of view
    :type view_type: string
    :param config: options necessary to recreate a view state (optional)
    :type config: JSON string

    :returns: the newly created resource view
    :rtype: dictionary

    '''
    model = context['model']

    resource_id = _get_or_bust(data_dict, 'resource_id')
    view_type = _get_or_bust(data_dict, 'view_type')
    view_plugin = ckan.lib.datapreview.get_view_plugin(view_type)

    if not view_plugin:
        raise ValidationError(
            {"view_type": "No plugin found for view_type {view_type}".format(
                view_type=view_type
            )}
        )

    default = logic.schema.default_create_resource_view_schema(view_plugin)
    schema = context.get('schema', default)
    plugin_schema = view_plugin.info().get('schema', {})
    schema.update(plugin_schema)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    _check_access('resource_view_create', context, data_dict)

    if context.get('preview'):
        return data

    max_order = model.Session.query(
        func.max(model.ResourceView.order)
    ).filter_by(resource_id=resource_id).first()

    order = 0
    if max_order[0] is not None:
        order = max_order[0] + 1
    data['order'] = order

    resource_view = model_save.resource_view_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    return model_dictize.resource_view_dictize(resource_view, context)


def resource_create_default_resource_views(context, data_dict):
    '''
    Creates the default views (if necessary) on the provided resource

    The function will get the plugins for the default views defined in
    the configuration, and if some were found the `can_view` method of
    each one of them will be called to determine if a resource view should
    be created. Resource views extensions get the resource dict and the
    parent dataset dict.

    If the latter is not provided, `package_show` is called to get it.

    By default only view plugins that don't require the resource data to be in
    the DataStore are called. See
    :py:func:`ckan.logic.action.create.package_create_default_resource_views.``
    for details on the ``create_datastore_views`` parameter.

    :param resource: full resource dict
    :type resource: dict
    :param package: full dataset dict (optional, if not provided
        :py:func:`~ckan.logic.action.get.package_show` will be called).
    :type package: dict
    :param create_datastore_views: whether to create views that rely on data
        being on the DataStore (optional, defaults to False)
    :type create_datastore_views: bool

    :returns: a list of resource views created (empty if none were created)
    :rtype: list of dictionaries
    '''

    resource_dict = _get_or_bust(data_dict, 'resource')

    _check_access('resource_create_default_resource_views', context, data_dict)

    dataset_dict = data_dict.get('package')

    create_datastore_views = ckan.common.asbool(
        data_dict.get('create_datastore_views', False))

    return ckan.lib.datapreview.add_views_to_resource(
        context,
        resource_dict,
        dataset_dict,
        view_types=[],
        create_datastore_views=create_datastore_views)


def package_create_default_resource_views(context, data_dict):
    '''
    Creates the default views on all resources of the provided dataset

    By default only view plugins that don't require the resource data to be in
    the DataStore are called. Passing `create_datastore_views` as True will
    only create views that require data to be in the DataStore. The first case
    happens when the function is called from `package_create` or
    `package_update`, the second when it's called from the DataPusher when
    data was uploaded to the DataStore.

    :param package: full dataset dict (ie the one obtained
        calling :py:func:`~ckan.logic.action.get.package_show`).
    :type package: dict
    :param create_datastore_views: whether to create views that rely on data
        being on the DataStore (optional, defaults to False)
    :type create_datastore_views: bool

    :returns: a list of resource views created (empty if none were created)
    :rtype: list of dictionaries
    '''

    dataset_dict = _get_or_bust(data_dict, 'package')

    _check_access('package_create_default_resource_views', context, data_dict)

    create_datastore_views = ckan.common.asbool(
        data_dict.get('create_datastore_views', False))

    return ckan.lib.datapreview.add_views_to_dataset_resources(
        context,
        dataset_dict,
        view_types=[],
        create_datastore_views=create_datastore_views)


def package_relationship_create(context, data_dict):
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
    model = context['model']
    user = context['user']
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
        return NotFound('Object package %r was not found.' % id2)

    data, errors = _validate(data_dict, schema, context)
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


def member_create(context, data_dict=None):
    '''Make an object (e.g. a user, dataset or group) a member of a group.

    If the object is already a member of the group then the capacity of the
    membership will be updated.

    You must be authorized to edit the group.

    :param id: the id or name of the group to add the object to
    :type id: string
    :param object: the id or name of the object to add
    :type object: string
    :param object_type: the type of the object being added, e.g. ``'package'``
        or ``'user'``
    :type object_type: string
    :param capacity: the capacity of the membership
    :type capacity: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    group_id, obj_id, obj_type, capacity = \
        _get_or_bust(data_dict, ['id', 'object', 'object_type', 'capacity'])

    group = model.Group.get(group_id)
    if not group:
        raise NotFound('Group was not found.')

    obj_class = ckan.logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound('%s was not found.' % obj_type.title())

    _check_access('member_create', context, data_dict)

    # Look up existing, in case it exists
    member = model.Session.query(model.Member).\
        filter(model.Member.table_name == obj_type).\
        filter(model.Member.table_id == obj.id).\
        filter(model.Member.group_id == group.id).\
        filter(model.Member.state == 'active').first()
    if member:
        user_obj = model.User.get(user)
        if member.table_name == u'user' and \
                member.table_id == user_obj.id and \
                member.capacity == u'admin' and \
                capacity != u'admin':
            raise NotAuthorized("Administrators cannot revoke their "
                                "own admin status")
    else:
        member = model.Member(table_name=obj_type,
                              table_id=obj.id,
                              group_id=group.id,
                              state='active')
        member.group = group
    member.capacity = capacity

    model.Session.add(member)
    model.repo.commit()

    return model_dictize.member_dictize(member, context)


def package_collaborator_create(context, data_dict):
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

    model = context['model']

    package_id, user_id, capacity = _get_or_bust(
        data_dict,
        ['id', 'user_id', 'capacity']
    )

    allowed_capacities = authz.get_collaborator_capacities()
    if capacity not in allowed_capacities:
        raise ValidationError(
            _('Role must be one of "{}"').format(', '.join(
                allowed_capacities)))

    _check_access('package_collaborator_create', context, data_dict)

    package = model.Package.get(package_id)
    if not package:
        raise NotFound(_('Dataset not found'))

    user = model.User.get(user_id)
    if not user:
        raise NotFound(_('User not found'))

    if not authz.check_config_permission('allow_dataset_collaborators'):
        raise ValidationError(_('Dataset collaborators not enabled'))

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

    log.info('User {} added as collaborator in package {} ({})'.format(
        user.name, package.id, capacity))

    return model_dictize.member_dictize(collaborator, context)


def _group_or_org_create(context, data_dict, is_org=False):
    model = context['model']
    user = context['user']
    session = context['session']
    data_dict['is_organization'] = is_org

    upload = uploader.get_uploader('group')
    upload.update_data_dict(data_dict, 'image_url',
                            'image_upload', 'clear_upload')
    # get the schema
    group_type = data_dict.get('type', 'organization' if is_org else 'group')
    group_plugin = lib_plugins.lookup_group_plugin(group_type)
    try:
        schema = group_plugin.form_to_db_schema_options({
            'type': 'create', 'api': 'api_version' in context,
            'context': context})
    except AttributeError:
        schema = group_plugin.form_to_db_schema()

    if 'api_version' not in context:
        # old plugins do not support passing the schema so we need
        # to ensure they still work
        try:
            group_plugin.check_data_dict(data_dict, schema)
        except TypeError:
            group_plugin.check_data_dict(data_dict)

    data, errors = lib_plugins.plugin_validate(
        group_plugin, context, data_dict, schema,
        'organization_create' if is_org else 'group_create')
    log.debug('group_create validate_errs=%r user=%s group=%s data_dict=%r',
              errors, context.get('user'), data_dict.get('name'), data_dict)

    if errors:
        session.rollback()
        raise ValidationError(errors)

    group = model_save.group_dict_save(data, context)

    # Needed to let extensions know the group id
    session.flush()

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.create(group)

    if is_org:
        activity_type = 'new organization'
    else:
        activity_type = 'new group'

    user_id = model.User.by_name(six.ensure_text(user)).id

    activity_dict = {
        'user_id': user_id,
        'object_id': group.id,
        'activity_type': activity_type,
    }
    activity_dict['data'] = {
        'group': ckan.lib.dictization.table_dictize(group, context)
    }
    activity_create_context = {
        'model': model,
        'user': user,
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }
    logic.get_action('activity_create')(activity_create_context, activity_dict)

    upload.upload(uploader.get_max_image_size())

    if not context.get('defer_commit'):
        model.repo.commit()
    context["group"] = group
    context["id"] = group.id

    # creator of group/org becomes an admin
    # this needs to be after the repo.commit or else revisions break
    member_dict = {
        'id': group.id,
        'object': user_id,
        'object_type': 'user',
        'capacity': 'admin',
    }
    member_create_context = {
        'model': model,
        'user': user,
        'ignore_auth': True,  # we are not a member of the group at this point
        'session': session
    }
    logic.get_action('member_create')(member_create_context, member_dict)

    log.debug('Created object %s' % group.name)

    return_id_only = context.get('return_id_only', False)
    action = 'organization_show' if is_org else 'group_show'

    output = context['id'] if return_id_only \
        else _get_action(action)(context, {'id': group.id})

    return output


def group_create(context, data_dict):
    '''Create a new group.

    You must be authorized to create groups.

    Plugins may change the parameters of this function depending on the value
    of the ``type`` parameter, see the
    :py:class:`~ckan.plugins.interfaces.IGroupForm` plugin interface.

    :param name: the name of the group, a string between 2 and 100 characters
        long, containing only lowercase alphanumeric characters, ``-`` and
        ``_``
    :type name: string
    :param id: the id of the group (optional)
    :type id: string
    :param title: the title of the group (optional)
    :type title: string
    :param description: the description of the group (optional)
    :type description: string
    :param image_url: the URL to an image to be displayed on the group's page
        (optional)
    :type image_url: string
    :param type: the type of the group (optional, default: ``'group'``),
        :py:class:`~ckan.plugins.interfaces.IGroupForm` plugins
        associate themselves with different group types and provide custom
        group handling behaviour for these types
        Cannot be 'organization'
    :type type: string
    :param state: the current state of the group, e.g. ``'active'`` or
        ``'deleted'``, only active groups show up in search results and
        other lists of groups, this parameter will be ignored if you are not
        authorized to change the state of the group (optional, default:
        ``'active'``)
    :type state: string
    :param approval_status: (optional)
    :type approval_status: string
    :param extras: the group's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to groups, each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string), and optionally ``'deleted'``
    :type extras: list of dataset extra dictionaries
    :param packages: the datasets (packages) that belong to the group, a list
        of dictionaries each with keys ``'name'`` (string, the id or name of
        the dataset) and optionally ``'title'`` (string, the title of the
        dataset)
    :type packages: list of dictionaries
    :param groups: the groups that belong to the group, a list of dictionaries
        each with key ``'name'`` (string, the id or name of the group) and
        optionally ``'capacity'`` (string, the capacity in which the group is
        a member of the group)
    :type groups: list of dictionaries
    :param users: the users that belong to the group, a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and
        optionally ``'capacity'`` (string, the capacity in which the user is
        a member of the group)
    :type users: list of dictionaries

    :returns: the newly created group (unless 'return_id_only' is set to True
              in the context, in which case just the group id will
              be returned)
    :rtype: dictionary

    '''
    # wrapper for creating groups
    if data_dict.get('type') == 'organization':
        # FIXME better exception?
        raise Exception(_('Trying to create an organization as a group'))
    _check_access('group_create', context, data_dict)
    return _group_or_org_create(context, data_dict)


def organization_create(context, data_dict):
    '''Create a new organization.

    You must be authorized to create organizations.

    Plugins may change the parameters of this function depending on the value
    of the ``type`` parameter, see the
    :py:class:`~ckan.plugins.interfaces.IGroupForm` plugin interface.

    :param name: the name of the organization, a string between 2 and
        100 characters long, containing only lowercase alphanumeric
        characters, ``-`` and ``_``
    :type name: string
    :param id: the id of the organization (optional)
    :type id: string
    :param title: the title of the organization (optional)
    :type title: string
    :param description: the description of the organization (optional)
    :type description: string
    :param image_url: the URL to an image to be displayed on the
        organization's page (optional)
    :type image_url: string
    :param state: the current state of the organization, e.g. ``'active'`` or
        ``'deleted'``, only active organizations show up in search results and
        other lists of organizations, this parameter will be ignored if you
        are not authorized to change the state of the organization
        (optional, default: ``'active'``)
    :type state: string
    :param approval_status: (optional)
    :type approval_status: string
    :param extras: the organization's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to organizations,
        each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string), and optionally ``'deleted'``
    :type extras: list of dataset extra dictionaries
    :param packages: the datasets (packages) that belong to the organization,
        a list of dictionaries each with keys ``'name'`` (string, the id
        or name of the dataset) and optionally ``'title'`` (string, the
        title of the dataset)
    :type packages: list of dictionaries
    :param users: the users that belong to the organization, a list
        of dictionaries each with key ``'name'`` (string, the id or name
        of the user) and optionally ``'capacity'`` (string, the capacity
        in which the user is a member of the organization)
    :type users: list of dictionaries

    :returns: the newly created organization (unless 'return_id_only' is set
              to True in the context, in which case just the organization id
              will be returned)
    :rtype: dictionary

    '''
    # wrapper for creating organizations
    data_dict.setdefault('type', 'organization')
    _check_access('organization_create', context, data_dict)
    return _group_or_org_create(context, data_dict, is_org=True)


@logic.auth_audit_exempt
def rating_create(context, data_dict):
    '''Rate a dataset (package).

    You must provide your API key in the Authorization header.

    :param package: the name or id of the dataset to rate
    :type package: string
    :param rating: the rating to give to the dataset, an integer between 1 and
        5
    :type rating: int

    :returns: a dictionary with two keys: ``'rating average'`` (the average
        rating of the dataset you rated) and ``'rating count'`` (the number of
        times the dataset has been rated)
    :rtype: dictionary

    '''
    model = context['model']
    user = context.get("user")

    package_ref = data_dict.get('package')
    rating = data_dict.get('rating')
    opts_err = None
    if not package_ref:
        opts_err = _('You must supply a package id or name '
                     '(parameter "package").')
    elif not rating:
        opts_err = _('You must supply a rating (parameter "rating").')
    else:
        try:
            rating_int = int(rating)
        except ValueError:
            opts_err = _('Rating must be an integer value.')
        else:
            package = model.Package.get(package_ref)
            if rating < model.MIN_RATING or rating > model.MAX_RATING:
                opts_err = _('Rating must be between %i and %i.') \
                    % (model.MIN_RATING, model.MAX_RATING)
            elif not package:
                opts_err = _('Not found') + ': %r' % package_ref
    if opts_err:
        raise ValidationError(opts_err)

    user = model.User.by_name(user)
    package.set_rating(user, rating_int)
    model.repo.commit()

    package = model.Package.get(package_ref)
    ret_dict = {'rating average': package.get_average_rating(),
                'rating count': len(package.ratings)}
    return ret_dict


def user_create(context, data_dict):
    '''Create a new user.

    You must be authorized to create users.

    :param name: the name of the new user, a string between 2 and 100
        characters in length, containing only lowercase alphanumeric
        characters, ``-`` and ``_``
    :type name: string
    :param email: the email address for the new user
    :type email: string
    :param password: the password of the new user, a string of at least 4
        characters
    :type password: string
    :param id: the id of the new user (optional)
    :type id: string
    :param fullname: the full name of the new user (optional)
    :type fullname: string
    :param about: a description of the new user (optional)
    :type about: string
    :param image_url: the URL to an image to be displayed on the group's page
        (optional)
    :type image_url: string
    :param plugin_extras: private extra user data belonging to plugins.
        Only sysadmin users may set this value. It should be a dict that can
        be dumped into JSON, and plugins should namespace their extras with
        the plugin name to avoid collisions with other plugins, eg::

            {
                "name": "test_user",
                "email": "test@example.com",
                "plugin_extras": {
                    "my_plugin": {
                        "private_extra": 1
                    },
                    "another_plugin": {
                        "another_extra": True
                    }
                }
            }
    :type plugin_extras: dict


    :returns: the newly created user
    :rtype: dictionary

    '''
    model = context['model']
    schema = context.get('schema') or ckan.logic.schema.default_user_schema()
    session = context['session']

    _check_access('user_create', context, data_dict)

    author_obj = model.User.get(context.get('user'))
    if data_dict.get("id"):
        is_sysadmin = (author_obj and author_obj.sysadmin)
        if not is_sysadmin or model.User.get(data_dict["id"]):
            data_dict.pop("id", None)
    context.pop("user_obj", None)

    upload = uploader.get_uploader('user')
    upload.update_data_dict(data_dict, 'image_url',
                            'image_upload', 'clear_upload')
    data, errors = _validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors)

    # user schema prevents non-sysadmins from providing password_hash
    if 'password_hash' in data:
        data['_password'] = data.pop('password_hash')

    user = model_save.user_dict_save(data, context)

    # Flush the session to cause user.id to be initialised, because
    # activity_create() (below) needs it.
    session.flush()

    activity_create_context = {
        'model': model,
        'user': context['user'],
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }
    activity_dict = {
        'user_id': user.id,
        'object_id': user.id,
        'activity_type': 'new user',
    }
    logic.get_action('activity_create')(activity_create_context, activity_dict)

    upload.upload(uploader.get_max_image_size())

    if not context.get('defer_commit'):
        model.repo.commit()

    # A new context is required for dictizing the newly constructed user in
    # order that all the new user's data is returned, in particular, the
    # api_key.
    #
    # The context is copied so as not to clobber the caller's context dict.
    user_dictize_context = context.copy()
    user_dictize_context['keep_apikey'] = True
    user_dictize_context['keep_email'] = True

    include_plugin_extras = False
    if author_obj:
        include_plugin_extras = author_obj.sysadmin and 'plugin_extras' in data
    user_dict = model_dictize.user_dictize(
        user, user_dictize_context,
        include_plugin_extras=include_plugin_extras
    )

    context['user_obj'] = user
    context['id'] = user.id

    model.Dashboard.get(user.id)  # Create dashboard for user.

    log.debug('Created user {name}'.format(name=user.name))
    return user_dict


def user_invite(context, data_dict):
    '''Invite a new user.

    You must be authorized to create group members.

    :param email: the email of the user to be invited to the group
    :type email: string
    :param group_id: the id or name of the group
    :type group_id: string
    :param role: role of the user in the group. One of ``member``, ``editor``,
        or ``admin``
    :type role: string

    :returns: the newly created user
    :rtype: dictionary
    '''
    import string
    _check_access('user_invite', context, data_dict)

    schema = context.get('schema',
                         ckan.logic.schema.default_user_invite_schema())
    data, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    model = context['model']
    group = model.Group.get(data['group_id'])
    if not group:
        raise NotFound()

    name = _get_random_username_from_email(data['email'])
    # Choose a password. However it will not be used - the invitee will not be
    # told it - they will need to reset it
    while True:
        password = ''.join(random.SystemRandom().choice(
            string.ascii_lowercase + string.ascii_uppercase + string.digits)
            for _ in range(12))
        # Occasionally it won't meet the constraints, so check
        errors = {}
        logic.validators.user_password_validator(
            'password', {'password': password}, errors, None)
        if not errors:
            break

    data['name'] = name
    data['password'] = password
    data['state'] = ckan.model.State.PENDING
    create_context = dict(context, ignore_auth=True)
    user_dict = _get_action('user_create')(create_context, data)
    user = ckan.model.User.get(user_dict['id'])
    member_dict = {
        'username': user.id,
        'id': data['group_id'],
        'role': data['role']
    }

    if group.is_organization:
        _get_action('organization_member_create')(context, member_dict)
        group_dict = _get_action('organization_show')(context,
                                                      {'id': data['group_id']})
    else:
        _get_action('group_member_create')(context, member_dict)
        group_dict = _get_action('group_show')(context,
                                               {'id': data['group_id']})
    try:
        mailer.send_invite(user, group_dict, data['role'])
    except (socket_error, mailer.MailerException) as error:
        # Email could not be sent, delete the pending user

        _get_action('user_delete')(context, {'id': user.id})

        error_dict = {
            "message": _('Error sending the invite email, \
                the user was not created: {0}').format(error)
        }
        raise ValidationError(error_dict, error_summary=error_dict)

    return model_dictize.user_dictize(user, context)


def _get_random_username_from_email(email):
    localpart = email.split('@')[0]
    cleaned_localpart = re.sub(r'[^\w]', '-', localpart).lower()

    # if we can't create a unique user name within this many attempts
    # then something else is probably wrong and we should give up
    max_name_creation_attempts = 100

    for i in range(max_name_creation_attempts):
        random_number = random.SystemRandom().random() * 10000
        name = '%s-%d' % (cleaned_localpart, random_number)
        if not ckan.model.User.get(name):
            return name

    return cleaned_localpart


def vocabulary_create(context, data_dict):
    '''Create a new tag vocabulary.

    You must be a sysadmin to create vocabularies.

    :param name: the name of the new vocabulary, e.g. ``'Genre'``
    :type name: string
    :param tags: the new tags to add to the new vocabulary, for the format of
        tag dictionaries see :py:func:`tag_create`
    :type tags: list of tag dictionaries

    :returns: the newly-created vocabulary
    :rtype: dictionary

    '''
    model = context['model']
    schema = context.get('schema') or \
        ckan.logic.schema.default_create_vocabulary_schema()

    _check_access('vocabulary_create', context, data_dict)

    data, errors = _validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    vocabulary = model_save.vocabulary_dict_save(data, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug('Created Vocabulary %s' % vocabulary.name)

    return model_dictize.vocabulary_dictize(vocabulary, context)


def activity_create(context, activity_dict, **kw):
    '''Create a new activity stream activity.

    You must be a sysadmin to create new activities.

    :param user_id: the name or id of the user who carried out the activity,
        e.g. ``'seanh'``
    :type user_id: string
    :param object_id: the name or id of the object of the activity, e.g.
        ``'my_dataset'``
    :param activity_type: the type of the activity, this must be an activity
        type that CKAN knows how to render, e.g. ``'new package'``,
        ``'changed user'``, ``'deleted group'`` etc.
    :type activity_type: string
    :param data: any additional data about the activity
    :type data: dictionary

    :returns: the newly created activity
    :rtype: dictionary

    '''

    _check_access('activity_create', context, activity_dict)

    # this action had a ignore_auth param which has been removed
    # removed in 2.2
    if 'ignore_auth' in kw:
        raise Exception('Activity Stream calling parameters have changed '
                        'ignore_auth must be passed in the context not as '
                        'a param')

    if not ckan.common.asbool(
            config.get('ckan.activity_streams_enabled', 'true')):
        return

    model = context['model']

    # Any revision_id that the caller attempts to pass in the activity_dict is
    # ignored and removed here.
    if 'revision_id' in activity_dict:
        del activity_dict['revision_id']

    schema = context.get('schema') or \
        ckan.logic.schema.default_create_activity_schema()

    data, errors = _validate(activity_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    activity = model_save.activity_dict_save(data, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug("Created '%s' activity" % activity.activity_type)
    return model_dictize.activity_dictize(activity, context)


def tag_create(context, data_dict):
    '''Create a new vocabulary tag.

    You must be a sysadmin to create vocabulary tags.

    You can only use this function to create tags that belong to a vocabulary,
    not to create free tags. (To create a new free tag simply add the tag to
    a package, e.g. using the
    :py:func:`~ckan.logic.action.update.package_update` function.)

    :param name: the name for the new tag, a string between 2 and 100
        characters long containing only alphanumeric characters and ``-``,
        ``_`` and ``.``, e.g. ``'Jazz'``
    :type name: string
    :param vocabulary_id: the id of the vocabulary that the new tag
        should be added to, e.g. the id of vocabulary ``'Genre'``
    :type vocabulary_id: string

    :returns: the newly-created tag
    :rtype: dictionary

    '''
    model = context['model']

    _check_access('tag_create', context, data_dict)

    schema = context.get('schema') or \
        ckan.logic.schema.default_create_tag_schema()
    data, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    tag = model_save.tag_dict_save(data_dict, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug("Created tag '%s' " % tag)
    return model_dictize.tag_dictize(tag, context)


def follow_user(context, data_dict):
    '''Start following another user.

    You must provide your API key in the Authorization header.

    :param id: the id or name of the user to follow, e.g. ``'joeuser'``
    :type id: string

    :returns: a representation of the 'follower' relationship between yourself
        and the other user
    :rtype: dictionary

    '''
    if 'user' not in context:
        raise NotAuthorized(_("You must be logged in to follow users"))

    model = context['model']
    session = context['session']

    userobj = model.User.get(context['user'])
    if not userobj:
        raise NotAuthorized(_("You must be logged in to follow users"))

    schema = (context.get('schema')
              or ckan.logic.schema.default_follow_user_schema())

    validated_data_dict, errors = _validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    # Don't let a user follow herself.
    if userobj.id == validated_data_dict['id']:
        message = _('You cannot follow yourself')
        raise ValidationError({'message': message}, error_summary=message)

    # Don't let a user follow someone she is already following.
    if model.UserFollowingUser.is_following(userobj.id,
                                            validated_data_dict['id']):
        followeduserobj = model.User.get(validated_data_dict['id'])
        name = followeduserobj.display_name
        message = _('You are already following {0}').format(name)
        raise ValidationError({'message': message}, error_summary=message)

    follower = model_save.follower_dict_save(
        validated_data_dict, context, model.UserFollowingUser)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug(u'User {follower} started following user {object}'.format(
        follower=follower.follower_id, object=follower.object_id))

    return model_dictize.user_following_user_dictize(follower, context)


def follow_dataset(context, data_dict):
    '''Start following a dataset.

    You must provide your API key in the Authorization header.

    :param id: the id or name of the dataset to follow, e.g. ``'warandpeace'``
    :type id: string

    :returns: a representation of the 'follower' relationship between yourself
        and the dataset
    :rtype: dictionary

    '''

    if 'user' not in context:
        raise NotAuthorized(
            _("You must be logged in to follow a dataset."))

    model = context['model']
    session = context['session']

    userobj = model.User.get(context['user'])
    if not userobj:
        raise NotAuthorized(
            _("You must be logged in to follow a dataset."))

    schema = (context.get('schema')
              or ckan.logic.schema.default_follow_dataset_schema())

    validated_data_dict, errors = _validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    # Don't let a user follow a dataset she is already following.
    if model.UserFollowingDataset.is_following(userobj.id,
                                               validated_data_dict['id']):
        # FIXME really package model should have this logic and provide
        # 'display_name' like users and groups
        pkgobj = model.Package.get(validated_data_dict['id'])
        name = pkgobj.title or pkgobj.name or pkgobj.id
        message = _(
            'You are already following {0}').format(name)
        raise ValidationError({'message': message}, error_summary=message)

    follower = model_save.follower_dict_save(validated_data_dict, context,
                                             model.UserFollowingDataset)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug(u'User {follower} started following dataset {object}'.format(
        follower=follower.follower_id, object=follower.object_id))

    return model_dictize.user_following_dataset_dictize(follower, context)


def _group_or_org_member_create(context, data_dict, is_org=False):
    # creator of group/org becomes an admin
    # this needs to be after the repo.commit or else revisions break
    model = context['model']
    user = context['user']
    session = context['session']

    schema = ckan.logic.schema.member_schema()
    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    username = _get_or_bust(data_dict, 'username')
    role = data_dict.get('role')
    group_id = data_dict.get('id')
    group = model.Group.get(group_id)
    if not group:
        msg = _('Organization not found') if is_org else _('Group not found')
        raise NotFound(msg)
    result = model.User.get(username)
    if result:
        user_id = result.id
    else:
        message = _(u'User {username} does not exist.').format(
            username=username)
        raise ValidationError({'message': message}, error_summary=message)
    member_dict = {
        'id': group.id,
        'object': user_id,
        'object_type': 'user',
        'capacity': role,
    }
    member_create_context = {
        'model': model,
        'user': user,
        'session': session,
        'ignore_auth': context.get('ignore_auth'),
    }
    return logic.get_action('member_create')(member_create_context,
                                             member_dict)


def group_member_create(context, data_dict):
    '''Make a user a member of a group.

    You must be authorized to edit the group.

    :param id: the id or name of the group
    :type id: string
    :param username: name or id of the user to be made member of the group
    :type username: string
    :param role: role of the user in the group. One of ``member``, ``editor``,
        or ``admin``
    :type role: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary
    '''
    _check_access('group_member_create', context, data_dict)
    return _group_or_org_member_create(context, data_dict)


def organization_member_create(context, data_dict):
    '''Make a user a member of an organization.

    You must be authorized to edit the organization.

    :param id: the id or name of the organization
    :type id: string
    :param username: name or id of the user to be made member of the
        organization
    :type username: string
    :param role: role of the user in the organization. One of ``member``,
        ``editor``, or ``admin``
    :type role: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary
    '''
    _check_access('organization_member_create', context, data_dict)
    return _group_or_org_member_create(context, data_dict, is_org=True)


def follow_group(context, data_dict):
    '''Start following a group.

    You must provide your API key in the Authorization header.

    :param id: the id or name of the group to follow, e.g. ``'roger'``
    :type id: string

    :returns: a representation of the 'follower' relationship between yourself
        and the group
    :rtype: dictionary

    '''
    if 'user' not in context:
        raise NotAuthorized(
            _("You must be logged in to follow a group."))

    model = context['model']
    session = context['session']

    userobj = model.User.get(context['user'])
    if not userobj:
        raise NotAuthorized(
            _("You must be logged in to follow a group."))

    schema = context.get('schema',
                         ckan.logic.schema.default_follow_group_schema())

    validated_data_dict, errors = _validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    # Don't let a user follow a group she is already following.
    if model.UserFollowingGroup.is_following(userobj.id,
                                             validated_data_dict['id']):
        groupobj = model.Group.get(validated_data_dict['id'])
        name = groupobj.display_name
        message = _(
            'You are already following {0}').format(name)
        raise ValidationError({'message': message}, error_summary=message)

    follower = model_save.follower_dict_save(validated_data_dict, context,
                                             model.UserFollowingGroup)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug(u'User {follower} started following group {object}'.format(
        follower=follower.follower_id, object=follower.object_id))

    return model_dictize.user_following_group_dictize(follower, context)


def api_token_create(context, data_dict):
    """Create new API Token for current user.

    Apart from the `user` and `name` field that are required by
    default implementation, there may be additional fields registered
    by extensions.

    :param user: name or id of the user who owns new API Token
    :type user: string
    :param name: distinctive name for API Token
    :type name: string

    :returns: Returns a dict with the key "token" containing the
              encoded token value. Extensions can privide additional
              fields via `add_extra` method of
              :py:class:`~ckan.plugins.interfaces.IApiToken`
    :rtype: dictionary

    """
    model = context[u'model']
    user, name = _get_or_bust(data_dict, [u'user', u'name'])

    if model.User.get(user) is None:
        raise NotFound("User not found")

    _check_access(u'api_token_create', context, data_dict)

    schema = context.get(u'schema')
    if not schema:
        schema = api_token.get_schema()

    validated_data_dict, errors = _validate(data_dict, schema, context)

    if errors:
        raise ValidationError(errors)

    token_obj = model_save.api_token_save(
        {u'user': user, u'name': name}, context
    )
    model.Session.commit()
    data = {
        u'jti': token_obj.id,
        u'iat': api_token.into_seconds(token_obj.created_at)
    }

    data = api_token.postprocess(data, token_obj.id, validated_data_dict)
    token = api_token.encode(data)

    result = api_token.add_extra({u'token': token})
    return result
