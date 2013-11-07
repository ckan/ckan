'''API functions for adding data to CKAN.'''

import logging

from pylons import config
import paste.deploy.converters

import ckan.lib.plugins as lib_plugins
import ckan.logic as logic
import ckan.rating as ratings
import ckan.plugins as plugins
import ckan.lib.dictization
import ckan.logic.action
import ckan.logic.schema
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.navl.dictization_functions

from ckan.common import _

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
_get_or_bust = logic.get_or_bust

def package_create(context, data_dict):
    '''Create a new dataset (package).

    You must be authorized to create new datasets. If you specify any groups
    for the new dataset, you must also be authorized to edit these groups.

    Plugins may change the parameters of this function depending on the value
    of the ``type`` parameter, see the ``IDatasetForm`` plugin interface.

    :param name: the name of the new dataset, must be between 2 and 100
        characters long and contain only lowercase alphanumeric characters,
        ``-`` and ``_``, e.g. ``'warandpeace'``
    :type name: string
    :param title: the title of the dataset (optional, default: same as
        ``name``)
    :type title: string
    :param author: the name of the dataset's author (optional)
    :type author: string
    :param author_email: the email address of the dataset's author (optional)
    :type author_email: string
    :param maintainer: the name of the dataset's maintainer (optional)
    :type maintainer: string
    :param maintainer_email: the email address of the dataset's maintainer
        (optional)
    :type maintainer_email: string
    :param license_id: the id of the dataset's license, see ``license_list()``
        for available values (optional)
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
    :param type: the type of the dataset (optional), ``IDatasetForm`` plugins
        associate themselves with different dataset types and provide custom
        dataset handling behaviour for these types
    :type type: string
    :param resources: the dataset's resources, see ``resource_create()``
        for the format of resource dictionaries (optional)
    :type resources: list of resource dictionaries
    :param tags: the dataset's tags, see ``tag_create()`` for the format
        of tag dictionaries (optional)
    :type tags: list of tag dictionaries
    :param extras: the dataset's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to datasets, each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string)
    :type extras: list of dataset extra dictionaries
    :param relationships_as_object: see ``package_relationship_create()`` for
        the format of relationship dictionaries (optional)
    :type relationships_as_object: list of relationship dictionaries
    :param relationships_as_subject: see ``package_relationship_create()`` for
        the format of relationship dictionaries (optional)
    :type relationships_as_subject: list of relationship dictionaries
    :param groups: the groups to which the dataset belongs (optional), each
        group dictionary should have one or more of the following keys which
        identify an existing group:
        ``'id'`` (the id of the group, string), ``'name'`` (the name of the
        group, string), ``'title'`` (the title of the group, string), to see
        which groups exist call ``group_list()``
    :type groups: list of dictionaries
    :param owner_org: the id of the dataset's owning organization, see
        ``organization_list()`` or ``organization_list_for_user`` for
        available values (optional)
    :type owner_org: string

    :returns: the newly created dataset (unless 'return_id_only' is set to True
              in the context, in which case just the dataset id will be returned)
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    package_type = data_dict.get('type')
    package_plugin = lib_plugins.lookup_package_plugin(package_type)
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

    data, errors = _validate(data_dict, schema, context)
    log.debug('package_create validate_errs=%r user=%s package=%s data=%r',
              errors, context.get('user'),
              data.get('name'), data_dict)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create object %s') % data.get("name")

    pkg = model_save.package_dict_save(data, context)
    admins = []
    if user:
        admins = [model.User.by_name(user.decode('utf8'))]

    model.setup_default_user_roles(pkg, admins)
    # Needed to let extensions know the package id
    model.Session.flush()
    data['id'] = pkg.id

    context_org_update = context.copy()
    context_org_update['ignore_auth'] = True
    context_org_update['defer_commit'] = True
    _get_action('package_owner_org_update')(context_org_update,
                                            {'id': pkg.id,
                                             'organization_id': pkg.owner_org})

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.create(pkg)

        item.after_create(context, data)

    if not context.get('defer_commit'):
        model.repo.commit()

    ## need to let rest api create
    context["package"] = pkg
    ## this is added so that the rest controller can make a new location
    context["id"] = pkg.id
    log.debug('Created object %s' % pkg.name)

    # Make sure that a user provided schema is not used on package_show
    context.pop('schema', None)

    return_id_only = context.get('return_id_only', False)

    output = context['id'] if return_id_only \
            else _get_action('package_show')(context, {'id':context['id']})

    return output

def resource_create(context, data_dict):
    '''Appends a new resource to a datasets list of resources.

    :param package_id: id of package that the resource needs should be added to.
    :type package_id: string
    :param url: url of resource
    :type url: string
    :param revision_id: (optional)
    :type revisiion_id: string
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
    :param webstore_url: (optional)
    :type webstore_url: string
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
    :param webstore_last_updated: (optional)
    :type webstore_last_updated: iso date string

    :returns: the newly created resource
    :rtype: dictionary

    '''
    model = context['model']
    user = context['user']

    package_id = _get_or_bust(data_dict, 'package_id')
    data_dict.pop('package_id')

    pkg_dict = _get_action('package_show')(context, {'id': package_id})

    _check_access('resource_create', context, data_dict)

    if not 'resources' in pkg_dict:
        pkg_dict['resources'] = []
    pkg_dict['resources'].append(data_dict)

    try:
        pkg_dict = _get_action('package_update')(context, pkg_dict)
    except ValidationError, e:
        errors = e.error_dict['resources'][-1]
        raise ValidationError(errors)

    return pkg_dict['resources'][-1]


def related_create(context, data_dict):
    '''Add a new related item to a dataset.

    You must provide your API key in the Authorization header.

    :param title: the title of the related item
    :type title: string
    :param type: the type of the related item, e.g. ``'Application'``,
        ``'Idea'`` or ``'Visualisation'``
    :type type: string
    :param id: the id of the related item (optional)
    :type id: string
    :param description: the description of the related item (optional)
    :type description: string
    :param url: the URL to the related item (optional)
    :type url: string
    :param image_url: the URL to the image for the related item (optional)
    :type image_url: string
    :param dataset_id: the name or id of the dataset that the related item
        belongs to (optional)
    :type dataset_id: string

    :returns: the newly created related item
    :rtype: dictionary

    '''
    model = context['model']
    session = context['session']
    user = context['user']
    userobj = model.User.get(user)

    _check_access('related_create', context, data_dict)

    data_dict["owner_id"] = userobj.id
    data, errors = _validate(data_dict,
                            ckan.logic.schema.default_related_schema(),
                            context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    related = model_save.related_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit_and_remove()

    dataset_dict = None
    if 'dataset_id' in data_dict:
        dataset = model.Package.get(data_dict['dataset_id'])
        dataset.related.append( related )
        model.repo.commit_and_remove()
        dataset_dict = ckan.lib.dictization.table_dictize(dataset, context)

    session.flush()

    related_dict = model_dictize.related_dictize(related, context)
    activity_dict = {
            'user_id': userobj.id,
            'object_id': related.id,
            'activity_type': 'new related item',
            }
    activity_dict['data'] = {
            'related': related_dict,
            'dataset': dataset_dict,
    }
    activity_create_context = {
        'model': model,
        'user': user,
        'defer_commit':True,
        'session': session
    }
    activity_create(activity_create_context, activity_dict, ignore_auth=True)
    session.commit()

    context["related"] = related
    context["id"] = related.id
    log.debug('Created object %s' % related.title)
    return related_dict


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
    schema = context.get('schema') or ckan.logic.schema.default_create_relationship_schema()
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
    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Create package relationship: %s %s %s') % (pkg1, rel_type, pkg2)
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

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create member object %s') % data_dict.get('name', '')

    group_id, obj_id, obj_type, capacity = _get_or_bust(data_dict, ['id', 'object', 'object_type', 'capacity'])

    group = model.Group.get(group_id)
    if not group:
        raise NotFound('Group was not found.')

    obj_class = ckan.logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound('%s was not found.' % obj_type.title())

    # User must be able to update the group to add a member to it
    _check_access('group_update', context, data_dict)

    # Look up existing, in case it exists
    member = model.Session.query(model.Member).\
            filter(model.Member.table_name == obj_type).\
            filter(model.Member.table_id == obj.id).\
            filter(model.Member.group_id == group.id).\
            filter(model.Member.state == 'active').first()
    if not member:
        member = model.Member(table_name = obj_type,
                              table_id = obj.id,
                              group_id = group.id,
                              state = 'active')

    member.capacity = capacity

    model.Session.add(member)
    model.repo.commit()

    return model_dictize.member_dictize(member, context)

def _group_or_org_create(context, data_dict, is_org=False):
    model = context['model']
    user = context['user']
    session = context['session']
    parent = context.get('parent', None)
    data_dict['is_organization'] = is_org


    # get the schema
    group_plugin = lib_plugins.lookup_group_plugin(
            group_type=data_dict.get('type'))
    try:
        schema = group_plugin.form_to_db_schema_options({'type':'create',
                                               'api':'api_version' in context,
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

    data, errors = _validate(data_dict, schema, context)
    log.debug('group_create validate_errs=%r user=%s group=%s data_dict=%r',
              errors, context.get('user'), data_dict.get('name'), data_dict)

    if errors:
        session.rollback()
        raise ValidationError(errors)

    rev = model.repo.new_revision()
    rev.author = user

    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create object %s') % data.get("name")

    group = model_save.group_dict_save(data, context)

    if parent:
        parent_group = model.Group.get( parent )
        if parent_group:
            member = model.Member(group=parent_group, table_id=group.id, table_name='group')
            session.add(member)
            log.debug('Group %s is made child of group %s',
                      group.name, parent_group.name)

    if user:
        admins = [model.User.by_name(user.decode('utf8'))]
    else:
        admins = []
    model.setup_default_user_roles(group, admins)
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

    user_id = model.User.by_name(user.decode('utf8')).id

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
        'defer_commit':True,
        'session': session
    }
    logic.get_action('activity_create')(activity_create_context,
            activity_dict, ignore_auth=True)

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
        'ignore_auth': True, # we are not a member of the group at this point
        'session': session
    }
    logic.get_action('member_create')(member_create_context, member_dict)

    log.debug('Created object %s' % group.name)
    return model_dictize.group_dictize(group, context)


def group_create(context, data_dict):
    '''Create a new group.

    You must be authorized to create groups.

    Plugins may change the parameters of this function depending on the value
    of the ``type`` parameter, see the ``IGroupForm`` plugin interface.

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
    :param type: the type of the group (optional), ``IGroupForm`` plugins
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

    :returns: the newly created group
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
    of the ``type`` parameter, see the ``IGroupForm`` plugin interface.

    :param name: the name of the organization, a string between 2 and 100 characters
        long, containing only lowercase alphanumeric characters, ``-`` and
        ``_``
    :type name: string
    :param id: the id of the organization (optional)
    :type id: string
    :param title: the title of the organization (optional)
    :type title: string
    :param description: the description of the organization (optional)
    :type description: string
    :param image_url: the URL to an image to be displayed on the organization's page
        (optional)
    :type image_url: string
    :param state: the current state of the organization, e.g. ``'active'`` or
        ``'deleted'``, only active organizations show up in search results and
        other lists of organizations, this parameter will be ignored if you are not
        authorized to change the state of the organization (optional, default:
        ``'active'``)
    :type state: string
    :param approval_status: (optional)
    :type approval_status: string
    :param extras: the organization's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to organizations, each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string), and optionally ``'deleted'``
    :type extras: list of dataset extra dictionaries
    :param packages: the datasets (packages) that belong to the organization, a list
        of dictionaries each with keys ``'name'`` (string, the id or name of
        the dataset) and optionally ``'title'`` (string, the title of the
        dataset)
    :type packages: list of dictionaries
    :param users: the users that belong to the organization, a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and
        optionally ``'capacity'`` (string, the capacity in which the user is
        a member of the organization)
    :type users: list of dictionaries

    :returns: the newly created organization
    :rtype: dictionary

    '''
    # wrapper for creating organizations
    data_dict['type'] = 'organization'
    _check_access('organization_create', context, data_dict)
    return _group_or_org_create(context, data_dict, is_org=True)


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
        opts_err = _('You must supply a package id or name (parameter "package").')
    elif not rating:
        opts_err = _('You must supply a rating (parameter "rating").')
    else:
        try:
            rating_int = int(rating)
        except ValueError:
            opts_err = _('Rating must be an integer value.')
        else:
            package = model.Package.get(package_ref)
            if rating < ratings.MIN_RATING or rating > ratings.MAX_RATING:
                opts_err = _('Rating must be between %i and %i.') % (ratings.MIN_RATING, ratings.MAX_RATING)
            elif not package:
                opts_err = _('Not found') + ': %r' % package_ref
    if opts_err:
        raise ValidationError(opts_err)

    user = model.User.by_name(user)
    ratings.set_rating(user, package, rating_int)

    package = model.Package.get(package_ref)
    ret_dict = {'rating average':package.get_average_rating(),
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
    :param openid: (optional)
    :type openid: string

    :returns: the newly created yser
    :rtype: dictionary

    '''
    model = context['model']
    schema = context.get('schema') or ckan.logic.schema.default_user_schema()
    session = context['session']

    _check_access('user_create', context, data_dict)

    data, errors = _validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors)

    user = model_save.user_dict_save(data, context)

    # Flush the session to cause user.id to be initialised, because
    # activity_create() (below) needs it.
    session.flush()

    activity_create_context = {
        'model': model,
        'user': context['user'],
        'defer_commit': True,
        'session': session
    }
    activity_dict = {
            'user_id': user.id,
            'object_id': user.id,
            'activity_type': 'new user',
            }
    logic.get_action('activity_create')(activity_create_context,
            activity_dict, ignore_auth=True)

    if not context.get('defer_commit'):
        model.repo.commit()

    # A new context is required for dictizing the newly constructed user in
    # order that all the new user's data is returned, in particular, the
    # api_key.
    #
    # The context is copied so as not to clobber the caller's context dict.
    user_dictize_context = context.copy()
    user_dictize_context['keep_sensitive_data'] = True
    user_dict = model_dictize.user_dictize(user, user_dictize_context)

    context['user_obj'] = user
    context['id'] = user.id
    log.debug('Created user %s' % user.name)
    return user_dict

