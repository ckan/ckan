import logging
from pylons.i18n import _

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
import ckan.logic.auth as auth

# FIXME this looks nasty and should be shared better
from ckan.logic.action.update import _update_package_relationship

log = logging.getLogger(__name__)

# define some shortcuts
error_summary = ckan.logic.action.error_summary
validate = ckan.lib.navl.dictization_functions.validate
check_access = logic.check_access
get_action = logic.get_action
ValidationError = logic.ValidationError
NotFound = logic.NotFound

def package_create(context, data_dict):

    model = context['model']
    user = context['user']
    model.Session.remove()
    model.Session()._context = context

    package_type = data_dict.get('type')
    package_plugin = lib_plugins.lookup_package_plugin(package_type)
    try:
        schema = package_plugin.form_to_db_schema_options({'type':'create',
                                               'api':'api_version' in context,
                                               'context': context})
    except AttributeError:
        schema = package_plugin.form_to_db_schema()

    check_access('package_create', context, data_dict)

    if 'api_version' not in context:
        # old plugins do not support passing the schema so we need
        # to ensure they still work
        try:
            package_plugin.check_data_dict(data_dict, schema)
        except TypeError:
            package_plugin.check_data_dict(data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, error_summary(errors))

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

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.create(pkg)

    if not context.get('defer_commit'):
        model.repo.commit()

    ## need to let rest api create
    context["package"] = pkg
    ## this is added so that the rest controller can make a new location
    context["id"] = pkg.id
    log.debug('Created object %s' % str(pkg.name))
    return get_action('package_show')(context, {'id':context['id']})

def package_create_validate(context, data_dict):
    model = context['model']
    schema = lib_plugins.lookup_package_plugin().form_to_db_schema()
    model.Session.remove()
    model.Session()._context = context

    check_access('package_create',context,data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, error_summary(errors))
    else:
        return data

def resource_create(context, data_dict):
    #TODO This doesn't actually do anything

    model = context['model']
    user = context['user']

    data, errors = validate(data_dict,
                            ckan.logic.schema.default_resource_schema(),
                            context)


def related_create(context, data_dict):
    model = context['model']
    user = context['user']
    userobj = model.User.get(user)

    data_dict["owner_id"] = userobj.id
    data, errors = validate(data_dict,
                            ckan.logic.schema.default_related_schema(),
                            context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors, error_summary(errors))

    related = model_save.related_dict_save(data, context)
    if not context.get('defer_commit'):
        model.repo.commit_and_remove()

    if 'dataset_id' in data_dict:
        dataset = model.Package.get(data_dict['dataset_id'])
        dataset.related.append( related )
        model.repo.commit_and_remove()

    context["related"] = related
    context["id"] = related.id
    log.debug('Created object %s' % str(related.title))
    return model_dictize.related_dictize(related, context)


def package_relationship_create(context, data_dict):

    model = context['model']
    user = context['user']
    schema = context.get('schema') or ckan.logic.schema.default_create_relationship_schema()
    api = context.get('api_version')
    ref_package_by = 'id' if api == 2 else 'name'

    id = data_dict['subject']
    id2 = data_dict['object']
    rel_type = data_dict['type']
    comment = data_dict.get('comment', u'')

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('Subject package %r was not found.' % id)
    if not pkg2:
        return NotFound('Object package %r was not found.' % id2)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, error_summary(errors))

    check_access('package_relationship_create', context, data_dict)

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
    """
    Add an object as a member to a group. If the membership already exists
    and is active then the capacity will be overwritten in case it has
    changed.

    context:
        model - The CKAN model module
        user  - The name of the current user

    data_dict:
        id - The ID of the group to which we want to add a new object
        object - The ID of the object being added as a member
        object_type - The name of the type being added, all lowercase,
                      e.g. package, or user
        capacity - The capacity with which to add this object
    """
    model = context['model']
    user = context['user']

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create member object %s') % data_dict.get("name", "")

    group = model.Group.get(data_dict.get('id', ''))
    obj_id   = data_dict['object']
    obj_type = data_dict['object_type']
    capacity = data_dict['capacity']

    # User must be able to update the group to add a member to it
    check_access('group_update', context, data_dict)

    # Look up existing, in case it exists
    member = model.Session.query(model.Member).\
            filter(model.Member.table_name == obj_type).\
            filter(model.Member.table_id == obj_id).\
            filter(model.Member.group_id == group.id).\
            filter(model.Member.state    == "active").first()
    if member:
        member.capacity = capacity
    else:
        member = model.Member(table_name = obj_type,
                              table_id = obj_id,
                              group_id = group.id,
                              capacity=capacity)

    model.Session.add(member)
    model.repo.commit()

    return model_dictize.member_dictize(member, context)

