from nose.tools import assert_equal
import copy

def change_lists_to_sets(iterable):
    '''recursive method to drill down into iterables to
    convert any list or tuples into sets. Does not work
    though for dictionaries in lists.'''
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
    '''Asserts dicts are equal, assuming that the ordering of
    any lists is unimportant.'''                
    dicts = [copy.deepcopy(dict1), copy.deepcopy(dict2)]
    for d in dicts:
        d = change_lists_to_sets(d)
    assert_equal(dicts[0], dicts[1])
