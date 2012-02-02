from copy import deepcopy

from ckan.logic import NotFound

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
    (First match returned, in order: package, group, auth_group, user).'''
    pkg = model.Package.get(domain_object_ref)
    if pkg:
        return pkg
    group = model.Group.get(domain_object_ref)
    if group:
        return group
    authorization_group = model.AuthorizationGroup.by_name(domain_object_ref)  or\
                          model.Session.query(model.AuthorizationGroup).get(domain_object_ref)
    if authorization_group:
        return authorization_group
    user = model.User.get(domain_object_ref)
    if user:
        return user
    raise NotFound('Domain object %r not found' % domain_object_ref)

