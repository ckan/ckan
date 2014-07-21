'''API functions for updating existing data in CKAN.'''

import logging
import datetime
import json

from pylons import config
from vdm.sqlalchemy.base import SQLAlchemySession
import paste.deploy.converters as converters

import ckan.plugins as plugins
import ckan.logic as logic
import ckan.logic.schema as schema_
import ckan.lib.dictization as dictization
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions
import ckan.lib.navl.validators as validators
import ckan.lib.plugins as lib_plugins
import ckan.lib.email_notifications as email_notifications
import ckan.lib.search as search
import ckan.lib.uploader as uploader

from ckan.common import _, request

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
    id = _get_or_bust(data_dict, "id")

    session = context['session']
    schema = context.get('schema') or schema_.default_update_related_schema()

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

    dataset_dict = None
    if 'package' in context:
        dataset = context['package']
        dataset_dict = ckan.lib.dictization.table_dictize(dataset, context)

    related_dict = model_dictize.related_dictize(related, context)
    activity_dict = {
        'user_id': context['user'],
        'object_id': related.id,
        'activity_type': 'changed related item',
    }
    activity_dict['data'] = {
        'related': related_dict,
        'dataset': dataset_dict,
    }
    activity_create_context = {
        'model': model,
        'user': context['user'],
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }

    _get_action('activity_create')(activity_create_context, activity_dict)

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

    resource = model.Resource.get(id)
    context["resource"] = resource

    if not resource:
        logging.error('Could not find resource ' + id)
        raise NotFound(_('Resource was not found.'))

    _check_access('resource_update', context, data_dict)
    del context["resource"]

    package_id = resource.resource_group.package.id
    pkg_dict = _get_action('package_show')(context, {'id': package_id})

    for n, p in enumerate(pkg_dict['resources']):
        if p['id'] == id:
            break
    else:
        logging.error('Could not find resource ' + id)
        raise NotFound(_('Resource was not found.'))

    upload = uploader.ResourceUpload(data_dict)

    pkg_dict['resources'][n] = data_dict

    try:
        context['defer_commit'] = True
        context['use_cache'] = False
        pkg_dict = _get_action('package_update')(context, pkg_dict)
        context.pop('defer_commit')
    except ValidationError, e:
        errors = e.error_dict['resources'][n]
        raise ValidationError(errors)

    upload.upload(id, uploader.get_max_resource_size())
    model.repo.commit()
    return _get_action('resource_show')(context, {'id': id})


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

    pkg = model.Package.get(name_or_id)
    if pkg is None:
        raise NotFound(_('Package was not found.'))
    context["package"] = pkg
    data_dict["id"] = pkg.id

    _check_access('package_update', context, data_dict)

    # get the schema
    package_plugin = lib_plugins.lookup_package_plugin(pkg.type)
    if 'schema' in context:
        schema = context['schema']
    else:
        schema = package_plugin.update_package_schema()

    if 'api_version' not in context:
        # check_data_dict() is deprecated. If the package_plugin has a
        # check_data_dict() we'll call it, if it doesn't have the method we'll
        # do nothing.
        check_data_dict = getattr(package_plugin, 'check_data_dict', None)
        if check_data_dict:
            try:
                package_plugin.check_data_dict(data_dict, schema)
            except TypeError:
                # Old plugins do not support passing the schema so we need
                # to ensure they still work.
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

    #avoid revisioning by updating directly
    model.Session.query(model.Package).filter_by(id=pkg.id).update(
        {"metadata_modified": datetime.datetime.utcnow()})
    model.Session.refresh(pkg)

    pkg = model_save.package_dict_save(data, context)

    context_org_update = context.copy()
    context_org_update['ignore_auth'] = True
    context_org_update['defer_commit'] = True
    _get_action('package_owner_org_update')(context_org_update,
                                            {'id': pkg.id,
                                             'organization_id': pkg.owner_org})

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.edit(pkg)

        item.after_update(context, data)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug('Updated object %s' % pkg.name)

    return_id_only = context.get('return_id_only', False)

    # Make sure that a user provided schema is not used on package_show
    context.pop('schema', None)

    # we could update the dataset so we should still be able to read it.
    context['ignore_auth'] = True
    output = data_dict['id'] if return_id_only \
            else _get_action('package_show')(context, {'id': data_dict['id']})

    return output

