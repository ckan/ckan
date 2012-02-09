import logging

import ckan.rating as ratings
from ckan.plugins import (PluginImplementations,
                          IGroupController,
                          IPackageController)
from ckan.logic import NotFound, ValidationError
from ckan.logic import check_access
from ckan.lib.base import _
import ckan.lib.dictization
from ckan.lib.dictization.model_dictize import (package_to_api1,
                                                package_to_api2,
                                                group_to_api1,
                                                group_to_api2)

from ckan.lib.dictization.model_save import (group_api_to_dict,
                                             group_dict_save,
                                             package_api_to_dict,
                                             package_dict_save,
                                             user_dict_save,
                                             activity_dict_save)

from ckan.lib.dictization.model_dictize import (group_dictize,
                                                package_dictize,
                                                user_dictize,
                                                activity_dictize)


from ckan.logic.schema import (default_create_package_schema,
                               default_resource_schema,
                               default_create_relationship_schema,
                               default_create_activity_schema)

from ckan.logic.schema import default_group_schema, default_user_schema
from ckan.lib.navl.dictization_functions import validate 
from ckan.logic.action.update import (_update_package_relationship,
                                      package_error_summary,
                                      group_error_summary,
                                      relationship_error_summary)
from ckan.logic.action import rename_keys

log = logging.getLogger(__name__)

def package_create(context, data_dict):

    model = context['model']
    user = context['user']
    schema = context.get('schema') or default_create_package_schema()
    model.Session.remove()
    model.Session()._context = context

    check_access('package_create', context, data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, package_error_summary(errors))

    rev = model.repo.new_revision()
    rev.author = user
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create object %s') % data.get("name")

    pkg = package_dict_save(data, context)
    admins = []
    if user:
        admins = [model.User.by_name(user.decode('utf8'))]

    model.setup_default_user_roles(pkg, admins)
    # Needed to let extensions know the package id
    model.Session.flush()

    for item in PluginImplementations(IPackageController):
        item.create(pkg)

    if not context.get('defer_commit'):
        model.repo.commit()        

    ## need to let rest api create
    context["package"] = pkg
    ## this is added so that the rest controller can make a new location 
    context["id"] = pkg.id
    log.debug('Created object %s' % str(pkg.name))
    return package_dictize(pkg, context) 

def package_create_validate(context, data_dict):
    model = context['model']
    user = context['user']
    schema = context.get('schema') or default_create_package_schema()
    model.Session.remove()
    model.Session()._context = context
    
    check_access('package_create',context,data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, package_error_summary(errors))
    else:
        return data

def resource_create(context, data_dict):
    #TODO This doesn't actually do anything

    model = context['model']
    user = context['user']

    data, errors = validate(data_dict,
                            default_resource_schema(),
                            context)

def package_relationship_create(context, data_dict):

    model = context['model']
    user = context['user']
    schema = context.get('schema') or default_create_relationship_schema()
    api = context.get('api_version') or '1'
    ref_package_by = 'id' if api == '2' else 'name'

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
        raise ValidationError(errors, relationship_error_summary(errors))

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

def group_create(context, data_dict):
    model = context['model']
    user = context['user']
    session = context['session']
    schema = context.get('schema') or default_group_schema()

    check_access('group_create',context,data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors, group_error_summary(errors))

    rev = model.repo.new_revision()
    rev.author = user

    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create object %s') % data.get("name")

    group = group_dict_save(data, context)

    if user:
        admins = [model.User.by_name(user.decode('utf8'))]
    else:
        admins = []
    model.setup_default_user_roles(group, admins)
    # Needed to let extensions know the group id
    session.flush()
    for item in PluginImplementations(IGroupController):
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
    return group_dictize(group, context)

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
    schema = context.get('schema') or default_user_schema()
    session = context['session']

    check_access('user_create', context, data_dict)

    data, errors = validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors, group_error_summary(errors))

    user = user_dict_save(data, context)

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
    return user_dictize(user, context)

## Modifications for rest api

def package_create_rest(context, data_dict):
    
    api = context.get('api_version') or '1'

    check_access('package_create_rest', context, data_dict)

    dictized_package = package_api_to_dict(data_dict, context)
    dictized_after = package_create(context, dictized_package) 

    pkg = context['package']

    if api == '1':
        package_dict = package_to_api1(pkg, context)
    else:
        package_dict = package_to_api2(pkg, context)

    data_dict['id'] = pkg.id

    return package_dict

def group_create_rest(context, data_dict):

    api = context.get('api_version') or '1'

    check_access('group_create_rest', context, data_dict)

    dictized_group = group_api_to_dict(data_dict, context)
    dictized_after = group_create(context, dictized_group) 

    group = context['group']

    if api == '1':
        group_dict = group_to_api1(group, context)
    else:
        group_dict = group_to_api2(group, context)

    data_dict['id'] = group.id

    return group_dict

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

    schema = context.get('schema') or default_create_activity_schema()
    data, errors = validate(activity_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    activity = activity_dict_save(activity_dict, context)

    if not context.get('defer_commit'):
        model.repo.commit()

    log.debug("Created '%s' activity" % activity.activity_type)
    return activity_dictize(activity, context)

def package_relationship_create_rest(context, data_dict):
    # rename keys
    key_map = {'id': 'subject',
               'id2': 'object',
               'rel': 'type'}
    # Don't be destructive to enable parameter values for
    # object and type to override the URL parameters.
    data_dict = rename_keys(data_dict, key_map, destructive=False)

    relationship_dict = package_relationship_create(context, data_dict)
    return relationship_dict

