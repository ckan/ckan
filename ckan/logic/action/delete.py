from pylons.i18n import _

import ckan.logic
import ckan.logic.action
import ckan.plugins as plugins

# define some shortcuts
ValidationError = ckan.logic.ValidationError
NotFound = ckan.logic.NotFound
check_access = ckan.logic.check_access

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

    for item in plugins.PluginImplementations(plugins.IPackageController):
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

def related_delete(context, data_dict):
    model = context['model']
    user = context['user']
    id = data_dict['id']

    entity = model.Related.get(id)

    if entity is None:
        raise NotFound

    check_access('related_delete',context, data_dict)

    entity.delete()
    model.repo.commit()


def member_delete(context, data_dict=None):
    """
    Removes an object as a member of a group. If the membership already exists
    and is active then it will be deleted.

    context:
        model - The CKAN model module
        user  - The name of the current user

    data_dict:
        id - The ID of the group from which we want to remove object
        object - The ID of the object being removed as a member
        object_type - The name of the type being removed, all lowercase,
                      e.g. package, or user
    """
    model = context['model']
    user = context['user']

    group = model.Group.get(data_dict.get('id'))
    obj_id   = data_dict['object']
    obj_type = data_dict['object_type']

    # User must be able to update the group to remove a member from it
    check_access('group_update', context, data_dict)

    member = model.Session.query(model.Member).\
            filter(model.Member.table_name == obj_type).\
            filter(model.Member.table_id == obj_id).\
            filter(model.Member.group_id == group.id).\
            filter(model.Member.state    == "active").first()
    if member:
        member.delete()
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

    for item in plugins.PluginImplementations(plugins.IGroupController):
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

def vocabulary_delete(context, data_dict):
    model = context['model']

    vocab_id = data_dict.get('id')
    if not vocab_id:
        raise ValidationError({'id': _('id not in data')})

    vocab_obj = model.vocabulary.Vocabulary.get(vocab_id)
    if vocab_obj is None:
        raise NotFound(_('Could not find vocabulary "%s"') % vocab_id)

    check_access('vocabulary_delete', context, data_dict)

    vocab_obj.delete()
    model.repo.commit()

def tag_delete(context, data_dict):
    model = context['model']

    if not data_dict.has_key('id') or not data_dict['id']:
        raise ValidationError({'id': _('id not in data')})
    tag_id_or_name = data_dict['id']

    vocab_id_or_name = data_dict.get('vocabulary_id')

    tag_obj = model.tag.Tag.get(tag_id_or_name, vocab_id_or_name)

    if tag_obj is None:
        raise NotFound(_('Could not find tag "%s"') % tag_id_or_name)

    check_access('tag_delete', context, data_dict)

    tag_obj.delete()
    model.repo.commit()

def package_relationship_delete_rest(context, data_dict):

    # rename keys
    key_map = {'id': 'subject',
               'id2': 'object',
               'rel': 'type'}
    # We want 'destructive', so that the value of the subject,
    # object and rel in the URI overwrite any values for these
    # in params. This is because you are not allowed to change
    # these values.
    data_dict = ckan.logic.action.rename_keys(data_dict, key_map, destructive=True)

    package_relationship_delete(context, data_dict)
