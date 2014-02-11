'''API functions for deleting data from CKAN.'''

from sqlalchemy import or_

import ckan.logic
import ckan.logic.action
import ckan.plugins as plugins
import ckan.lib.dictization.model_dictize as model_dictize

from ckan.common import _

validate = ckan.lib.navl.dictization_functions.validate

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
ValidationError = ckan.logic.ValidationError
NotFound = ckan.logic.NotFound
_check_access = ckan.logic.check_access
_get_or_bust = ckan.logic.get_or_bust
_get_action = ckan.logic.get_action


def user_delete(context, data_dict):
    '''Delete a user.

    Only sysadmins can delete users.

    :param id: the id or usernamename of the user to delete
    :type id: string
    '''

    _check_access('user_delete', context, data_dict)

    model = context['model']
    user_id = _get_or_bust(data_dict, 'id')
    user = model.User.get(user_id)

    if user is None:
        raise NotFound('User "{id}" was not found.'.format(id=user_id))

    user.delete()
    model.repo.commit()


def package_delete(context, data_dict):
    '''Delete a dataset (package).

    You must be authorized to delete the dataset.

    :param id: the id or name of the dataset to delete
    :type id: string

    '''
    model = context['model']
    user = context['user']
    id = _get_or_bust(data_dict, 'id')

    entity = model.Package.get(id)

    if entity is None:
        raise NotFound

    _check_access('package_delete',context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete Package: %s') % entity.name

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.delete(entity)

        item.after_delete(context, data_dict)

    entity.delete()
    model.repo.commit()

def resource_delete(context, data_dict):
    '''Delete a resource from a dataset.

    You must be a sysadmin or the owner of the resource to delete it.

    :param id: the id of the resource
    :type id: string

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    entity = model.Resource.get(id)

    if entity is None:
        raise NotFound

    _check_access('resource_delete',context, data_dict)

    package_id = entity.get_package_id()

    pkg_dict = _get_action('package_show')(context, {'id': package_id})

    if pkg_dict.get('resources'):
        pkg_dict['resources'] = [r for r in pkg_dict['resources'] if not
                r['id'] == id]
    try:
        pkg_dict = _get_action('package_update')(context, pkg_dict)
    except ValidationError, e:
        errors = e.error_dict['resources'][-1]
        raise ValidationError(errors)

    model.repo.commit()


def package_relationship_delete(context, data_dict):
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
    model = context['model']
    user = context['user']
    id, id2, rel = _get_or_bust(data_dict, ['subject', 'object', 'type'])

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('Subject package %r was not found.' % id)
    if not pkg2:
        return NotFound('Object package %r was not found.' % id2)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound

    relationship = existing_rels[0]
    revisioned_details = 'Package Relationship: %s %s %s' % (id, rel, id2)

    context['relationship'] = relationship
    _check_access('package_relationship_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete %s') % revisioned_details

    relationship.delete()
    model.repo.commit()

def related_delete(context, data_dict):
    '''Delete a related item from a dataset.

    You must be a sysadmin or the owner of the related item to delete it.

    :param id: the id of the related item
    :type id: string

    '''
    model = context['model']
    session = context['session']
    user = context['user']
    userobj = model.User.get(user)

    id = _get_or_bust(data_dict, 'id')

    entity = model.Related.get(id)

    if entity is None:
        raise NotFound

    _check_access('related_delete',context, data_dict)

    related_dict = model_dictize.related_dictize(entity, context)
    activity_dict = {
        'user_id': userobj.id,
        'object_id': entity.id,
        'activity_type': 'deleted related item',
    }
    activity_dict['data'] = {
        'related': related_dict
    }
    activity_create_context = {
        'model': model,
        'user': user,
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }

    _get_action('activity_create')(activity_create_context, activity_dict)
    session.commit()

    entity.delete()
    model.repo.commit()


def member_delete(context, data_dict=None):
    '''Remove an object (e.g. a user, dataset or group) from a group.

    You must be authorized to edit a group to remove objects from it.

    :param id: the id of the group
    :type id: string
    :param object: the id or name of the object to be removed
    :type object: string
    :param object_type: the type of the object to be removed, e.g. ``package``
        or ``user``
    :type object_type: string

    '''
    model = context['model']

    group_id, obj_id, obj_type = _get_or_bust(data_dict, ['id', 'object', 'object_type'])

    group = model.Group.get(group_id)
    if not group:
        raise NotFound('Group was not found.')

    obj_class = ckan.logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound('%s was not found.' % obj_type.title())

    _check_access('member_delete', context, data_dict)

    member = model.Session.query(model.Member).\
            filter(model.Member.table_name == obj_type).\
            filter(model.Member.table_id == obj.id).\
            filter(model.Member.group_id == group.id).\
            filter(model.Member.state    == 'active').first()
    if member:
        rev = model.repo.new_revision()
        rev.author = context.get('user')
        rev.message = _(u'REST API: Delete Member: %s') % obj_id
        member.delete()
        model.repo.commit()

def _group_or_org_delete(context, data_dict, is_org=False):
    '''Delete a group.

    You must be authorized to delete the group.

    :param id: the name or id of the group
    :type id: string

    '''
    model = context['model']
    user = context['user']
    id = _get_or_bust(data_dict, 'id')

    group = model.Group.get(id)
    context['group'] = group
    if group is None:
        raise NotFound('Group was not found.')

    revisioned_details = 'Group: %s' % group.name

    if is_org:
        _check_access('organization_delete', context, data_dict)
    else:
        _check_access('group_delete', context, data_dict)

    # organization delete will delete all datasets for that org
    # FIXME this gets all the packages the user can see which generally will
    # be all but this is only a fluke so we should fix this properly
    if is_org:
        for pkg in group.packages(with_private=True):
            _get_action('package_delete')(context, {'id': pkg.id})

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete %s') % revisioned_details

    # The group's Member objects are deleted
    # (including hierarchy connections to parent and children groups)
    for member in model.Session.query(model.Member).\
            filter(or_(model.Member.table_id == id,
                       model.Member.group_id == id)).\
            filter(model.Member.state == 'active').all():
        member.delete()

    group.delete()

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.delete(group)

    model.repo.commit()

def group_delete(context, data_dict):
    '''Delete a group.

    You must be authorized to delete the group.

    :param id: the name or id of the group
    :type id: string

    '''
    return _group_or_org_delete(context, data_dict)

def organization_delete(context, data_dict):
    '''Delete an organization.

    You must be authorized to delete the organization.

    :param id: the name or id of the organization
    :type id: string

    '''
    return _group_or_org_delete(context, data_dict, is_org=True)

def _group_or_org_purge(context, data_dict, is_org=False):
    '''Purge a group or organization.

    The group or organization will be completely removed from the database.
    This cannot be undone!

    Only sysadmins can purge groups or organizations.

    :param id: the name or id of the group or organization to be purged
    :type id: string

    :param is_org: you should pass is_org=True if purging an organization,
        otherwise False (optional, default: False)
    :type is_org: boolean

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    group = model.Group.get(id)
    context['group'] = group
    if group is None:
        if is_org:
            raise NotFound('Organization was not found')
        else:
            raise NotFound('Group was not found')

    if is_org:
        _check_access('organization_purge', context, data_dict)
    else:
        _check_access('group_purge', context, data_dict)

    members = model.Session.query(model.Member)
    members = members.filter(model.Member.group_id == group.id)
    if members.count() > 0:
        model.repo.new_revision()
        for m in members.all():
            m.delete()
        model.repo.commit_and_remove()

    group = model.Group.get(id)
    model.repo.new_revision()
    group.purge()
    model.repo.commit_and_remove()

def group_purge(context, data_dict):
    '''Purge a group.

    .. warning:: Purging a group cannot be undone!

    Purging a group completely removes the group from the CKAN database,
    whereas deleting a group simply marks the group as deleted (it will no
    longer show up in the frontend, but is still in the db).

    You must be authorized to purge the group.

    :param id: the name or id of the group to be purged
    :type id: string

    '''
    return _group_or_org_purge(context, data_dict, is_org=False)

def organization_purge(context, data_dict):
    '''Purge an organization.

    .. warning:: Purging an organization cannot be undone!

    Purging an organization completely removes the organization from the CKAN
    database, whereas deleting an organization simply marks the organization as
    deleted (it will no longer show up in the frontend, but is still in the
    db).

    You must be authorized to purge the organization.

    :param id: the name or id of the organization to be purged
    :type id: string

    '''
    return _group_or_org_purge(context, data_dict, is_org=True)

def task_status_delete(context, data_dict):
    '''Delete a task status.

    You must be a sysadmin to delete task statuses.

    :param id: the id of the task status to delete
    :type id: string

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    entity = model.TaskStatus.get(id)

    if entity is None:
        raise NotFound

    _check_access('task_status_delete', context, data_dict)

    entity.delete()
    model.Session.commit()

def vocabulary_delete(context, data_dict):
    '''Delete a tag vocabulary.

    You must be a sysadmin to delete vocabularies.

    :param id: the id of the vocabulary
    :type id: string

    '''
    model = context['model']

    vocab_id = data_dict.get('id')
    if not vocab_id:
        raise ValidationError({'id': _('id not in data')})

    vocab_obj = model.vocabulary.Vocabulary.get(vocab_id)
    if vocab_obj is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)

    _check_access('vocabulary_delete', context, data_dict)

    vocab_obj.delete()
    model.repo.commit()

def tag_delete(context, data_dict):
    '''Delete a tag.

    You must be a sysadmin to delete tags.

    :param id: the id or name of the tag
    :type id: string
    :param vocabulary_id: the id or name of the vocabulary that the tag belongs
        to (optional, default: None)
    :type vocabulary_id: string

    '''
    model = context['model']

    if not data_dict.has_key('id') or not data_dict['id']:
        raise ValidationError({'id': _('id not in data')})
    tag_id_or_name = _get_or_bust(data_dict, 'id')

    vocab_id_or_name = data_dict.get('vocabulary_id')

    tag_obj = model.tag.Tag.get(tag_id_or_name, vocab_id_or_name)

    if tag_obj is None:
        raise NotFound(_('Could not find tag "%s"') % tag_id_or_name)

    _check_access('tag_delete', context, data_dict)

    tag_obj.delete()
    model.repo.commit()

def package_relationship_delete_rest(context, data_dict):

    # rename keys
    key_map = {'id': 'subject',
               'id2': 'object',
               'rel': 'type'}
    # We want 'destructive', so that the value of the subject,
    # object and rel in the URI overwrite any values for these
    # in params. This is because you are not allowed to change
    # these values.
    data_dict = ckan.logic.action.rename_keys(data_dict, key_map, destructive=True)

    package_relationship_delete(context, data_dict)

def _unfollow(context, data_dict, schema, FollowerClass):
    model = context['model']

    if not context.has_key('user'):
        raise ckan.logic.NotAuthorized(
                _("You must be logged in to unfollow something."))
    userobj = model.User.get(context['user'])
    if not userobj:
        raise ckan.logic.NotAuthorized(
                _("You must be logged in to unfollow something."))
    follower_id = userobj.id

    validated_data_dict, errors = validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)
    object_id = validated_data_dict.get('id')

    follower_obj = FollowerClass.get(follower_id, object_id)
    if follower_obj is None:
        raise NotFound(
                _('You are not following {0}.').format(data_dict.get('id')))

    follower_obj.delete()
    model.repo.commit()

def unfollow_user(context, data_dict):
    '''Stop following a user.

    :param id: the id or name of the user to stop following
    :type id: string

    '''
    schema = context.get('schema') or (
            ckan.logic.schema.default_follow_user_schema())
    _unfollow(context, data_dict, schema, context['model'].UserFollowingUser)

def unfollow_dataset(context, data_dict):
    '''Stop following a dataset.

    :param id: the id or name of the dataset to stop following
    :type id: string

    '''
    schema = context.get('schema') or (
            ckan.logic.schema.default_follow_dataset_schema())
    _unfollow(context, data_dict, schema,
            context['model'].UserFollowingDataset)


def _group_or_org_member_delete(context, data_dict=None):
    model = context['model']
    user = context['user']
    session = context['session']

    group_id = data_dict.get('id')
    group = model.Group.get(group_id)
    user_id = data_dict.get('username')
    user_id = data_dict.get('user_id') if user_id is None else user_id
    member_dict = {
        'id': group.id,
        'object': user_id,
        'object_type': 'user',
    }
    member_context = {
        'model': model,
        'user': user,
        'session': session
    }
    _get_action('member_delete')(member_context, member_dict)


def group_member_delete(context, data_dict=None):
    '''Remove a user from a group.

    You must be authorized to edit the group.

    :param id: the id or name of the group
    :type id: string
    :param username: name or id of the user to be removed
    :type username: string

    '''
    _check_access('group_member_delete',context, data_dict)
    return _group_or_org_member_delete(context, data_dict)

def organization_member_delete(context, data_dict=None):
    '''Remove a user from an organization.

    You must be authorized to edit the organization.

    :param id: the id or name of the organization
    :type id: string
    :param username: name or id of the user to be removed
    :type username: string

    '''
    _check_access('organization_member_delete',context, data_dict)
    return _group_or_org_member_delete(context, data_dict)


def unfollow_group(context, data_dict):
    '''Stop following a group.

    :param id: the id or name of the group to stop following
    :type id: string

    '''
    schema = context.get('schema',
            ckan.logic.schema.default_follow_group_schema())
    _unfollow(context, data_dict, schema,
            context['model'].UserFollowingGroup)
