import logging
import datetime

from pylons.i18n import _
from vdm.sqlalchemy.base import SQLAlchemySession

import ckan.authz as authz
import ckan.plugins as plugins
import ckan.logic as logic
import ckan.logic.schema
import ckan.lib.dictization
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions
import ckan.lib.navl.validators as validators
import ckan.lib.plugins as lib_plugins

log = logging.getLogger(__name__)

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_validate = ckan.lib.navl.dictization_functions.validate
_get_action = logic.get_action
_check_access = logic.check_access
NotFound = logic.NotFound
ValidationError = logic.ValidationError
_get_or_bust = logic.get_or_bust

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
    '''TODO: What does this function do?

    You must be authorized to update the dataset.

    :param id: the name or id of the dataset, e.g. ``'warandpeace'``
    :type id: string

    '''
    model = context['model']
    session = model.Session
    SQLAlchemySession.setattr(session, 'revisioning_disabled', True)
    id = _get_or_bust(data_dict, "id")
    pkg = model.Package.get(id)

    _check_access('make_latest_pending_package_active', context, data_dict)

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


def related_update(context, data_dict):
    '''Update a related item.

    You must be the owner of a related item to update it.

    For further parameters see ``related_create()``.

    :param id: the id of the related item to update
    :type id: string

    :returns: the updated related item
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']
    id = _get_or_bust(data_dict, "id")

    schema = context.get('schema') or ckan.logic.schema.default_related_schema()
    model.Session.remove()

    related = model.Related.get(id)
    context["related"] = related

    if not related:
        logging.error('Could not find related ' + id)
        raise NotFound(_('Item was not found.'))

    _check_access('related_update', context, data_dict)
    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    related = model_save.related_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    return model_dictize.related_dictize(related, context)



def resource_update(context, data_dict):
    '''Update a resource.

    To update a resource you must be authorized to update the dataset that the
    resource belongs to.

    For further parameters see ``resource_create()``.

    :param id: the id of the resource to update
    :type id: string

    :returns: the updated resource
    :rtype: string

    '''
    model = context['model']
    user = context['user']
    id = _get_or_bust(data_dict, "id")
    schema = context.get('schema') or ckan.logic.schema.default_update_resource_schema()
    model.Session.remove()

    resource = model.Resource.get(id)
    context["resource"] = resource

    if not resource:
        logging.error('Could not find resource ' + id)
        raise NotFound(_('Resource was not found.'))

    _check_access('resource_update', context, data_dict)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update object %s') % data.get("name", "")

    resource = model_save.resource_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit()
    return model_dictize.resource_dictize(resource, context)



def package_update(context, data_dict):
    '''Update a dataset (package).

    You must be authorized to edit the dataset and the groups that it belongs
    to.

    Plugins may change the parameters of this function depending on the value
    of the dataset's ``type`` attribute, see the ``IDatasetForm`` plugin
    interface.

    For further parameters see ``package_create()``.

    :param id: the name or id of the dataset to update
    :type id: string

    :returns: the updated dataset (if 'return_package_dict' is True in the
              context, which is the default. Otherwise returns just the
              dataset id)
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']
    name_or_id = data_dict.get("id") or data_dict['name']
    model.Session.remove()
    model.Session()._context = context

    pkg = model.Package.get(name_or_id)
    if pkg is None:
        raise NotFound(_('Package was not found.'))
    context["package"] = pkg
    data_dict["id"] = pkg.id

    _check_access('package_update', context, data_dict)

    # get the schema
    package_plugin = lib_plugins.lookup_package_plugin(pkg.type)
    try:
        schema = package_plugin.form_to_db_schema_options({'type':'update',
                                               'api':'api_version' in context,
                                               'context': context})
    except AttributeError:
        schema = package_plugin.form_to_db_schema()

    if 'api_version' not in context:
        # old plugins do not support passing the schema so we need
        # to ensure they still work
        try:
            package_plugin.check_data_dict(data_dict, schema)
        except TypeError:
            package_plugin.check_data_dict(data_dict)

    data, errors = _validate(data_dict, schema, context)
    log.debug('package_update validate_errs=%r user=%s package=%s data=%r',
              errors, context.get('user'),
              context.get('package').name if context.get('package') else '',
              data)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update object %s') % data.get("name")

    pkg = model_save.package_dict_save(data, context)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.edit(pkg)
    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug('Updated object %s' % str(pkg.name))

    return_id_only = context.get('return_id_only', False)

    output = data_dict['id'] if return_id_only \
            else _get_action('package_show')(context, {'id': data_dict['id']})

    return output

