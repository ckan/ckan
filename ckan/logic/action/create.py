import logging

import ckan.authz
from ckan.plugins import (PluginImplementations,
                          IGroupController,
                          IPackageController)
from ckan.logic import NotFound, check_access, NotAuthorized, ValidationError
from ckan.lib.base import _
from ckan.lib.dictization.model_dictize import package_to_api1, package_to_api2
from ckan.lib.dictization.model_save import (group_api_to_dict,
                                             group_dict_save,
                                             package_api_to_dict,
                                             package_dict_save)

from ckan.lib.dictization.model_dictize import (group_dictize,
                                                package_dictize)


from ckan.logic.schema import default_create_package_schema, default_resource_schema

from ckan.logic.schema import default_group_schema
from ckan.lib.navl.dictization_functions import validate
from ckan.logic.action.update import _update_package_relationship
log = logging.getLogger(__name__)


def package_create(data_dict, context):

    model = context['model']
    user = context['user']
    schema = context.get('schema') or default_create_package_schema()

    check_access(model.System(), model.Action.PACKAGE_CREATE, context)

    data, errors = validate(data_dict,
                            schema,
                            context)

    if errors:
        raise ValidationError(errors)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Create object %s') % data["name"]

    pkg = package_dict_save(data, context)

    if user:
        admins = [model.User.by_name(user.decode('utf8'))]
    else:
        admins = []
    model.setup_default_user_roles(pkg, admins)
    for item in PluginImplementations(IPackageController):
        item.create(pkg)
    model.repo.commit()        
    ## need to let rest api create
    context["package"] = pkg
    ## this is added so that the rest controller can make a new location 
    context["id"] = pkg.id
    log.debug('Created object %s' % str(pkg.name))
    return package_dictize(pkg, context)

def resource_create(data_dict, context):
    model = context['model']
    user = context['user']

    data, errors = validate(data_dict,
                            default_resource_schema(),
                            context)


def package_relationship_create(data_dict, context):

    model = context['model']
    user = context['user']
    id = context["id"]
    id2 = context["id2"]
    rel = context["rel"]
    api = context.get('api_version') or '1'
    ref_package_by = 'id' if api == '2' else 'name'

    # Create a Package Relationship.
    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('First package named in address was not found.')
    if not pkg2:
        return NotFound('Second package named in address was not found.')

    am_authorized = ckan.authz.Authorizer().\
                    authorized_package_relationship(\
                    user, pkg1, pkg2, action=model.Action.EDIT)
    if not am_authorized:
        raise NotAuthorized

    ##FIXME should have schema
    comment = data_dict.get('comment', u'')

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if existing_rels:
        return _update_package_relationship(existing_rels[0],
                                            comment, context)
    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Create package relationship: %s %s %s') % (pkg1, rel, pkg2)
    rel = pkg1.add_relationship(rel, pkg2, comment=comment)
    model.repo.commit_and_remove()
    relationship_dicts = rel.as_dict(ref_package_by=ref_package_by)
    return relationship_dicts

def group_create(data_dict, context):
    model = context['model']
    user = context['user']

    check_access(model.System(), model.Action.GROUP_CREATE, context)

    context = {'model': model, 'session': model.Session}
    dictized = group_api_to_dict(data_dict, context)

    data, errors = validate(dictized,
                            default_group_schema(),
                            context)

    if errors:
        raise ValidationError(errors)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Create object %s') % data['name']

    group = group_dict_save(data, context)

    if user:
        admins = [model.User.by_name(user.decode('utf8'))]
    else:
        admins = []
    model.setup_default_user_roles(group, admins)
    for item in PluginImplementations(IGroupController):
        item.create(group)
    model.repo.commit()        
    context["id"] = group.id
    log.debug('Created object %s' % str(group.name))
    return group_dictize(group, context)

def rating_create(data_dict, context):

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
            if rating < ckan.rating.MIN_RATING or rating > ckan.rating.MAX_RATING:
                opts_err = _('Rating must be between %i and %i.') % (ckan.rating.MIN_RATING, ckan.rating.MAX_RATING)
            elif not package:
                opts_err = _('Package with name %r does not exist.') % package_ref
    if opts_err:
        raise ValidationError(opts_err)

    user = model.User.by_name(user)
    ckan.rating.set_rating(user, package, rating_int)

    package = model.Package.get(package_ref)
    ret_dict = {'rating average':package.get_average_rating(),
                'rating count': len(package.ratings)}
    return ret_dict


## Modifications for rest api

def package_create_rest(data_dict, context):

    api = context.get('api_version') or '1'

    dictized_package = package_api_to_dict(data_dict, context)
    dictized_after = package_create(dictized_package, context) 

    pkg = context["package"]

    if api == '1':
        package_dict = package_to_api1(pkg, context)
    else:
        package_dict = package_to_api2(pkg, context)

    return package_dict

