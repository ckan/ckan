import logging
import re
import datetime

from ckan.plugins import PluginImplementations, IGroupController, IPackageController
from ckan.logic import NotFound, ValidationError, ParameterError
from ckan.logic import check_access

from ckan.lib.base import _
from vdm.sqlalchemy.base import SQLAlchemySession
import ckan.lib.dictization
from ckan.lib.dictization.model_dictize import (package_dictize,
                                                package_to_api1,
                                                package_to_api2,
                                                resource_dictize,
                                                task_status_dictize,
                                                group_dictize,
                                                group_to_api1,
                                                group_to_api2,
                                                user_dictize)
from ckan.lib.dictization.model_save import (group_api_to_dict,
                                             package_api_to_dict,
                                             group_dict_save,
                                             user_dict_save,
                                             task_status_dict_save,
                                             package_dict_save,
                                             resource_dict_save)
from ckan.logic.schema import (default_update_group_schema,
                               default_update_package_schema,
                               default_update_user_schema,
                               default_update_resource_schema,
                               default_update_relationship_schema,
                               default_task_status_schema)
from ckan.lib.navl.dictization_functions import validate
from ckan.logic.action import rename_keys, get_domain_object
from ckan.logic.action.get import roles_show

log = logging.getLogger(__name__)

def prettify(field_name):
    field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL', field_name.replace('_', ' ').capitalize())
    return _(field_name.replace('_', ' '))

def package_error_summary(error_dict):

    error_summary = {}
    for key, error in error_dict.iteritems():
        if key == 'resources':
            error_summary[_('Resources')] = _('Package resource(s) invalid')
        elif key == 'extras':
            error_summary[_('Extras')] = _('Missing Value')
        elif key == 'extras_validation':
            error_summary[_('Extras')] = error[0]
        else:
            error_summary[_(prettify(key))] = error[0]
    return error_summary

def resource_error_summary(error_dict):

    error_summary = {}
    for key, error in error_dict.iteritems():
        if key == 'extras':
            error_summary[_('Extras')] = _('Missing Value')
        elif key == 'extras_validation':
            error_summary[_('Extras')] = error[0]
        else:
            error_summary[_(prettify(key))] = error[0]
    return error_summary

def group_error_summary(error_dict):

    error_summary = {}
    for key, error in error_dict.iteritems():
        if key == 'extras':
            error_summary[_('Extras')] = _('Missing Value')
        elif key == 'extras_validation':
            error_summary[_('Extras')] = error[0]
        else:
            error_summary[_(prettify(key))] = error[0]
    return error_summary

def task_status_error_summary(error_dict):
    error_summary = {}
    for key, error in error_dict.iteritems():
        error_summary[_(prettify(key))] = error[0]
    return error_summary

def relationship_error_summary(error_dict):
    error_summary = {}
    for key, error in error_dict.iteritems():
        error_summary[_(prettify(key))] = error[0]
    return error_summary

def _make_latest_rev_active(context, q):

    session = context['model'].Session

    old_current = q.filter_by(current=True).first()
    if old_current:
        old_current.current = False
        session.add(old_current)

    latest_rev = q.filter_by(expired_timestamp=datetime.datetime(9999, 12, 31)).one()
    latest_rev.current = True
    if latest_rev.state in ('pending-deleted', 'deleted'):
        latest_rev.state = 'deleted'
        latest_rev.continuity.state = 'deleted'
    else:
        latest_rev.continuity.state = 'active'
        latest_rev.state = 'active'

    session.add(latest_rev)
        
    ##this is just a way to get the latest revision that changed
    ##in order to timestamp
    old_latest = context.get('latest_revision_date')
    if old_latest:
        if latest_rev.revision_timestamp > old_latest:
            context['latest_revision_date'] = latest_rev.revision_timestamp
            context['latest_revision'] = latest_rev.revision_id
    else:
        context['latest_revision_date'] = latest_rev.revision_timestamp
        context['latest_revision'] = latest_rev.revision_id

