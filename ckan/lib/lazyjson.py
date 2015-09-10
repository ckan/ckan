import simplejson as json
import simplejson.encoder as json_encoder


class LazyJSONObject(dict):
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

    def for_json(self):
        if self._json_string:
            return JSONString(self._json_string)
        return self._json_dict


def _loads_method(name):
    def method(self, *args, **kwargs):
        return getattr(self._loads(), name)(*args, **kwargs)
    return method

for fn in ['__contains__', '__delitem__', '__eq__', '__ge__',
           '__getitem__', '__gt__', '__iter__', '__le__', '__len__', '__lt__',
           '__ne__', '__setitem__', 'clear', 'copy', 'fromkeys', 'get',
           'has_key', 'items', 'iteritems', 'iterkeys', 'itervalues', 'keys',
           'pop', 'popitem', 'setdefault', 'update', 'values']:
    setattr(LazyJSONObject, fn, _loads_method(fn))


class JSONString(int):
    '''
    A type for already-encoded JSON

    Fake-out simplejson by subclassing int so that simplejson calls
    our __str__ method to produce JSON.

    This trick is unpleasant, but significantly less fragile than
    subclassing JSONEncoder and modifying its internal workings, or
    monkeypatching the simplejson library.
    '''
    def __new__(cls, s):
        obj = super(JSONString, cls).__new__(cls, -1)
        obj.s = s
        return obj

    def __str__(self):
        return self.s

    def __repr__(self):
        return "JSONString(%r)" % self.s