def package_resource_reorder(context, data_dict):
    '''Reorder resources against datasets.  If only partial resource ids are
    supplied then these are assumed to be first and the other resources will
    stay in their original order

    :param id: the id or name of the package to update
    :type id: string
    :param order: a list of resource ids in the order needed
    :type list: list
    '''

    id = _get_or_bust(data_dict, "id")
    order = _get_or_bust(data_dict, "order")
    if not isinstance(order, list):
        raise ValidationError({'order': 'Must be a list of resource'})

    if len(set(order)) != len(order):
        raise ValidationError({'order': 'Must supply unique resource_ids'})

    package_dict = _get_action('package_show')(context, {'id': id})
    existing_resources = package_dict.get('resources', [])
    ordered_resources = []

    for resource_id in order:
        for i in range(0, len(existing_resources)):
            if existing_resources[i]['id'] == resource_id:
                resource = existing_resources.pop(i)
                ordered_resources.append(resource)
                break
        else:
            raise ValidationError(
                {'order':
                 'resource_id {id} can not be found'.format(id=resource_id)}
            )

    new_resources = ordered_resources + existing_resources
    package_dict['resources'] = new_resources

    _check_access('package_resource_reorder', context, package_dict)
    _get_action('package_update')(context, package_dict)

    return {'id': id, 'order': [resource['id'] for resource in new_resources]}


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
    schema = context.get('schema') or schema_.default_update_relationship_schema()

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

def _group_or_org_update(context, data_dict, is_org=False):
    model = context['model']
    user = context['user']
    session = context['session']
    id = _get_or_bust(data_dict, 'id')

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

    upload = uploader.Upload('group', group.image_url)
    upload.update_data_dict(data_dict, 'image_url',
                           'image_upload', 'clear_upload')

    if is_org:
        _check_access('organization_update', context, data_dict)
    else:
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

    # when editing an org we do not want to update the packages if using the
    # new templates.
    if ((not is_org)
            and not converters.asbool(
                config.get('ckan.legacy_templates', False))
            and 'api_version' not in context):
        context['prevent_packages_update'] = True
    group = model_save.group_dict_save(data, context)

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.edit(group)

    if is_org:
        activity_type = 'changed organization'
    else:
        activity_type = 'changed group'

    activity_dict = {
            'user_id': model.User.by_name(user.decode('utf8')).id,
            'object_id': group.id,
            'activity_type': activity_type,
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
                'group': dictization.table_dictize(group, context)
                }
        activity_create_context = {
            'model': model,
            'user': user,
            'defer_commit': True,
            'ignore_auth': True,
            'session': session
        }
        _get_action('activity_create')(activity_create_context, activity_dict)
        # TODO: Also create an activity detail recording what exactly changed
        # in the group.

    upload.upload(uploader.get_max_image_size())
    if not context.get('defer_commit'):
        model.repo.commit()


    return model_dictize.group_dictize(group, context)

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
    return _group_or_org_update(context, data_dict)