## Modifications for rest api

def package_create_rest(context, data_dict):

    _check_access('package_create_rest', context, data_dict)

    dictized_package = model_save.package_api_to_dict(data_dict, context)
    dictized_after = _get_action('package_create')(context, dictized_package)

    pkg = context['package']

    package_dict = model_dictize.package_to_api(pkg, context)

    data_dict['id'] = pkg.id

    return package_dict

def group_create_rest(context, data_dict):

    _check_access('group_create_rest', context, data_dict)

    dictized_group = model_save.group_api_to_dict(data_dict, context)
    dictized_after = _get_action('group_create')(context, dictized_group)

    group = context['group']

    group_dict = model_dictize.group_to_api(group, context)

    data_dict['id'] = group.id

    return group_dict

def vocabulary_create(context, data_dict):
    '''Create a new tag vocabulary.

    You must be a sysadmin to create vocabularies.

    :param name: the name of the new vocabulary, e.g. ``'Genre'``
    :type name: string
    :param tags: the new tags to add to the new vocabulary, for the format of
        tag dictionaries see ``tag_create()``
    :type tags: list of tag dictionaries

    :returns: the newly-created vocabulary
    :rtype: dictionary

    '''
    model = context['model']
    schema = context.get('schema') or ckan.logic.schema.default_create_vocabulary_schema()

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

