# encoding: utf-8

'''API functions for deleting data from CKAN.'''

import logging

import sqlalchemy as sqla
import six

import ckan.lib.jobs as jobs
import ckan.logic
import ckan.logic.action
import ckan.plugins as plugins
import ckan.lib.dictization as dictization
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.api_token as api_token
from ckan import authz

from ckan.common import _


log = logging.getLogger('ckan.logic')

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

    user_memberships = model.Session.query(model.Member).filter(
        model.Member.table_id == user.id).all()

    for membership in user_memberships:
        membership.delete()

    datasets_where_user_is_collaborator = model.Session.query(model.PackageMember).filter(
            model.PackageMember.user_id == user.id).all()
    for collaborator in datasets_where_user_is_collaborator:
        collaborator.delete()

    model.repo.commit()


def package_delete(context, data_dict):
    '''Delete a dataset (package).

    This makes the dataset disappear from all web & API views, apart from the
    trash.

    You must be authorized to delete the dataset.

    :param id: the id or name of the dataset to delete
    :type id: string

    '''
    model = context['model']
    session = context['session']
    user = context['user']
    id = _get_or_bust(data_dict, 'id')

    entity = model.Package.get(id)

    if entity is None:
        raise NotFound

    _check_access('package_delete', context, data_dict)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.delete(entity)

        item.after_delete(context, data_dict)

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

    # Create activity
    if not entity.private:
        user_obj = model.User.by_name(user)
        if user_obj:
            user_id = user_obj.id
        else:
            user_id = 'not logged in'

        activity = entity.activity_stream_item('changed', user_id)
        session.add(activity)

    model.repo.commit()


def dataset_purge(context, data_dict):
    '''Purge a dataset.

    .. warning:: Purging a dataset cannot be undone!

    Purging a database completely removes the dataset from the CKAN database,
    whereas deleting a dataset simply marks the dataset as deleted (it will no
    longer show up in the front-end, but is still in the db).

    You must be authorized to purge the dataset.

    :param id: the name or id of the dataset to be purged
    :type id: string

    '''
    from sqlalchemy import or_

    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    pkg = model.Package.get(id)
    context['package'] = pkg
    if pkg is None:
        raise NotFound('Dataset was not found')

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
    pkg.purge()
    model.repo.commit_and_remove()


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

    package_show_context = dict(context, for_update=True)
    pkg_dict = _get_action('package_show')(package_show_context, {'id': package_id})

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.before_delete(context, data_dict,
                             pkg_dict.get('resources', []))

    pkg_dict = _get_action('package_show')(context, {'id': package_id})

    if pkg_dict.get('resources'):
        pkg_dict['resources'] = [r for r in pkg_dict['resources'] if not
                r['id'] == id]
    try:
        pkg_dict = _get_action('package_update')(context, pkg_dict)
    except ValidationError as e:
        errors = e.error_dict['resources'][-1]
        raise ValidationError(errors)

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.after_delete(context, pkg_dict.get('resources', []))

    model.repo.commit()


def resource_view_delete(context, data_dict):
    '''Delete a resource_view.

    :param id: the id of the resource_view
    :type id: string

    '''
    model = context['model']
    id = _get_or_bust(data_dict, 'id')

    resource_view = model.ResourceView.get(id)
    if not resource_view:
        raise NotFound

    context["resource_view"] = resource_view
    context['resource'] = model.Resource.get(resource_view.resource_id)
    _check_access('resource_view_delete', context, data_dict)

    resource_view.delete()
    model.repo.commit()


def resource_view_clear(context, data_dict):
    '''Delete all resource views, or all of a particular type.

    :param view_types: specific types to delete (optional)
    :type view_types: list

    '''
    model = context['model']

    _check_access('resource_view_clear', context, data_dict)

    view_types = data_dict.get('view_types')
    model.ResourceView.delete_all(view_types)
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

    relationship.delete()
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
        member.delete()
        model.repo.commit()


def package_collaborator_delete(context, data_dict):
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

    model = context['model']

    package_id, user_id = _get_or_bust(
        data_dict,
        ['id', 'user_id']
    )

    _check_access('package_collaborator_delete', context, data_dict)

    if not authz.check_config_permission('allow_dataset_collaborators'):
        raise ValidationError(_('Dataset collaborators not enabled'))

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

    log.info('User {} removed as collaborator from package {}'.format(
        user_id, package.id))


