from ckan.logic import NotFound
from ckan.lib.base import _
from ckan.logic import check_access
from ckan.logic.action import rename_keys

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
    id = data_dict['subject']
    id2 = data_dict['object']
    rel = data_dict['type']

    pkg1 = model.Package.get(id)
    pkg2 = model.Package.get(id2)
    if not pkg1:
        raise NotFound('Subject package %r was not found.' % id)
    if not pkg2:
        return NotFound('Object package %r was not found.' % id2)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise NotFound

    relationship = existing_rels[0]
    revisioned_details = 'Package Relationship: %s %s %s' % (id, rel, id2)

    context['relationship'] = relationship
    check_access('package_relationship_delete', context, data_dict)

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

def task_status_delete(context, data_dict):
    model = context['model']
    user = context['user']
    id = data_dict['id']
    model.Session.remove()
    model.Session()._context = context

    entity = model.TaskStatus.get(id)

    if entity is None:
        raise NotFound

    check_access('task_status_delete', context, data_dict)

    entity.delete()
    model.Session.commit()

def package_relationship_delete_rest(context, data_dict):

    # rename keys
    key_map = {'id': 'subject',
               'id2': 'object',
               'rel': 'type'}
    # We want 'destructive', so that the value of the subject,
    # object and rel in the URI overwrite any values for these
    # in params. This is because you are not allowed to change
    # these values.
    data_dict = rename_keys(data_dict, key_map, destructive=True)

    package_relationship_delete(context, data_dict)

    
