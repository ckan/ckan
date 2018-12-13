# encoding: utf-8

from nose.tools import assert_equal
import copy


def change_lists_to_sets(iterable):
    '''Convert any lists or tuples in `iterable` into sets.

    Recursively drill down into iterable and convert any list or tuples to
    sets.

    Does not work for dictionaries in lists.

    '''
    if isinstance(iterable, dict):
        for key in iterable:
            if isinstance(iterable[key], (list, tuple)):
                try:
                    iterable[key] = set(iterable[key])
                except TypeError:
                    # e.g. unhashable
                    pass
            elif getattr(iterable[key], '__iter__', False):
                change_lists_to_sets(iterable[key])
    elif isinstance(iterable, (list, tuple)):
        for item in iterable:
            if isinstance(item, (list, tuple)):
                iterable.pop(item)
                iterable.append(set(item))
            elif getattr(item, '__iter__', False):
                change_lists_to_sets(item)
    else:
        raise NotImplementedError


def assert_dicts_equal_ignoring_ordering(dict1, dict2):
    '''Assert that dict1 and dict2 are equal.

    Assumes that the ordering of any lists in the dicts is unimportant.

    '''
    dicts = [copy.deepcopy(dict1), copy.deepcopy(dict2)]
    for d in dicts:
        d = change_lists_to_sets(d)
    assert_equal(dicts[0], dicts[1])