def package_update_validate(context, data_dict):
    model = context['model']
    user = context['user']

    id = _get_or_bust(data_dict, "id")
    model.Session.remove()
    model.Session()._context = context

    pkg = model.Package.get(id)
    context["package"] = pkg

    if pkg is None:
        raise NotFound(_('Package was not found.'))
    data_dict["id"] = pkg.id

    # get the schema
    package_plugin = lib_plugins.lookup_package_plugin(pkg.type)
    try:
        schema = package_plugin.form_to_db_schema_options({'type':'update',
                                               'api':'api_version' in context,
                                               'context': context})
    except AttributeError:
        schema = package_plugin.form_to_db_schema()

    _check_access('package_update', context, data_dict)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)
    return data


def _update_package_relationship(relationship, comment, context):
    model = context['model']
    api = context.get('api_version')
    ref_package_by = 'id' if api == 2 else 'name'
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
    '''Update a relationship between two datasets (packages).

    You must be authorized to edit both the subject and the object datasets.

    :param id: the id of the package relationship to update
    :type id: string
    :param subject: the name or id of the dataset that is the subject of the
        relationship (optional)
    :type subject: string
    :param object: the name or id of the dataset that is the object of the
        relationship (optional)
    :param type: the type of the relationship, one of ``'depends_on'``,
        ``'dependency_of'``, ``'derives_from'``, ``'has_derivation'``,
        ``'links_to'``, ``'linked_from'``, ``'child_of'`` or ``'parent_of'``
        (optional)
    :type type: string
    :param comment: a comment about the relationship (optional)
    :type comment: string

    :returns: the updated relationship
    :rtype: dictionary

    '''
    model = context['model']
    schema = context.get('schema') or ckan.logic.schema.default_update_relationship_schema()

    id, id2, rel = _get_or_bust(data_dict, ['subject', 'object', 'type'])

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

    _check_access('package_relationship_update', context, data_dict)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound('This relationship between the packages was not found.')
    entity = existing_rels[0]
    comment = data_dict.get('comment', u'')
    context['relationship'] = entity
    return _update_package_relationship(entity, comment, context)

def group_update(context, data_dict):
    '''Update a group.

    You must be authorized to edit the group.

    Plugins may change the parameters of this function depending on the value
    of the group's ``type`` attribute, see the ``IGroupForm`` plugin interface.

    For further parameters see ``group_create()``.

    :param id: the name or id of the group to update
    :type id: string

    :returns: the updated group
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']
    session = context['session']
    id = _get_or_bust(data_dict, 'id')
    parent = context.get('parent', None)

    group = model.Group.get(id)
    context["group"] = group
    if group is None:
        raise NotFound('Group was not found.')

    # get the schema
    group_plugin = lib_plugins.lookup_group_plugin(group.type)
    try:
        schema = group_plugin.form_to_db_schema_options({'type':'update',
                                               'api':'api_version' in context,
                                               'context': context})
    except AttributeError:
        schema = group_plugin.form_to_db_schema()

    _check_access('group_update', context, data_dict)

    if 'api_version' not in context:
        # old plugins do not support passing the schema so we need
        # to ensure they still work
        try:
            group_plugin.check_data_dict(data_dict, schema)
        except TypeError:
            group_plugin.check_data_dict(data_dict)

    data, errors = _validate(data_dict, schema, context)
    log.debug('group_update validate_errs=%r user=%s group=%s data_dict=%r',
              errors, context.get('user'),
              context.get('group').name if context.get('group') else '',
              data_dict)

    if errors:
        session.rollback()
        raise ValidationError(errors)

    rev = model.repo.new_revision()
    rev.author = user

    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Update object %s') % data.get("name")

    group = model_save.group_dict_save(data, context)

    if parent:
        parent_group = model.Group.get( parent )
        if parent_group and not parent_group in group.get_groups(group.type):
            # Delete all of this groups memberships
            current = session.query(model.Member).\
               filter(model.Member.table_id == group.id).\
               filter(model.Member.table_name == "group").all()
            if current:
                log.debug('Parents of group %s deleted: %r', group.name,
                          [membership.group.name for membership in current])
            for c in current:
                session.delete(c)
            member = model.Member(group=parent_group, table_id=group.id, table_name='group')
            session.add(member)
            log.debug('Group %s is made child of group %s',
                      group.name, parent_group.name)


    for item in plugins.PluginImplementations(plugins.IGroupController):
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
        activity_create_context = {
            'model': model,
            'user': user,
            'defer_commit':True,
            'session': session
        }
        _get_action('activity_create')(activity_create_context, activity_dict,
                ignore_auth=True)
        # TODO: Also create an activity detail recording what exactly changed
        # in the group.

    if not context.get('defer_commit'):
        model.repo.commit()

    return model_dictize.group_dictize(group, context)

def user_update(context, data_dict):
    '''Update a user account.

    Normal users can only update their own user accounts. Sysadmins can update
    any user account.

    For further parameters see ``user_create()``.

    :param id: the name or id of the user to update
    :type id: string

    :returns: the updated user account
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']
    session = context['session']
    schema = context.get('schema') or ckan.logic.schema.default_update_user_schema()
    id = _get_or_bust(data_dict, 'id')

    user_obj = model.User.get(id)
    context['user_obj'] = user_obj
    if user_obj is None:
        raise NotFound('User was not found.')

    _check_access('user_update', context, data_dict)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        session.rollback()
        raise ValidationError(errors)

    user = model_save.user_dict_save(data, context)

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
    _get_action('activity_create')(activity_create_context, activity_dict, ignore_auth=True)
    # TODO: Also create an activity detail recording what exactly changed in
    # the user.

    if not context.get('defer_commit'):
        model.repo.commit()
    return model_dictize.user_dictize(user, context)