def activity_create(context, activity_dict, ignore_auth=False):
    '''Create a new activity stream activity.

    You must be a sysadmin to create new activities.

    :param user_id: the name or id of the user who carried out the activity,
        e.g. ``'seanh'``
    :type user_id: string
    :param object_id: the name or id of the object of the activity, e.g.
        ``'my_dataset'``
    :param activity_type: the type of the activity, this must be an activity
        type that CKAN knows how to render, e.g. ``'new package'``,
        ``'changed user'``, ``'deleted group'`` etc. (for a full list see
        ``activity_renderers`` in ``ckan/logic/action/get.py``
    :type activity_type: string
    :param data: any additional data about the activity
    :type data: dictionary

    :returns: the newly created activity
    :rtype: dictionary

    '''
    if not paste.deploy.converters.asbool(
            config.get('ckan.activity_streams_enabled', 'true')):
        return

    model = context['model']

    # Any revision_id that the caller attempts to pass in the activity_dict is
    # ignored and overwritten here.
    if getattr(model.Session, 'revision', None):
        activity_dict['revision_id'] = model.Session.revision.id
    else:
        activity_dict['revision_id'] = None

    if not ignore_auth:
        _check_access('activity_create', context, activity_dict)

    schema = context.get('schema') or ckan.logic.schema.default_create_activity_schema()
    data, errors = _validate(activity_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    activity = model_save.activity_dict_save(data, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug("Created '%s' activity" % activity.activity_type)
    return model_dictize.activity_dictize(activity, context)

def package_relationship_create_rest(context, data_dict):
    # rename keys
    key_map = {'id': 'subject',
               'id2': 'object',
               'rel': 'type'}
    # Don't be destructive to enable parameter values for
    # object and type to override the URL parameters.
    data_dict = ckan.logic.action.rename_keys(data_dict, key_map, destructive=False)

    relationship_dict = _get_action('package_relationship_create')(context, data_dict)
    return relationship_dict

def tag_create(context, tag_dict):
    '''Create a new vocabulary tag.

    You must be a sysadmin to create vocabulary tags.

    You can only use this function to create tags that belong to a vocabulary,
    not to create free tags. (To create a new free tag simply add the tag to
    a package, e.g. using the ``package_update`` function.)

    :param name: the name for the new tag, a string between 2 and 100
        characters long containing only alphanumeric characters and ``-``,
        ``_`` and ``.``, e.g. ``'Jazz'``
    :type name: string
    :param vocabulary_id: the name or id of the vocabulary that the new tag
        should be added to, e.g. ``'Genre'``
    :type vocabulary_id: string

    :returns: the newly-created tag
    :rtype: dictionary

    '''
    model = context['model']

    _check_access('tag_create', context, tag_dict)

    schema = context.get('schema') or ckan.logic.schema.default_create_tag_schema()
    data, errors = _validate(tag_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    tag = model_save.tag_dict_save(tag_dict, context)

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
        raise logic.NotAuthorized(_("You must be logged in to follow users"))

    model = context['model']
    session = context['session']

    userobj = model.User.get(context['user'])
    if not userobj:
        raise logic.NotAuthorized(_("You must be logged in to follow users"))

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
        message = _(
                'You are already following {0}').format(name)
        raise ValidationError({'message': message}, error_summary=message)

    follower = model_save.follower_dict_save(validated_data_dict, context,
            model.UserFollowingUser)

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

    if not context.has_key('user'):
        raise logic.NotAuthorized(
                _("You must be logged in to follow a dataset."))

    model = context['model']
    session = context['session']

    userobj = model.User.get(context['user'])
    if not userobj:
        raise logic.NotAuthorized(
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

    username = _get_or_bust(data_dict, 'username')
    role = data_dict.get('role')
    group_id = data_dict.get('id')
    group = model.Group.get(group_id)
    result = session.query(model.User).filter_by(name=username).first()
    if result:
        user_id = result.id
    else:
        message = _(u'User {username} does not exist.').format(username=username)
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
        'session': session
    }
    logic.get_action('member_create')(member_create_context, member_dict)

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
        raise logic.NotAuthorized(
                _("You must be logged in to follow a group."))

    model = context['model']
    session = context['session']

    userobj = model.User.get(context['user'])
    if not userobj:
        raise logic.NotAuthorized(
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
