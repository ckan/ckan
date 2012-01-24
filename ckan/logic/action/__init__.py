from copy import deepcopy

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