def _group_or_org_delete(context, data_dict, is_org=False):
    '''Delete a group.

    You must be authorized to delete the group.

    :param id: the name or id of the group
    :type id: string

    '''
    from sqlalchemy import or_

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

    # organization delete will not occur while all datasets for that org are
    # not deleted
    if is_org:
        datasets = model.Session.query(model.Package) \
                        .filter_by(owner_org=group.id) \
                        .filter(model.Package.state != 'deleted') \
                        .count()
        if datasets:
            if not authz.check_config_permission('ckan.auth.create_unowned_dataset'):
                raise ValidationError(_('Organization cannot be deleted while it '
                                      'still has datasets'))

            pkg_table = model.package_table
            # using Core SQLA instead of the ORM should be faster
            model.Session.execute(
                pkg_table.update().where(
                    sqla.and_(pkg_table.c.owner_org == group.id,
                              pkg_table.c.state != 'deleted')
                ).values(owner_org=None)
            )

    # The group's Member objects are deleted
    # (including hierarchy connections to parent and children groups)
    for member in model.Session.query(model.Member).\
            filter(or_(model.Member.table_id == id,
                       model.Member.group_id == id)).\
            filter(model.Member.state == 'active').all():
        member.delete()

    group.delete()

    if is_org:
        activity_type = 'deleted organization'
    else:
        activity_type = 'deleted group'

    activity_dict = {
        'user_id': model.User.by_name(six.ensure_text(user)).id,
        'object_id': group.id,
        'activity_type': activity_type,
        'data': {
            'group': dictization.table_dictize(group, context)
            }
    }
    activity_create_context = {
        'model': model,
        'user': user,
        'defer_commit': True,
        'ignore_auth': True,
        'session': context['session']
    }
    _get_action('activity_create')(activity_create_context, activity_dict)

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

    You must be authorized to delete the organization
    and no datasets should belong to the organization
    unless 'ckan.auth.create_unowned_dataset=True'

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
    :type is_org: bool

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

    if is_org:
        # Clear the owner_org field
        datasets = model.Session.query(model.Package) \
                        .filter_by(owner_org=group.id) \
                        .filter(model.Package.state != 'deleted') \
                        .count()
        if datasets:
            if not authz.check_config_permission('ckan.auth.create_unowned_dataset'):
                raise ValidationError('Organization cannot be purged while it '
                                      'still has datasets')
            pkg_table = model.package_table
            # using Core SQLA instead of the ORM should be faster
            model.Session.execute(
                pkg_table.update().where(
                    sqla.and_(pkg_table.c.owner_org == group.id,
                              pkg_table.c.state != 'deleted')
                ).values(owner_org=None)
            )

    # Delete related Memberships
    members = model.Session.query(model.Member) \
                   .filter(sqla.or_(model.Member.group_id == group.id,
                                    model.Member.table_id == group.id))
    if members.count() > 0:
        for m in members.all():
            m.purge()
        model.repo.commit_and_remove()

    group = model.Group.get(id)
    group.purge()
    model.repo.commit_and_remove()

def group_purge(context, data_dict):
    '''Purge a group.

    .. warning:: Purging a group cannot be undone!

    Purging a group completely removes the group from the CKAN database,
    whereas deleting a group simply marks the group as deleted (it will no
    longer show up in the frontend, but is still in the db).

    Datasets in the organization will remain, just not in the purged group.

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

    Datasets owned by the organization will remain, just not in an
    organization any more.

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

    if 'id' not in data_dict or not data_dict['id']:
        raise ValidationError({'id': _('id not in data')})
    tag_id_or_name = _get_or_bust(data_dict, 'id')

    vocab_id_or_name = data_dict.get('vocabulary_id')

    tag_obj = model.tag.Tag.get(tag_id_or_name, vocab_id_or_name)

    if tag_obj is None:
        raise NotFound(_('Could not find tag "%s"') % tag_id_or_name)

    _check_access('tag_delete', context, data_dict)

    tag_obj.delete()
    model.repo.commit()


def _unfollow(context, data_dict, schema, FollowerClass):
    model = context['model']

    if 'user' not in context:
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


@ckan.logic.validate(ckan.logic.schema.job_clear_schema)
def job_clear(context, data_dict):
    '''Clear background job queues.

    Does not affect jobs that are already being processed.

    :param list queues: The queues to clear. If not given then ALL
        queues are cleared.

    :returns: The cleared queues.
    :rtype: list

    .. versionadded:: 2.7
    '''
    _check_access(u'job_clear', context, data_dict)
    queues = data_dict.get(u'queues')
    if queues:
        queues = [jobs.get_queue(q) for q in queues]
    else:
        queues = jobs.get_all_queues()
    names = [jobs.remove_queue_name_prefix(queue.name) for queue in queues]
    for queue, name in zip(queues, names):
        queue.empty()
        log.info(u'Cleared background job queue "{}"'.format(name))
    return names


def job_cancel(context, data_dict):
    '''Cancel a queued background job.

    Removes the job from the queue and deletes it.

    :param string id: The ID of the background job.

    .. versionadded:: 2.7
    '''
    _check_access(u'job_cancel', context, data_dict)
    id = _get_or_bust(data_dict, u'id')
    try:
        jobs.job_from_id(id).delete()
        log.info(u'Cancelled background job {}'.format(id))
    except KeyError:
        raise NotFound


def api_token_revoke(context, data_dict):
    """Delete API Token.

    :param string token: Token to remove(required if `jti` not specified).
    :param string jti: Id of the token to remove(overrides `token` if specified).

    .. versionadded:: 3.0
    """
    jti = data_dict.get(u'jti')
    if not jti:
        token = _get_or_bust(data_dict, u'token')
        decoders = plugins.PluginImplementations(plugins.IApiToken)
        for plugin in decoders:
            data = plugin.decode_api_token(token)
            if data:
                break
        else:
            data = api_token.decode(token)

        if data:
            jti = data.get(u'jti')

    _check_access(u'api_token_revoke', context, {u'jti': jti})
    model = context[u'model']
    model.ApiToken.revoke(jti)
