import logging
import re
import datetime

import ckan.authz
from ckan.plugins import PluginImplementations, IGroupController, IPackageController
from ckan.logic import NotFound, check_access, NotAuthorized, ValidationError
from ckan.lib.base import _
from ckan.lib.dictization.model_dictize import group_dictize, package_dictize
from ckan.lib.dictization.model_save import (group_api_to_dict,
                                             package_api_to_dict,
                                             group_dict_save,
                                             package_dict_save)
from ckan.logic.schema import (default_update_group_schema,
                               default_update_package_schema)
from ckan.lib.navl.dictization_functions import validate
log = logging.getLogger(__name__)

def prettify(field_name):
    field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL', field_name.replace('_', ' ').capitalize())
    return _(field_name.replace('_', ' '))

def package_error_summary(error_dict):

    error_summary = {}
    for key, error in error_dict.iteritems():
        if key == 'resources':
            error_summary[_('Resources')] = _('Package resource(s) incomplete')
        elif key == 'extras':
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

def check_group_auth(data_dict, context):
    model = context['model']
    pkg = context.get("package")

    ## hack as api does not allow groups
    if context.get("allow_partial_update"):
        return
    
    group_dicts = data_dict.get("groups", [])
    groups = set()
    for group_dict in group_dicts:
        id = group_dict.get('id')
        if not id:
            continue
        grp = model.Group.get(id)
        if grp is None:
            raise NotFound(_('Group was not found.'))
        groups.add(grp)

    if pkg:
        groups = groups - set(pkg.groups)

    for group in groups:
        check_access(group, model.Action.EDIT, context)

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
    else:
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

def make_latest_pending_package_active(context):

    model = context['model']
    session = model.Session
    id = context["id"]
    pkg = model.Package.get(id)

    check_access(pkg, model.Action.EDIT, context)

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
    
    session.commit()        
    session.remove()        


def package_update(data_dict, context):
    model = context['model']
    user = context['user']
    id = context["id"]
    preview = context.get('preview', False)
    schema = context.get('schema') or default_update_package_schema()
    model.Session.remove()

    pkg = model.Package.get(id)
    context["package"] = pkg

    if pkg is None:
        raise NotFound(_('Package was not found.'))

    check_access(pkg, model.Action.EDIT, context)

    data, errors = validate(data_dict, schema, context)

    check_group_auth(data, context)

    if errors:
        model.Session.rollback()
        raise ValidationError(errors, package_error_summary(errors))

    if not preview:
        rev = model.repo.new_revision()
        rev.author = user
        if 'message' in context:
            rev.message = context['message']
        else:
            rev.message = _(u'REST API: Create object %s') % data.get("name")

    pkg = package_dict_save(data, context)

    if not preview:
        for item in PluginImplementations(IPackageController):
            item.edit(pkg)
        model.repo.commit()        
        return package_dictize(pkg, context)
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
        model.repo.commit_and_remove()
    rel_dict = relationship.as_dict(package=relationship.subject,
                                    ref_package_by=ref_package_by)
    return rel_dict

def package_relationship_update(data_dict, context):

    model = context['model']
    user = context['user']
    id = context["id"]
    id2 = context["id2"]
    rel = context["rel"]
    api = context.get('api_version') or '1'
    ref_package_by = 'id' if api == '2' else 'name'

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('First package named in address was not found.')
    if not pkg2:
        return NotFound('Second package named in address was not found.')

    authorizer = ckan.authz.Authorizer()
    am_authorized = authorizer.authorized_package_relationship(
         user, pkg1, pkg2, action=model.Action.EDIT)

    if not am_authorized:
        raise NotAuthorized

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound('This relationship between the packages was not found.')
    entity = existing_rels[0]
    comment = data_dict.get('comment', u'')
    return _update_package_relationship(entity, comment, context)

def group_update(data_dict, context):

    model = context['model']
    user = context['user']
    schema = context.get('schema') or default_update_group_schema()
    id = context['id']

    group = model.Group.get(id)
    context["group"] = group
    if group is None:
        raise NotFound('Group was not found.')

    check_access(group, model.Action.EDIT, context)

    data, errors = validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors, group_error_summary(errors))

    rev = model.repo.new_revision()
    rev.author = user
    
    if 'message' in context:
        rev.message = context['message']
    else:
        rev.message = _(u'REST API: Create object %s') % data.get("name")

    group = group_dict_save(data, context)

    for item in PluginImplementations(IGroupController):
        item.edit(group)

    model.repo.commit()        
    if errors:
        raise ValidationError(errors)

    return group_dictize(group, context)

## Modifications for rest api

def package_update_rest(data_dict, context):

    model = context['model']
    id = context["id"]
    pkg = model.Package.get(id)
    context["package"] = pkg
    context["allow_partial_update"] = True
    dictized_package = package_api_to_dict(data_dict, context)
    return package_update(dictized_package, context)

def group_update_rest(data_dict, context):

    model = context['model']
    id = context["id"]
    group = model.Group.get(id)
    context["group"] = group
    context["allow_partial_update"] = True
    dictized_package = group_api_to_dict(data_dict, context)
    return group_update(dictized_package, context)

