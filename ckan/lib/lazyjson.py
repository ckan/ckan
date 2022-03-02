# encoding: utf-8

from typing import Any
from simplejson import (
    loads,
    RawJSON,
    dumps)


class LazyJSONObject(RawJSON):
    u'''
    An object that behaves like a dict returned from json.loads
    but when passed to simplejson.dumps will render original
    string passed when possible. Accepts and produces only
    unicode strings containing a single JSON object.
    '''
    def __init__(self, json_string: str):
        assert isinstance(json_string, str), json_string
        self._json_string = json_string
        self._json_dict = None

    def _loads(self):
        if not self._json_dict:
            assert self._json_string is not None
            self._json_dict = loads(self._json_string)
            self._json_string = None
        return self._json_dict

    def __repr__(self):
        if self._json_string:
            return u'<LazyJSONObject %r>' % self._json_string
        return u'<LazyJSONObject %r>' % self._json_dict

    @property  # type: ignore
    def encoded_json(self):
        if self._json_string:
            return self._json_string
        return dumps(
            self._json_dict,
            ensure_ascii=False,
            separators=(u',', u':'))


def _loads_method(name: str):
    def method(self: Any, *args: Any, **kwargs: Any):
        return getattr(self._loads(), name)(*args, **kwargs)
    return method


for fn in [u'__contains__', u'__delitem__', u'__eq__', u'__ge__',
           u'__getitem__', u'__gt__', u'__iter__', u'__le__', u'__len__',
           u'__lt__', u'__ne__', u'__setitem__', u'clear', u'copy',
           u'fromkeys', u'get', u'items', u'iteritems',
           u'iterkeys', u'itervalues', u'keys', u'pop', u'popitem',
           u'setdefault', u'update', u'values']:
    setattr(LazyJSONObject, fn, _loads_method(fn))
