from ckan.logic import NotFound
from ckan.lib.base import _
from ckan.logic import check_access

from ckan.plugins import PluginImplementations, IGroupController, IPackageController


def package_delete(context, data_dict):

    model = context['model']
    user = context['user']
    id = data_dict['id']

    entity = model.Package.get(id)

    if entity is None:
        raise NotFound

    check_access('package_delete',context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete Package: %s') % entity.name

    for item in PluginImplementations(IPackageController):
        item.delete(entity)
    entity.delete()
    model.repo.commit()


def package_relationship_delete(context, data_dict):

    model = context['model']
    user = context['user']
    id = data_dict['id']
    id2 = data_dict['id2']
    rel = data_dict['rel']

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('First package named in address was not found.')
    if not pkg2:
        return NotFound('Second package named in address was not found.')

    check_access('package_relationship_delete', context, data_dict)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound

    relationship = existing_rels[0]
    revisioned_details = 'Package Relationship: %s %s %s' % (id, rel, id2)

    context['relationship'] = relationship
    check_access('relationship_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete %s') % revisioned_details

    relationship.delete()
    model.repo.commit()

def group_delete(context, data_dict):

    model = context['model']
    user = context['user']
    id = data_dict['id']

    group = model.Group.get(id)
    context['group'] = group
    if group is None:
        raise NotFound('Group was not found.')

    revisioned_details = 'Group: %s' % group.name

    check_access('group_delete', context, data_dict)

    rev = model.repo.new_revision()
    rev.author = user
    rev.message = _(u'REST API: Delete %s') % revisioned_details
    group.delete()

    for item in PluginImplementations(IGroupController):
        item.delete(group)

    model.repo.commit()

