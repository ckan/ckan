# encoding: utf-8

'''API functions for partial updates of existing data in CKAN'''

from ckan import model
from ckan.logic import (
    get_action as _get_action,
    check_access as _check_access,
    get_or_bust as _get_or_bust,
    fresh_context as _fresh_context,
    NotFound,
)
from ckan.types import Context, DataDict
from ckan.types.logic import ActionResult


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


def resource_patch(context: Context,
                   data_dict: DataDict) -> ActionResult.ResourcePatch:
    '''Patch a resource

    :param id: the id of the resource
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    '''
    _check_access('resource_patch', context, data_dict)

    resource = model.Resource.get(_get_or_bust(data_dict, 'id'))
    if not resource:
        raise NotFound('Resource was not found.')

    show_context: Context = _fresh_context(context)
    show_context.update({'for_update': True})

    package_dict = _get_action('package_show')(
        show_context,
        {'id': resource.package_id})

    if package_dict['resources'][resource.position]['id'] != resource.id:
        raise NotFound('Resource was not found.')

    patched = dict(package_dict['resources'][resource.position])
    # allow metadata_modified to be updated if data has changed
    patched.pop('metadata_modified', None)

    patched.update(data_dict)
    update_context = Context(context)
    update_context['original_package'] = package_dict
    return _get_action('resource_update')(update_context, patched)


def group_patch(context: Context,
                data_dict: DataDict) -> ActionResult.GroupPatch:
    '''Patch a group

    :param id: the id or name of the group
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    '''
    _check_access('group_patch', context, data_dict)

    show_context: Context = _fresh_context(context)

    group_dict = _get_action('group_show')(
        show_context,
        {'id': _get_or_bust(data_dict, 'id')})

    patched = dict(group_dict)
    patched.pop('display_name', None)
    patched.update(data_dict)

    patch_context = context.copy()
    return _get_action('group_update')(patch_context, patched)


def organization_patch(
        context: Context,
        data_dict: DataDict) -> ActionResult.OrganizationPatch:
    '''Patch an organization

    :param id: the id or name of the organization
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    '''
    _check_access('organization_patch', context, data_dict)

    show_context: Context = _fresh_context(context)

    organization_dict = _get_action('organization_show')(
        show_context,
        {'id': _get_or_bust(data_dict, 'id')})

    patched = dict(organization_dict)
    patched.pop('display_name', None)
    patched.update(data_dict)

    patch_context = context.copy()
    return _get_action('organization_update')(patch_context, patched)


def user_patch(context: Context,
               data_dict: DataDict) -> ActionResult.UserPatch:
    '''Patch a user

    :param id: the id or name of the user
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    '''
    _check_access('user_patch', context, data_dict)

    show_context: Context = _fresh_context(context)

    user_dict = _get_action('user_show')(
        show_context,
        {'id': _get_or_bust(data_dict, 'id')})

    patched = dict(user_dict)
    patched.pop('display_name', None)
    patched.update(data_dict)
    return _get_action('user_update')(context, patched)