def make_latest_pending_package_active(context, data_dict):

    model = context['model']
    session = model.Session
    SQLAlchemySession.setattr(session, 'revisioning_disabled', True)
    id = data_dict["id"]
    pkg = model.Package.get(id)

    check_access('make_latest_pending_package_active', context, data_dict)

    #packages
    q = session.query(model.PackageRevision).filter_by(id=pkg.id)
    _make_latest_rev_active(context, q)

    #resources
    for resource in pkg.resource_groups_all[0].resources_all:
        q = session.query(model.ResourceRevision).filter_by(id=resource.id)
        _make_latest_rev_active(context, q)

    #tags
    for tag in pkg.package_tag_all:
        q = session.query(model.PackageTagRevision).filter_by(id=tag.id)
        _make_latest_rev_active(context, q)

    #extras
    for extra in pkg.extras_list:
        q = session.query(model.PackageExtraRevision).filter_by(id=extra.id)
        _make_latest_rev_active(context, q)

    latest_revision = context.get('latest_revision')
    if not latest_revision:
        return

    q = session.query(model.Revision).filter_by(id=latest_revision)
    revision = q.first()
    revision.approved_timestamp = datetime.datetime.now()
    session.add(revision)
    
    if not context.get('defer_commit'):
        session.commit()        
    session.remove()        


def resource_update(context, data_dict):
    model = context['model']
    session = context['session']
    user = context['user']
    id = data_dict["id"]
    schema = context.get('schema') or default_update_resource_schema()
    model.Session.remove()

    resource = model.Resource.get(id)
    context["resource"] = resource

    if not resource:
        logging.error('Could not find resource ' + id)
        raise NotFound(_('Resource was not found.'))

    check_access('resource_update', context, data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, resource_error_summary(errors))

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update object %s') % data.get("name", "")

    resource = resource_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()        
    return resource_dictize(resource, context)


def package_update(context, data_dict):
    model = context['model']
    user = context['user']
    
    id = data_dict["id"]
    schema = context.get('schema') or default_update_package_schema()
    model.Session.remove()
    model.Session()._context = context

    pkg = model.Package.get(id)
    context["package"] = pkg

    if pkg is None:
        raise NotFound(_('Package was not found.'))
    data_dict["id"] = pkg.id

    check_access('package_update', context, data_dict)

    data, errors = validate(data_dict, schema, context)
    

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, package_error_summary(errors))

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update object %s') % data.get("name")

    pkg = package_dict_save(data, context)

    for item in PluginImplementations(IPackageController):
        item.edit(pkg)
    if not context.get('defer_commit'):
        model.repo.commit()        
    return package_dictize(pkg, context)

def package_update_validate(context, data_dict):
    model = context['model']
    user = context['user']
    
    id = data_dict["id"]
    schema = context.get('schema') or default_update_package_schema()
    model.Session.remove()
    model.Session()._context = context

    pkg = model.Package.get(id)
    context["package"] = pkg

    if pkg is None:
        raise NotFound(_('Package was not found.'))
    data_dict["id"] = pkg.id

    check_access('package_update', context, data_dict)

    data, errors = validate(data_dict, schema, context)


    if errors:
        model.Session.rollback()
        raise ValidationError(errors, package_error_summary(errors))
    return data


def _update_package_relationship(relationship, comment, context):
    model = context['model']
    api = context.get('api_version') or '1'
    ref_package_by = 'id' if api == '2' else 'name'
    is_changed = relationship.comment != comment
    if is_changed:
        rev = model.repo.new_revision()
        rev.author = context["user"]
        rev.message = (_(u'REST API: Update package relationship: %s %s %s') % 
            (relationship.subject, relationship.type, relationship.object))
        relationship.comment = comment
        if not context.get('defer_commit'):
            model.repo.commit_and_remove()
    rel_dict = relationship.as_dict(package=relationship.subject,
                                    ref_package_by=ref_package_by)
    return rel_dict

def package_relationship_update(context, data_dict):

    model = context['model']
    user = context['user']
    schema = context.get('schema') or default_update_relationship_schema()
    api = context.get('api_version') or '1'

    id = data_dict['subject']
    id2 = data_dict['object']
    rel = data_dict['type']
    ref_package_by = 'id' if api == '2' else 'name'

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('Subject package %r was not found.' % id)
    if not pkg2:
        return NotFound('Object package %r was not found.' % id2)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, relationship_error_summary(errors))

    check_access('package_relationship_update', context, data_dict)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound('This relationship between the packages was not found.')
    entity = existing_rels[0]
    comment = data_dict.get('comment', u'')
    context['relationship'] = entity
    return _update_package_relationship(entity, comment, context)

