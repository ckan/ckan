# encoding: utf-8

from copy import deepcopy
import re

from ckan.logic import NotFound
from ckan.lib.base import _, abort


def rename_keys(dict_, key_map, reverse=False, destructive=False):
    '''Returns a dict that has particular keys renamed,
    according to the key_map.

    Rename is by default non-destructive, so if the intended new
    key name already exists, it won\'t do that rename.

    To reverse the change, set reverse=True.'''
    new_dict = deepcopy(dict_)
    for key, mapping in key_map.items():
        if reverse:
            key, mapping = (mapping, key)
        if (not destructive) and new_dict.has_key(mapping):
            continue
        if dict_.has_key(key):
            value = dict_[key]
            new_dict[mapping] = value
            del new_dict[key]
    return new_dict


def get_domain_object(model, domain_object_ref):
    '''For an id or name, return the corresponding domain object.
    (First match returned, in order: system, package, group, auth_group, user).
    '''
    if domain_object_ref in ('system', 'System'):
        return model.System
    pkg = model.Package.get(domain_object_ref)
    if pkg:
        return pkg
    group = model.Group.get(domain_object_ref)
    if group:
        return group
    user = model.User.get(domain_object_ref)
    if user:
        return user
    raise NotFound('Domain object %r not found' % domain_object_ref)


def error_summary(error_dict):
    ''' Do some i18n stuff on the error_dict keys '''

    def prettify(field_name):
        field_name = re.sub('(?<!\w)[Uu]rl(?!\w)', 'URL',
                            field_name.replace('_', ' ').capitalize())
        return _(field_name.replace('_', ' '))

    summary = {}
    for key, error in error_dict.iteritems():
        if key == 'resources':
            summary[_('Resources')] = _('Package resource(s) invalid')
        elif key == 'extras':
            summary[_('Extras')] = _('Missing Value')
        elif key == 'extras_validation':
            summary[_('Extras')] = error[0]
        else:
            summary[_(prettify(key))] = error[0]
    return summary
