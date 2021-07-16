# encoding: utf-8

from simplejson import loads, RawJSON, dumps
from six import text_type


class LazyJSONObject(RawJSON):
    '''
    An object that behaves like a dict returned from json.loads
    but when passed to simplejson.dumps will render original
    string passed when possible. Accepts and produces only
    unicode strings containing a single JSON object.
    '''
    def __init__(self, json_string):
        assert isinstance(json_string, text_type), json_string
        self._json_string = json_string
        self._json_dict = None

    def _loads(self):
        if not self._json_dict:
            self._json_dict = loads(self._json_string)
            self._json_string = None
        return self._json_dict

    def __repr__(self):
        if self._json_string:
            return '<LazyJSONObject %r>' % self._json_string
        return '<LazyJSONObject %r>' % self._json_dict

    @property
    def encoded_json(self):
        if self._json_string:
            return self._json_string
        return dumps(
            self._json_dict,
            ensure_ascii=False,
            separators=(',', ':'))


def _loads_method(name):
    def method(self, *args, **kwargs):
        return getattr(self._loads(), name)(*args, **kwargs)
    return method


for fn in ['__contains__', '__delitem__', '__eq__', '__ge__',
           '__getitem__', '__gt__', '__iter__', '__le__', '__len__',
           '__lt__', '__ne__', '__setitem__', 'clear', 'copy',
           'fromkeys', 'get', 'items', 'iteritems',
           'iterkeys', 'itervalues', 'keys', 'pop', 'popitem',
           'setdefault', 'update', 'values']:
    setattr(LazyJSONObject, fn, _loads_method(fn))