def group_create(context, data_dict):
    model = context['model']
    user = context['user']
    session = context['session']
    parent = context.get('parent', None)

    check_access('group_create', context, data_dict)

    # get the schema
    group_plugin = lib_plugins.lookup_group_plugin()
    try:
        schema = group_plugin.form_to_db_schema_options({'type':'create',
                                               'api':'api_version' in context,
                                               'context': context})
    except AttributeError:
        schema = group_plugin.form_to_db_schema()

    data, errors = validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors, error_summary(errors))

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

    if user:
        admins = [model.User.by_name(user.decode('utf8'))]
    else:
        admins = []
    model.setup_default_user_roles(group, admins)
    # Needed to let extensions know the group id
    session.flush()

    for item in plugins.PluginImplementations(plugins.IGroupController):
        item.create(group)

    activity_dict = {
            'user_id': model.User.by_name(user.decode('utf8')).id,
            'object_id': group.id,
            'activity_type': 'new group',
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
    activity_create(activity_create_context, activity_dict, ignore_auth=True)

    if not context.get('defer_commit'):
        model.repo.commit()
    context["group"] = group
    context["id"] = group.id
    log.debug('Created object %s' % str(group.name))
    return model_dictize.group_dictize(group, context)

def rating_create(context, data_dict):

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
    '''Creates a new user'''

    model = context['model']
    schema = context.get('schema') or ckan.logic.schema.default_user_schema()
    session = context['session']

    check_access('user_create', context, data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors, error_summary(errors))

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
    activity_create(activity_create_context, activity_dict, ignore_auth=True)

    if not context.get('defer_commit'):
        model.repo.commit()

    context['user'] = user
    context['id'] = user.id
    log.debug('Created user %s' % str(user.name))
    return model_dictize.user_dictize(user, context)

## Modifications for rest api

def package_create_rest(context, data_dict):

    check_access('package_create_rest', context, data_dict)

    dictized_package = model_save.package_api_to_dict(data_dict, context)
    dictized_after = get_action('package_create')(context, dictized_package)

    pkg = context['package']

    package_dict = model_dictize.package_to_api(pkg, context)

    data_dict['id'] = pkg.id

    return package_dict

def group_create_rest(context, data_dict):

    check_access('group_create_rest', context, data_dict)

    dictized_group = model_save.group_api_to_dict(data_dict, context)
    dictized_after = get_action('group_create')(context, dictized_group)

    group = context['group']

    group_dict = model_dictize.group_to_api(group, context)

    data_dict['id'] = group.id

    return group_dict

def vocabulary_create(context, data_dict):

    model = context['model']
    schema = context.get('schema') or ckan.logic.schema.default_create_vocabulary_schema()

    model.Session.remove()
    model.Session()._context = context

    check_access('vocabulary_create', context, data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, error_summary(errors))

    vocabulary = model_save.vocabulary_dict_save(data, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug('Created Vocabulary %s' % str(vocabulary.name))

    return model_dictize.vocabulary_dictize(vocabulary, context)

def activity_create(context, activity_dict, ignore_auth=False):
    '''Create a new activity stream activity and return a dictionary
    representation of it.

    '''
    model = context['model']
    user = context['user']

    # Any revision_id that the caller attempts to pass in the activity_dict is
    # ignored and overwritten here.
    if getattr(model.Session, 'revision', None):
        activity_dict['revision_id'] = model.Session.revision.id
    else:
        activity_dict['revision_id'] = None

    if not ignore_auth:
        check_access('activity_create', context, activity_dict)

    schema = context.get('schema') or ckan.logic.schema.default_create_activity_schema()
    data, errors = validate(activity_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    activity = model_save.activity_dict_save(activity_dict, context)

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

    relationship_dict = get_action('package_relationship_create')(context, data_dict)
    return relationship_dict

def tag_create(context, tag_dict):
    '''Create a new tag and return a dictionary representation of it.'''

    model = context['model']

    check_access('tag_create', context, tag_dict)

    schema = context.get('schema') or ckan.logic.schema.default_create_tag_schema()
    data, errors = validate(tag_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    tag = model_save.tag_dict_save(tag_dict, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug("Created tag '%s' " % tag)
    return model_dictize.tag_dictize(tag, context)