def organization_update(context, data_dict):
    '''Update a organization.

    You must be authorized to edit the organization.

    For further parameters see ``organization_create()``.

    :param id: the name or id of the organization to update
    :type id: string

    :returns: the updated organization
    :rtype: dictionary

    '''
    return _group_or_org_update(context, data_dict, is_org=True)

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
    schema = context.get('schema') or schema_.default_update_user_schema()
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
        'defer_commit': True,
        'ignore_auth': True,
        'session': session
    }
    _get_action('activity_create')(activity_create_context, activity_dict)
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
    schema = context.get('schema') or schema_.default_task_status_schema()

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

    if not (data_dict.get('data') and isinstance(data_dict.get('data'), list)):
        raise ValidationError(
            {'error': 'term_translation_update_many needs to have a '
                      'list of dicts in field data'}
        )

    context['defer_commit'] = True

    action = _get_action('term_translation_update')
    for num, row in enumerate(data_dict['data']):
        action(context, row)

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

    schema = context.get('schema') or schema_.default_update_vocabulary_schema()
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

    The ``user`` parameter must be given.

    You must be authorized to update the domain object.

    To delete all of a user or authorization group's roles for domain object,
    pass an empty list ``[]`` to the ``roles`` parameter.

    :param user: the name or id of the user
    :type user: string
    :param domain_object: the name or id of the domain object (e.g. a package,
        group or authorization group)
    :type domain_object: string
    :param roles: the new roles, e.g. ``['editor']``
    :type roles: list of strings

    :returns: the updated roles of all users for the
        domain object
    :rtype: dictionary

    '''
    model = context['model']

    new_user_ref = data_dict.get('user') # the user who is being given the new role
    if not bool(new_user_ref):
        raise ValidationError('You must provide the "user" parameter.')
    domain_object_ref = _get_or_bust(data_dict, 'domain_object')
    if not isinstance(data_dict['roles'], (list, tuple)):
        raise ValidationError('Parameter "%s" must be of type: "%s"' % ('role', 'list'))
    desired_roles = set(data_dict['roles'])

    if new_user_ref:
        user_object = model.User.get(new_user_ref)
        if not user_object:
            raise NotFound('Cannot find user %r' % new_user_ref)
        data_dict['user'] = user_object.id
        add_user_to_role_func = model.add_user_to_role
        remove_user_from_role_func = model.remove_user_from_role

    domain_object = logic.action.get_domain_object(model, domain_object_ref)
    data_dict['id'] = domain_object.id

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
    # Collate all the roles for each user
    roles_by_user = {} # user:roles
    for user_role_dict in data_dict['user_roles']:
        user = user_role_dict.get('user')
        if user:
            roles = user_role_dict['roles']
            if user not in roles_by_user:
                roles_by_user[user] = []
            roles_by_user[user].extend(roles)
    # For each user, update its roles
    for user in roles_by_user:
        uro_data_dict = {'user': user,
                         'roles': roles_by_user[user],
                         'domain_object': data_dict['domain_object']}
        user_role_update(context, uro_data_dict)
    return _get_action('roles_show')(context, data_dict)


def dashboard_mark_activities_old(context, data_dict):
    '''Mark all the authorized user's new dashboard activities as old.

    This will reset dashboard_new_activities_count to 0.

    '''
    _check_access('dashboard_mark_activities_old', context,
            data_dict)
    model = context['model']
    user_id = model.User.get(context['user']).id
    model.Dashboard.get(user_id).activity_stream_last_viewed = (
            datetime.datetime.now())
    if not context.get('defer_commit'):
        model.repo.commit()


@logic.auth_audit_exempt
def send_email_notifications(context, data_dict):
    '''Send any pending activity stream notification emails to users.

    You must provide a sysadmin's API key in the Authorization header of the
    request, or call this action from the command-line via a `paster post ...`
    command.

    '''
    # If paste.command_request is True then this function has been called
    # by a `paster post ...` command not a real HTTP request, so skip the
    # authorization.
    if not request.environ.get('paste.command_request'):
        _check_access('send_email_notifications', context, data_dict)

    if not converters.asbool(
            config.get('ckan.activity_streams_email_notifications')):
        raise ValidationError('ckan.activity_streams_email_notifications'
                              ' is not enabled in config')

    email_notifications.get_and_send_notifications_for_all_users()


def package_owner_org_update(context, data_dict):
    '''Update the owning organization of a dataset

    :param id: the name or id of the dataset to update
    :type id: string

    :param organization_id: the name or id of the owning organization
    :type id: string
    '''
    model = context['model']
    name_or_id = data_dict.get('id')
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
            member_obj.save()

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


def _bulk_update_dataset(context, data_dict, update_dict):
    ''' Bulk update shared code for organizations'''

    datasets = data_dict.get('datasets', [])
    org_id = data_dict.get('org_id')

    model = context['model']

    model.Session.query(model.package_table) \
        .filter(model.Package.id.in_(datasets)) \
        .filter(model.Package.owner_org == org_id) \
        .update(update_dict, synchronize_session=False)

    # revisions
    model.Session.query(model.package_revision_table) \
        .filter(model.PackageRevision.id.in_(datasets)) \
        .filter(model.PackageRevision.owner_org == org_id) \
        .filter(model.PackageRevision.current == True) \
        .update(update_dict, synchronize_session=False)

    model.Session.commit()

    # solr update here
    psi = search.PackageSearchIndex()

    # update the solr index in batches
    BATCH_SIZE = 50

    def process_solr(q):
        # update the solr index for the query
        query = search.PackageSearchQuery()
        q = {
            'q': q,
            'fl': 'data_dict',
            'wt': 'json',
            'fq': 'site_id:"%s"' % config.get('ckan.site_id'),
            'rows': BATCH_SIZE
        }

        for result in query.run(q)['results']:
            data_dict = json.loads(result['data_dict'])
            if data_dict['owner_org'] == org_id:
                data_dict.update(update_dict)
                psi.index_package(data_dict, defer_commit=True)

    count = 0
    q = []
    for id in datasets:
        q.append('id:"%s"' % (id))
        count += 1
        if count % BATCH_SIZE == 0:
            process_solr(' OR '.join(q))
            q = []
    if len(q):
        process_solr(' OR '.join(q))
    # finally commit the changes
    psi.commit()


def bulk_update_private(context, data_dict):
    ''' Make a list of datasets private

    :param datasets: list of ids of the datasets to update
    :type datasets: list of strings

    :param org_id: id of the owning organization
    :type org_id: int
    '''

    _check_access('bulk_update_private', context, data_dict)
    _bulk_update_dataset(context, data_dict, {'private': True})

def bulk_update_public(context, data_dict):
    ''' Make a list of datasets public

    :param datasets: list of ids of the datasets to update
    :type datasets: list of strings

    :param org_id: id of the owning organization
    :type org_id: int
    '''

    _check_access('bulk_update_public', context, data_dict)
    _bulk_update_dataset(context, data_dict, {'private': False})

def bulk_update_delete(context, data_dict):
    ''' Make a list of datasets deleted

    :param datasets: list of ids of the datasets to update
    :type datasets: list of strings

    :param org_id: id of the owning organization
    :type org_id: int
    '''

    _check_access('bulk_update_delete', context, data_dict)
    _bulk_update_dataset(context, data_dict, {'state': 'deleted'})