def group_update(context, data_dict):
    model = context['model']
    user = context['user']
    session = context['session']
    schema = context.get('schema') or default_update_group_schema()
    id = data_dict['id']

    group = model.Group.get(id)
    context["group"] = group
    if group is None:
        raise NotFound('Group was not found.')

    check_access('group_update', context, data_dict)

    data, errors = validate(data_dict, schema, context)
    if errors:
        session.rollback()
        raise ValidationError(errors, group_error_summary(errors))

    rev = model.repo.new_revision()
    rev.author = user
    
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update object %s') % data.get("name")

    group = group_dict_save(data, context)

    for item in PluginImplementations(IGroupController):
        item.edit(group)

    activity_dict = {
            'user_id': model.User.by_name(user.decode('utf8')).id,
            'object_id': group.id,
            'activity_type': 'changed group',
            }
    # Handle 'deleted' groups.
    # When the user marks a group as deleted this comes through here as
    # a 'changed' group activity. We detect this and change it to a 'deleted'
    # activity.
    if group.state == u'deleted':
        if session.query(ckan.model.Activity).filter_by(
                object_id=group.id, activity_type='deleted').all():
            # A 'deleted group' activity for this group has already been
            # emitted.
            # FIXME: What if the group was deleted and then activated again?
            activity_dict = None
        else:
            # We will emit a 'deleted group' activity.
            activity_dict['activity_type'] = 'deleted group'
    if activity_dict is not None:
        activity_dict['data'] = {
                'group': ckan.lib.dictization.table_dictize(group, context)
                }
        from ckan.logic.action.create import activity_create
        activity_create_context = {
            'model': model,
            'user': user,
            'defer_commit':True,
            'session': session
        }
        activity_create(activity_create_context, activity_dict,
                ignore_auth=True)
        # TODO: Also create an activity detail recording what exactly changed
        # in the group.

    if not context.get('defer_commit'):
        model.repo.commit()        

    return group_dictize(group, context)

def user_update(context, data_dict):
    '''Updates the user\'s details'''

    model = context['model']
    user = context['user']
    session = context['session']
    schema = context.get('schema') or default_update_user_schema() 
    id = data_dict['id']

    user_obj = model.User.get(id)
    context['user_obj'] = user_obj
    if user_obj is None:
        raise NotFound('User was not found.')

    check_access('user_update', context, data_dict)

    data, errors = validate(data_dict, schema, context)
    if errors:
        session.rollback()
        raise ValidationError(errors, group_error_summary(errors))

    user = user_dict_save(data, context)

    activity_dict = {
            'user_id': user.id,
            'object_id': user.id,
            'activity_type': 'changed user',
            }
    activity_create_context = {
        'model': model,
        'user': user,
        'defer_commit':True,
        'session': session
    }
    from ckan.logic.action.create import activity_create
    activity_create(activity_create_context, activity_dict, ignore_auth=True)
    # TODO: Also create an activity detail recording what exactly changed in
    # the user.

    if not context.get('defer_commit'):
        model.repo.commit()        
    return user_dictize(user, context)

def task_status_update(context, data_dict):
    model = context['model']
    session = model.meta.create_local_session()
    context['session'] = session

    user = context['user']
    id = data_dict.get("id")
    schema = context.get('schema') or default_task_status_schema()

    if id:
        task_status = model.TaskStatus.get(id)
        context["task_status"] = task_status

        if task_status is None:
            raise NotFound(_('TaskStatus was not found.'))
    
    check_access('task_status_update', context, data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors, task_status_error_summary(errors))

    task_status = task_status_dict_save(data, context)

    session.commit()
    session.close()
    return task_status_dictize(task_status, context)

def task_status_update_many(context, data_dict):
    results = []
    model = context['model']
    deferred = context.get('defer_commit')
    context['defer_commit'] = True
    for data in data_dict['data']:
        results.append(task_status_update(context, data))
    if not deferred:
        context.pop('defer_commit')
    if not context.get('defer_commit'):
        model.Session.commit()
    return {'results': results}

## Modifications for rest api

def package_update_rest(context, data_dict):

    model = context['model']
    id = data_dict.get("id")
    request_id = context['id']
    api = context.get('api_version') or '1'
    pkg = model.Package.get(request_id)

    if not pkg:
        raise NotFound


    if id and id != pkg.id:
        pkg_from_data = model.Package.get(id)
        if pkg_from_data != pkg:
            error_dict = {id:('Cannot change value of key from %s to %s. '
                'This key is read-only') % (pkg.id, id)}
            raise ValidationError(error_dict)

    context["package"] = pkg
    context["allow_partial_update"] = True
    dictized_package = package_api_to_dict(data_dict, context)

    check_access('package_update_rest', context, dictized_package)

    dictized_after = package_update(context, dictized_package)


    pkg = context['package']

    if api == '1':
        package_dict = package_to_api1(pkg, context)
    else:
        package_dict = package_to_api2(pkg, context)

    return package_dict

