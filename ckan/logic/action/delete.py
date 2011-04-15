from ckan.logic import NotFound, check_access, NotAuthorized
from ckan.lib.base import _
import ckan.authz
from ckan.plugins import PluginImplementations, IGroupController, IPackageController


def package_delete(context):

    model = context['model']
    user = context['user']
    id = context["id"]

    entity = model.Package.get(id)
    check_access(entity, model.Action.PURGE, context)

    if entity is None:
        raise NotFound
    
    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete Package: %s') % entity.name

    for item in PluginImplementations(IPackageController):
        item.delete(entity)
    entity.delete()
    model.repo.commit()        


def package_relationship_delete(context):

    model = context['model']
    user = context['user']
    id = context["id"]
    id2 = context["id2"]
    rel = context["rel"]

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

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound

    relationship = existing_rels[0]
    revisioned_details = 'Package Relationship: %s %s %s' % (id, rel, id2)

    check_access(relationship, model.Action.PURGE, context)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete %s') % revisioned_details

    relationship.delete()
    model.repo.commit()

def group_delete(context):

    model = context['model']
    user = context['user']
    id = context["id"]

    group = model.Group.get(id)
    context["group"] = group
    if group is None:
        raise NotFound('Group was not found.')

    revisioned_details = 'Group: %s' % group.name

    check_access(group, model.Action.PURGE, context)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete %s') % revisioned_details
    group.delete()

    for item in PluginImplementations(IGroupController):
        item.delete(group)

    model.repo.commit()