def task_status_update(context, data_dict):
    '''Update a task status.

    :param id: the id of the task status to update
    :type id: string
    :param entity_id:
    :type entity_id: string
    :param entity_type:
    :type entity_type: string
    :param task_type:
    :type task_type: string
    :param key:
    :type key: string
    :param value: (optional)
    :type value:
    :param state: (optional)
    :type state:
    :param last_updated: (optional)
    :type last_updated:
    :param error: (optional)
    :type error:

    :returns: the updated task status
    :rtype: dictionary

    '''
    model = context['model']
    session = model.meta.create_local_session()
    context['session'] = session

    user = context['user']
    id = data_dict.get("id")
    schema = context.get('schema') or ckan.logic.schema.default_task_status_schema()

    if id:
        task_status = model.TaskStatus.get(id)
        context["task_status"] = task_status

        if task_status is None:
            raise NotFound(_('TaskStatus was not found.'))

    _check_access('task_status_update', context, data_dict)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        session.rollback()
        raise ValidationError(errors)

    task_status = model_save.task_status_dict_save(data, context)

    session.commit()
    session.close()
    return model_dictize.task_status_dictize(task_status, context)

def task_status_update_many(context, data_dict):
    '''Update many task statuses at once.

    :param data: the task_status dictionaries to update, for the format of task
        status dictionaries see ``task_status_update()``
    :type data: list of dictionaries

    :returns: the updated task statuses
    :rtype: list of dictionaries

    '''
    results = []
    model = context['model']
    deferred = context.get('defer_commit')
    context['defer_commit'] = True
    for data in data_dict['data']:
        results.append(_get_action('task_status_update')(context, data))
    if not deferred:
        context.pop('defer_commit')
    if not context.get('defer_commit'):
        model.Session.commit()
    return {'results': results}

def term_translation_update(context, data_dict):
    '''Create or update a term translation.

    You must be a sysadmin to create or update term translations.

    :param term: the term to be translated, in the original language, e.g.
        ``'romantic novel'``
    :type term: string
    :param term_translation: the translation of the term, e.g.
        ``'Liebesroman'``
    :type term_translation: string
    :param lang_code: the language code of the translation, e.g. ``'de'``
    :type lang_code: string

    :returns: the newly created or updated term translation
    :rtype: dictionary

    '''
    model = context['model']

    _check_access('term_translation_update', context, data_dict)

    schema = {'term': [validators.not_empty, unicode],
              'term_translation': [validators.not_empty, unicode],
              'lang_code': [validators.not_empty, unicode]}

    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    trans_table = model.term_translation_table

    update = trans_table.update()
    update = update.where(trans_table.c.term == data['term'])
    update = update.where(trans_table.c.lang_code == data['lang_code'])
    update = update.values(term_translation = data['term_translation'])

    conn = model.Session.connection()
    result = conn.execute(update)

    # insert if not updated
    if not result.rowcount:
        conn.execute(trans_table.insert().values(**data))

    if not context.get('defer_commit'):
        model.Session.commit()

    return data

def term_translation_update_many(context, data_dict):
    '''Create or update many term translations at once.

    :param data: the term translation dictionaries to create or update,
        for the format of term translation dictionaries see
        ``term_translation_update()``
    :type data: list of dictionaries

    :returns: a dictionary with key ``'success'`` whose value is a string
        stating how many term translations were updated
    :rtype: string

    '''
    model = context['model']


    if not data_dict.get('data') and isinstance(data_dict, list):
        raise ValidationError(
            {'error':
             'term_translation_update_many needs to have a list of dicts in field data'}
        )

    context['defer_commit'] = True

    for num, row in enumerate(data_dict['data']):
        term_translation_update(context, row)

    model.Session.commit()

    return {'success': '%s rows updated' % (num + 1)}


## Modifications for rest api

def package_update_rest(context, data_dict):

    model = context['model']
    id = data_dict.get("id")
    request_id = context['id']
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
    context["allow_partial_update"] = False
    dictized_package = model_save.package_api_to_dict(data_dict, context)

    _check_access('package_update_rest', context, dictized_package)

    dictized_after = _get_action('package_update')(context, dictized_package)

    pkg = context['package']

    package_dict = model_dictize.package_to_api(pkg, context)

    return package_dict

