from pylons.i18n import _

import ckan.logic as logic
import ckan.plugins as plugins


def package_delete(context, data_dict):

    model = context['model']
    user = context['user']
    id = data_dict['id']

    entity = model.Package.get(id)

    if entity is None:
        raise logic.NotFound

    logic.check_access('package_delete',context, data_dict)

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
        raise logic.NotFound('Subject package %r was not found.' % id)
    if not pkg2:
        return logic.NotFound('Object package %r was not found.' % id2)

    existing_rels = pkg1.get_relationships_with(pkg2, rel)
    if not existing_rels:
        raise logic.NotFound

    relationship = existing_rels[0]
    revisioned_details = 'Package Relationship: %s %s %s' % (id, rel, id2)

    context['relationship'] = relationship
    logic.check_access('package_relationship_delete', context, data_dict)

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
        raise logic.NotFound('Group was not found.')

    revisioned_details = 'Group: %s' % group.name

    logic.check_access('group_delete', context, data_dict)

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
        raise logic.NotFound

    logic.check_access('task_status_delete', context, data_dict)

    entity.delete()
    model.Session.commit()

def vocabulary_delete(context, data_dict):
    model = context['model']

    vocab_id = data_dict.get('id')
    if not vocab_id:
        raise logic.ValidationError({'id': _('id not in data')})

    vocab_obj = model.vocabulary.Vocabulary.get(vocab_id)
    if vocab_obj is None:
        raise logic.NotFound(_('Could not find vocabulary "%s"') % vocab_id)

    logic.check_access('vocabulary_delete', context, data_dict)

    vocab_obj.delete()
    model.repo.commit()

def tag_delete(context, data_dict):
    model = context['model']

    if not data_dict.has_key('id') or not data_dict['id']:
        raise logic.ValidationError({'id': _('id not in data')})
    tag_id_or_name = data_dict['id']

    vocab_id_or_name = data_dict.get('vocabulary_id')

    tag_obj = model.tag.Tag.get(tag_id_or_name, vocab_id_or_name)

    if tag_obj is None:
        raise logic.NotFound(_('Could not find tag "%s"') % tag_id_or_name)

    logic.check_access('tag_delete', context, data_dict)

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
    data_dict = logic.action.rename_keys(data_dict, key_map, destructive=True)

    package_relationship_delete(context, data_dict)
