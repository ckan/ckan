import json

class LazyJSONObject(object):
    '''An object that behaves like a dict returned from json.loads'''
    def __init__(self, json_string):
        self._json_string = json_string
        self._json_dict = None

    def _loads(self):
        if not self._json_dict:
            self._json_dict = json.loads(self._json_string)
            self._json_string = None
        return self._json_dict

    def __nonzero__(self):
        return True

    def to_json_string(self, *args, **kwargs):
        if self._json_string:
            return self._json_string
        return json.dumps(self._json_dict, *args, **kwargs)


def _loads_method(name):
    def method(self, *args, **kwargs):
        return getattr(self._loads(), name)(*args, **kwargs)
    return method

for fn in ['__cmp__', '__contains__', '__delitem__', '__eq__', '__ge__',
        '__getitem__', '__gt__', '__iter__', '__le__', '__len__', '__lt__',
        '__ne__', '__setitem__', 'clear', 'copy', 'fromkeys', 'get', 'has_key',
        'items', 'iteritems', 'iterkeys', 'itervalues', 'keys', 'pop',
        'popitem', 'setdefault', 'update', 'values']:
    setattr(LazyJSONObject, fn, _loads_method(fn))


class LazyJSONEncoder(json.JSONEncoder):
    '''JSON encoder that handles LazyJSONObject elements'''
    def _iterencode_default(self, o, markers=None):
        if hasattr(o, 'to_json_string'):
            return iter([o.to_json_string()])
        return json.JSONEncoder._iterencode_default(self, o, markers)