def group_update_rest(context, data_dict):

    model = context['model']
    id = _get_or_bust(data_dict, "id")
    group = model.Group.get(id)
    context["group"] = group
    context["allow_partial_update"] = True
    dictized_group = model_save.group_api_to_dict(data_dict, context)

    _check_access('group_update_rest', context, dictized_group)

    dictized_after = _get_action('group_update')(context, dictized_group)

    group = context['group']

    group_dict = model_dictize.group_to_api(group, context)

    return group_dict

def vocabulary_update(context, data_dict):
    '''Update a tag vocabulary.

    You must be a sysadmin to update vocabularies.

    For further parameters see ``vocabulary_create()``.

    :param id: the id of the vocabulary to update
    :type id: string

    :returns: the updated vocabulary
    :rtype: dictionary

    '''
    model = context['model']

    vocab_id = data_dict.get('id')
    if not vocab_id:
        raise ValidationError({'id': _('id not in data')})

    vocab = model.vocabulary.Vocabulary.get(vocab_id)
    if vocab is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)

    data_dict['id'] = vocab.id
    if data_dict.has_key('name'):
        if data_dict['name'] == vocab.name:
            del data_dict['name']

    _check_access('vocabulary_update', context, data_dict)

    schema = context.get('schema') or ckan.logic.schema.default_update_vocabulary_schema()
    data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    updated_vocab = model_save.vocabulary_dict_update(data, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    return model_dictize.vocabulary_dictize(updated_vocab, context)

def package_relationship_update_rest(context, data_dict):

    # rename keys
    key_map = {'id': 'subject',
               'id2': 'object',
               'rel': 'type'}

    # We want 'destructive', so that the value of the subject,
    # object and rel in the URI overwrite any values for these
    # in params. This is because you are not allowed to change
    # these values.
    data_dict = logic.action.rename_keys(data_dict, key_map, destructive=True)

    relationship_dict = _get_action('package_relationship_update')(context, data_dict)

    return relationship_dict

def user_role_update(context, data_dict):
    '''Update a user or authorization group's roles for a domain object.

    Either the ``user`` or the ``authorization_group`` parameter must be given.

    You must be authorized to update the domain object.

    To delete all of a user or authorization group's roles for domain object,
    pass an empty list ``[]`` to the ``roles`` parameter.

    :param user: the name or id of the user
    :type user: string
    :param authorization_group: the name or id of the authorization group
    :type authorization_group: string
    :param domain_object: the name or id of the domain object (e.g. a package,
        group or authorization group)
    :type domain_object: string
    :param roles: the new roles, e.g. ``['editor']``
    :type roles: list of strings

    :returns: the updated roles of all users and authorization_groups for the
        domain object
    :rtype: dictionary

    '''
    model = context['model']

    new_user_ref = data_dict.get('user') # the user who is being given the new role
    new_authgroup_ref = data_dict.get('authorization_group') # the authgroup who is being given the new role
    if bool(new_user_ref) == bool(new_authgroup_ref):
        raise logic.ParameterError('You must provide either "user" or "authorization_group" parameter.')
    domain_object_ref = _get_or_bust(data_dict, 'domain_object')
    if not isinstance(data_dict['roles'], (list, tuple)):
        raise logic.ParameterError('Parameter "%s" must be of type: "%s"' % ('role', 'list'))
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

    domain_object = logic.action.get_domain_object(model, domain_object_ref)
    data_dict['id'] = domain_object.id
    if isinstance(domain_object, model.Package):
        _check_access('package_edit_permissions', context, data_dict)
    elif isinstance(domain_object, model.Group):
        _check_access('group_edit_permissions', context, data_dict)
    elif isinstance(domain_object, model.AuthorizationGroup):
        _check_access('authorization_group_edit_permissions', context, data_dict)
    # Todo: 'system' object
    else:
        raise logic.ParameterError('Not possible to update roles for domain object type %s' % type(domain_object))

    # current_uors: in order to avoid either creating a role twice or
    # deleting one which is non-existent, we need to get the users\'
    # current roles (if any)
    current_role_dicts = _get_action('roles_show')(context, data_dict)['roles']
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

    return _get_action('roles_show')(context, data_dict)

def user_role_bulk_update(context, data_dict):
    '''Update the roles of many users or authorization groups for an object.

    You must be authorized to update the domain object.

    :param user_roles: the updated user roles, for the format of user role
        dictionaries see ``user_role_update()``
    :type user_roles: list of dictionaries

    :returns: the updated roles of all users and authorization groups for the
        domain object
    :rtype: dictionary

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
    return _get_action('roles_show')(context, data_dict)
