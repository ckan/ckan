"""
Takes GET/POST variable dictionary, as might be returned by ``cgi``,
and turns them into lists and dictionaries.

Keys (variable names) can have subkeys, with a ``.`` and
can be numbered with ``-``, like ``a.b-3=something`` means that
the value ``a`` is a dictionary with a key ``b``, and ``b``
is a list, the third(-ish) element with the value ``something``.
Numbers are used to sort, missing numbers are ignored.

This doesn't deal with multiple keys, like in a query string of
``id=10&id=20``, which returns something like ``{'id': ['10',
'20']}``.  That's left to someplace else to interpret.  If you want to
represent lists in this model, you use indexes, and the lists are
explicitly ordered.

If you want to change the character that determines when to split for
a dict or list, both variable_decode and variable_encode take dict_char
and list_char keyword args. For example, to have the GET/POST variables,
``a_1=something`` as a list, you would use a ``list_char='_'``.
"""

from .api import FancyValidator

__all__ = ['variable_decode', 'variable_encode', 'NestedVariables']


def variable_decode(d, dict_char='.', list_char='-'):
    """
    Decode the flat dictionary d into a nested structure.
    """
    result = {}
    dicts_to_sort = set()
    known_lengths = {}
    for key, value in d.iteritems():
        keys = key.split(dict_char)
        new_keys = []
        was_repetition_count = False
        for key in keys:
            if key.endswith('--repetitions'):
                key = key[:-len('--repetitions')]
                new_keys.append(key)
                known_lengths[tuple(new_keys)] = int(value)
                was_repetition_count = True
                break
            elif list_char in key:
                maybe_key, index = key.split(list_char, 1)
                if not index.isdigit():
                    new_keys.append(key)
                else:
                    key = maybe_key
                    new_keys.append(key)
                    dicts_to_sort.add(tuple(new_keys))
                    new_keys.append(int(index))
            else:
                new_keys.append(key)
        if was_repetition_count:
            continue

        place = result
        for i in range(len(new_keys) - 1):
            try:
                if not isinstance(place[new_keys[i]], dict):
                    place[new_keys[i]] = {None: place[new_keys[i]]}
                place = place[new_keys[i]]
            except KeyError:
                place[new_keys[i]] = {}
                place = place[new_keys[i]]
        if new_keys[-1] in place:
            if isinstance(place[new_keys[-1]], dict):
                place[new_keys[-1]][None] = value
            elif isinstance(place[new_keys[-1]], list):
                if isinstance(value, list):
                    place[new_keys[-1]].extend(value)
                else:
                    place[new_keys[-1]].append(value)
            else:
                if isinstance(value, list):
                    place[new_keys[-1]] = [place[new_keys[-1]]]
                    place[new_keys[-1]].extend(value)
                else:
                    place[new_keys[-1]] = [place[new_keys[-1]], value]
        else:
            place[new_keys[-1]] = value

    to_sort_list = sorted(dicts_to_sort, key=len, reverse=True)
    for key in to_sort_list:
        to_sort = result
        source = None
        last_key = None
        for sub_key in key:
            source = to_sort
            last_key = sub_key
            to_sort = to_sort[sub_key]
        if None in to_sort:
            noneVals = [(0, x) for x in to_sort.pop(None)]
            noneVals.extend(to_sort.iteritems())
            to_sort = noneVals
        else:
            to_sort = to_sort.iteritems()
        to_sort = [x[1] for x in sorted(to_sort)]
        if key in known_lengths:
            if len(to_sort) < known_lengths[key]:
                to_sort.extend([''] * (known_lengths[key] - len(to_sort)))
        source[last_key] = to_sort

    return result


def variable_encode(d, prepend='', result=None, add_repetitions=True,
                    dict_char='.', list_char='-'):
    """
    Encode a nested structure into a flat dictionary.
    """
    if result is None:
        result = {}
    if isinstance(d, dict):
        for key, value in d.iteritems():
            if key is None:
                name = prepend
            elif not prepend:
                name = key
            else:
                name = "%s%s%s" % (prepend, dict_char, key)
            variable_encode(value, name, result, add_repetitions,
                            dict_char=dict_char, list_char=list_char)
    elif isinstance(d, list):
        for i, value in enumerate(d):
            variable_encode(value, "%s%s%i" % (prepend, list_char, i), result,
                add_repetitions, dict_char=dict_char, list_char=list_char)
        if add_repetitions:
            repName = ('%s--repetitions' % prepend
                if prepend else '__repetitions__')
            result[repName] = str(len(d))
    else:
        result[prepend] = d
    return result


class NestedVariables(FancyValidator):

    def _convert_to_python(self, value, state):
        return variable_decode(value)

    def _convert_from_python(self, value, state):
        return variable_encode(value)

    def empty_value(self, value):
        return {}