def group_update_rest(context, data_dict):

    model = context['model']
    id = data_dict["id"]
    api = context.get('api_version') or '1'
    group = model.Group.get(id)
    context["group"] = group
    context["allow_partial_update"] = True
    dictized_group = group_api_to_dict(data_dict, context)

    check_access('group_update_rest', context, dictized_group)

    dictized_after = group_update(context, dictized_group)

    group = context['group']


    if api == '1':
        group_dict = group_to_api1(group, context)
    else:
        group_dict = group_to_api2(group, context)

    return group_dict

def package_relationship_update_rest(context, data_dict):

    # rename keys
    key_map = {'id': 'subject',
               'id2': 'object',
               'rel': 'type'}

    # We want 'destructive', so that the value of the subject,
    # object and rel in the URI overwrite any values for these
    # in params. This is because you are not allowed to change
    # these values.
    data_dict = rename_keys(data_dict, key_map, destructive=True)

    relationship_dict = package_relationship_update(context, data_dict)

    return relationship_dict

def user_role_update(context, data_dict):
    '''
    For a named user (or authz group), set his/her authz roles on a domain_object.
    '''
    model = context['model']
    user = context['user'] # the current user, who is making the authz change

    new_user_ref = data_dict.get('user') # the user who is being given the new role
    new_authgroup_ref = data_dict.get('authorization_group') # the authgroup who is being given the new role
    if bool(new_user_ref) == bool(new_authgroup_ref):
        raise ParameterError('You must provide either "user" or "authorization_group" parameter.')
    domain_object_ref = data_dict['domain_object']
    if not isinstance(data_dict['roles'], (list, tuple)):
        raise ParameterError('Parameter "%s" must be of type: "%s"' % ('role', 'list'))
    desired_roles = set(data_dict['roles'])

    if new_user_ref:
        user_object = model.User.get(new_user_ref)
        if not user_object:
            raise NotFound('Cannot find user %r' % new_user_ref)
        data_dict['user'] = user_object.id
        add_user_to_role_func = model.add_user_to_role
        remove_user_from_role_func = model.remove_user_from_role
    else:
        user_object = model.AuthorizationGroup.get(new_authgroup_ref)
        if not user_object:
            raise NotFound('Cannot find authorization group %r' % new_authgroup_ref)        
        data_dict['authorization_group'] = user_object.id
        add_user_to_role_func = model.add_authorization_group_to_role
        remove_user_from_role_func = model.remove_authorization_group_from_role

    domain_object = get_domain_object(model, domain_object_ref)
    data_dict['id'] = domain_object.id
    if isinstance(domain_object, model.Package):
        check_access('package_edit_permissions', context, data_dict)
    elif isinstance(domain_object, model.Group):
        check_access('group_edit_permissions', context, data_dict)
    elif isinstance(domain_object, model.AuthorizationGroup):
        check_access('authorization_group_edit_permissions', context, data_dict)
    # Todo: 'system' object
    else:
        raise ParameterError('Not possible to update roles for domain object type %s' % type(domain_object))

    # current_uors: in order to avoid either creating a role twice or
    # deleting one which is non-existent, we need to get the users\'
    # current roles (if any)
    current_role_dicts = roles_show(context, data_dict)['roles']
    current_roles = set([role_dict['role'] for role_dict in current_role_dicts])

    # Whenever our desired state is different from our current state,
    # change it.
    for role in (desired_roles - current_roles):
        add_user_to_role_func(user_object, role, domain_object)
    for role in (current_roles - desired_roles):
        remove_user_from_role_func(user_object, role, domain_object)

    # and finally commit all these changes to the database
    if not (current_roles == desired_roles):
        model.repo.commit_and_remove()

    return roles_show(context, data_dict)

def user_role_bulk_update(context, data_dict):
    '''
    For a given domain_object, update authz roles that several users have on it.
    To delete all roles for a user on a domain object, set {roles: []}.
    '''
    for user_or_authgroup in ('user', 'authorization_group'):
        # Collate all the roles for each user
        roles_by_user = {} # user:roles
        for user_role_dict in data_dict['user_roles']:
            user = user_role_dict.get(user_or_authgroup)
            if user:
                roles = user_role_dict['roles']
                if user not in roles_by_user:
                    roles_by_user[user] = []
                roles_by_user[user].extend(roles)
        # For each user, update its roles
        for user in roles_by_user:
            uro_data_dict = {user_or_authgroup: user,
                             'roles': roles_by_user[user],
                             'domain_object': data_dict['domain_object']}
            user_role_update(context, uro_data_dict)
    return roles_show(context, data_dict)

