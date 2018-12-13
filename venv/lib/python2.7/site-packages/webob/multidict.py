# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Gives a multi-value dictionary object (MultiDict) plus several wrappers
"""
import cgi, copy, sys, warnings, urllib
from UserDict import DictMixin


__all__ = ['MultiDict', 'UnicodeMultiDict', 'NestedMultiDict', 'NoVars',
           'TrackableMultiDict']

class MultiDict(DictMixin):
    """
        An ordered dictionary that can have multiple values for each key.
        Adds the methods getall, getone, mixed and extend and add to the normal
        dictionary interface.
    """

    def __init__(self, *args, **kw):
        if len(args) > 1:
            raise TypeError("MultiDict can only be called with one positional argument")
        if args:
            if hasattr(args[0], 'iteritems'):
                items = list(args[0].iteritems())
            elif hasattr(args[0], 'items'):
                items = args[0].items()
            else:
                items = list(args[0])
            self._items = items
        else:
            self._items = []
        if kw:
            self._items.extend(kw.iteritems())

    @classmethod
    def view_list(cls, lst):
        """
        Create a dict that is a view on the given list
        """
        if not isinstance(lst, list):
            raise TypeError(
                "%s.view_list(obj) takes only actual list objects, not %r"
                % (cls.__name__, lst))
        obj = cls()
        obj._items = lst
        return obj

    @classmethod
    def from_fieldstorage(cls, fs):
        """
        Create a dict from a cgi.FieldStorage instance
        """
        obj = cls()
        # fs.list can be None when there's nothing to parse
        for field in fs.list or ():
            if field.filename:
                obj.add(field.name, field)
            else:
                obj.add(field.name, field.value)
        return obj

    def __getitem__(self, key):
        for k, v in reversed(self._items):
            if k == key:
                return v
        raise KeyError(key)

    def __setitem__(self, key, value):
        try:
            del self[key]
        except KeyError:
            pass
        self._items.append((key, value))

    def add(self, key, value):
        """
        Add the key and value, not overwriting any previous value.
        """
        self._items.append((key, value))

    def getall(self, key):
        """
        Return a list of all values matching the key (may be an empty list)
        """
        result = []
        for k, v in self._items:
            if key == k:
                result.append(v)
        return result

    def getone(self, key):
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        v = self.getall(key)
        if not v:
            raise KeyError('Key not found: %r' % key)
        if len(v) > 1:
            raise KeyError('Multiple values match %r: %r' % (key, v))
        return v[0]

    def mixed(self):
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        result = {}
        multi = {}
        for key, value in self.iteritems():
            if key in result:
                # We do this to not clobber any lists that are
                # *actual* values in this dictionary:
                if key in multi:
                    result[key].append(value)
                else:
                    result[key] = [result[key], value]
                    multi[key] = None
            else:
                result[key] = value
        return result

    def dict_of_lists(self):
        """
        Returns a dictionary where each key is associated with a list of values.
        """
        r = {}
        for key, val in self.iteritems():
            r.setdefault(key, []).append(val)
        return r

    def __delitem__(self, key):
        items = self._items
        found = False
        for i in range(len(items)-1, -1, -1):
            if items[i][0] == key:
                del items[i]
                found = True
        if not found:
            raise KeyError(key)

    def __contains__(self, key):
        for k, v in self._items:
            if k == key:
                return True
        return False

    has_key = __contains__

    def clear(self):
        self._items = []

    def copy(self):
        return self.__class__(self)

    def setdefault(self, key, default=None):
        for k, v in self._items:
            if key == k:
                return v
        self._items.append((key, default))
        return default

    def pop(self, key, *args):
        if len(args) > 1:
            raise TypeError, "pop expected at most 2 arguments, got "\
                              + repr(1 + len(args))
        for i in range(len(self._items)):
            if self._items[i][0] == key:
                v = self._items[i][1]
                del self._items[i]
                return v
        if args:
            return args[0]
        else:
            raise KeyError(key)

    def popitem(self):
        return self._items.pop()

    def update(self, *args, **kw):
        if args:
            lst = args[0]
            if len(lst) != len(dict(lst)):
                # this does not catch the cases where we overwrite existing
                # keys, but those would produce too many warning
                msg = ("Behavior of MultiDict.update() has changed "
                    "and overwrites duplicate keys. Consider using .extend()"
                )
                warnings.warn(msg, stacklevel=2)
        DictMixin.update(self, *args, **kw)

    def extend(self, other=None, **kwargs):
        if other is None:
            pass
        elif hasattr(other, 'items'):
            self._items.extend(other.items())
        elif hasattr(other, 'keys'):
            for k in other.keys():
                self._items.append((k, other[k]))
        else:
            for k, v in other:
                self._items.append((k, v))
        if kwargs:
            self.update(kwargs)

    def __repr__(self):
        items = map('(%r, %r)'.__mod__, _hide_passwd(self.iteritems()))
        return '%s([%s])' % (self.__class__.__name__, ', '.join(items))

    def __len__(self):
        return len(self._items)

    ##
    ## All the iteration:
    ##

    def keys(self):
        return [k for k, v in self._items]

    def iterkeys(self):
        for k, v in self._items:
            yield k

    __iter__ = iterkeys

    def items(self):
        return self._items[:]

    def iteritems(self):
        return iter(self._items)

    def values(self):
        return [v for k, v in self._items]

    def itervalues(self):
        for k, v in self._items:
            yield v

class UnicodeMultiDict(DictMixin):
    """
    A MultiDict wrapper that decodes returned values to unicode on the
    fly. Decoding is not applied to assigned values.

    The key/value contents are assumed to be ``str``/``strs`` or
    ``str``/``FieldStorages`` (as is returned by the ``paste.request.parse_``
    functions).

    Can optionally also decode keys when the ``decode_keys`` argument is
    True.

    ``FieldStorage`` instances are cloned, and the clone's ``filename``
    variable is decoded. Its ``name`` variable is decoded when ``decode_keys``
    is enabled.

    """
    def __init__(self, multi, encoding=None, errors='strict',
                 decode_keys=False):
        self.multi = multi
        if encoding is None:
            encoding = sys.getdefaultencoding()
        self.encoding = encoding
        self.errors = errors
        self.decode_keys = decode_keys

    def _decode_key(self, key):
        if self.decode_keys:
            try:
                key = key.decode(self.encoding, self.errors)
            except AttributeError:
                pass
        return key

    def _encode_key(self, key):
        if self.decode_keys and isinstance(key, unicode):
            return key.encode(self.encoding, self.errors)
        return key

    def _decode_value(self, value):
        """
        Decode the specified value to unicode. Assumes value is a ``str`` or
        `FieldStorage`` object.

        ``FieldStorage`` objects are specially handled.
        """
        if isinstance(value, cgi.FieldStorage):
            # decode FieldStorage's field name and filename
            value = copy.copy(value)
            if self.decode_keys:
                if not isinstance(value.name, unicode):
                    value.name = value.name.decode(self.encoding, self.errors)
            if value.filename:
                if not isinstance(value.filename, unicode):
                    value.filename = value.filename.decode(self.encoding,
                                                           self.errors)
        elif not isinstance(value, unicode):
            try:
                value = value.decode(self.encoding, self.errors)
            except AttributeError:
                pass
        return value

    def _encode_value(self, value):
        # FIXME: should this do the FieldStorage stuff too?
        if isinstance(value, unicode):
            value = value.encode(self.encoding, self.errors)
        return value

    def __getitem__(self, key):
        return self._decode_value(self.multi.__getitem__(self._encode_key(key)))

    def __setitem__(self, key, value):
        self.multi.__setitem__(self._encode_key(key), self._encode_value(value))

    def add(self, key, value):
        """
        Add the key and value, not overwriting any previous value.
        """
        self.multi.add(self._encode_key(key), self._encode_value(value))

    def getall(self, key):
        """
        Return a list of all values matching the key (may be an empty list)
        """
        return map(self._decode_value, self.multi.getall(self._encode_key(key)))

    def getone(self, key):
        """
        Get one value matching the key, raising a KeyError if multiple
        values were found.
        """
        return self._decode_value(self.multi.getone(self._encode_key(key)))

    def mixed(self):
        """
        Returns a dictionary where the values are either single
        values, or a list of values when a key/value appears more than
        once in this dictionary.  This is similar to the kind of
        dictionary often used to represent the variables in a web
        request.
        """
        unicode_mixed = {}
        for key, value in self.multi.mixed().iteritems():
            if isinstance(value, list):
                value = [self._decode_value(value) for value in value]
            else:
                value = self._decode_value(value)
            unicode_mixed[self._decode_key(key)] = value
        return unicode_mixed

    def dict_of_lists(self):
        """
        Returns a dictionary where each key is associated with a
        list of values.
        """
        unicode_dict = {}
        for key, value in self.multi.dict_of_lists().iteritems():
            value = [self._decode_value(value) for value in value]
            unicode_dict[self._decode_key(key)] = value
        return unicode_dict

    def __delitem__(self, key):
        self.multi.__delitem__(self._encode_key(key))

    def __contains__(self, key):
        return self.multi.__contains__(self._encode_key(key))

    has_key = __contains__

    def clear(self):
        self.multi.clear()

    def copy(self):
        return UnicodeMultiDict(self.multi.copy(), self.encoding, self.errors)

    def setdefault(self, key, default=None):
        return self._decode_value(
            self.multi.setdefault(self._encode_key(key),
                                  self._encode_value(default)))

    def pop(self, key, *args):
        return self._decode_value(self.multi.pop(self._encode_key(key), *args))

    def popitem(self):
        k, v = self.multi.popitem()
        return (self._decode_key(k), self._decode_value(v))

    def __repr__(self):
        items = map('(%r, %r)'.__mod__, _hide_passwd(self.iteritems()))
        return '%s([%s])' % (self.__class__.__name__, ', '.join(items))

    def __len__(self):
        return self.multi.__len__()

    ##
    ## All the iteration:
    ##

    def keys(self):
        return [self._decode_key(k) for k in self.multi.iterkeys()]

    def iterkeys(self):
        for k in self.multi.iterkeys():
            yield self._decode_key(k)

    __iter__ = iterkeys

    def items(self):
        return [(self._decode_key(k), self._decode_value(v))
                for k, v in self.multi.iteritems()]

    def iteritems(self):
        for k, v in self.multi.iteritems():
            yield (self._decode_key(k), self._decode_value(v))

    def values(self):
        return [self._decode_value(v) for v in self.multi.itervalues()]

    def itervalues(self):
        for v in self.multi.itervalues():
            yield self._decode_value(v)

_dummy = object()

class TrackableMultiDict(MultiDict):
    tracker = None
    name = None
    def __init__(self, *args, **kw):
        if '__tracker' in kw:
            self.tracker = kw.pop('__tracker')
        if '__name' in kw:
            self.name = kw.pop('__name')
        MultiDict.__init__(self, *args, **kw)
    def __setitem__(self, key, value):
        MultiDict.__setitem__(self, key, value)
        self.tracker(self, key, value)
    def add(self, key, value):
        MultiDict.add(self, key, value)
        self.tracker(self, key, value)
    def __delitem__(self, key):
        MultiDict.__delitem__(self, key)
        self.tracker(self, key)
    def clear(self):
        MultiDict.clear(self)
        self.tracker(self)
    def setdefault(self, key, default=None):
        result = MultiDict.setdefault(self, key, default)
        self.tracker(self, key, result)
        return result
    def pop(self, key, *args):
        result = MultiDict.pop(self, key, *args)
        self.tracker(self, key)
        return result
    def popitem(self):
        result = MultiDict.popitem(self)
        self.tracker(self)
        return result
    def update(self, *args, **kwargs):
        MultiDict.update(self, *args, **kwargs)
        self.tracker(self)
    def __repr__(self):
        items = map('(%r, %r)'.__mod__, _hide_passwd(self.iteritems()))
        return '%s([%s])' % (self.name or self.__class__.__name__, ', '.join(items))
    def copy(self):
        # Copies shouldn't be tracked
        return MultiDict(self)

class NestedMultiDict(MultiDict):
    """
    Wraps several MultiDict objects, treating it as one large MultiDict
    """

    def __init__(self, *dicts):
        self.dicts = dicts

    def __getitem__(self, key):
        for d in self.dicts:
            value = d.get(key, _dummy)
            if value is not _dummy:
                return value
        raise KeyError(key)

    def _readonly(self, *args, **kw):
        raise KeyError("NestedMultiDict objects are read-only")
    __setitem__ = _readonly
    add = _readonly
    __delitem__ = _readonly
    clear = _readonly
    setdefault = _readonly
    pop = _readonly
    popitem = _readonly
    update = _readonly

    def getall(self, key):
        result = []
        for d in self.dicts:
            result.extend(d.getall(key))
        return result

    # Inherited:
    # getone
    # mixed
    # dict_of_lists

    def copy(self):
        return MultiDict(self)

    def __contains__(self, key):
        for d in self.dicts:
            if key in d:
                return True
        return False

    has_key = __contains__

    def __len__(self):
        v = 0
        for d in self.dicts:
            v += len(d)
        return v

    def __nonzero__(self):
        for d in self.dicts:
            if d:
                return True
        return False

    def items(self):
        return list(self.iteritems())

    def iteritems(self):
        for d in self.dicts:
            for item in d.iteritems():
                yield item

    def values(self):
        return list(self.itervalues())

    def itervalues(self):
        for d in self.dicts:
            for value in d.itervalues():
                yield value

    def keys(self):
        return list(self.iterkeys())

    def __iter__(self):
        for d in self.dicts:
            for key in d:
                yield key

    iterkeys = __iter__

class NoVars(object):
    """
    Represents no variables; used when no variables
    are applicable.

    This is read-only
    """

    def __init__(self, reason=None):
        self.reason = reason or 'N/A'

    def __getitem__(self, key):
        raise KeyError("No key %r: %s" % (key, self.reason))

    def __setitem__(self, *args, **kw):
        raise KeyError("Cannot add variables: %s" % self.reason)

    add = __setitem__
    setdefault = __setitem__
    update = __setitem__

    def __delitem__(self, *args, **kw):
        raise KeyError("No keys to delete: %s" % self.reason)
    clear = __delitem__
    pop = __delitem__
    popitem = __delitem__

    def get(self, key, default=None):
        return default

    def getall(self, key):
        return []

    def getone(self, key):
        return self[key]

    def mixed(self):
        return {}
    dict_of_lists = mixed

    def __contains__(self, key):
        return False
    has_key = __contains__

    def copy(self):
        return self

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__,
                             self.reason)

    def __len__(self):
        return 0

    def __cmp__(self, other):
        return cmp({}, other)

    def keys(self):
        return []
    def iterkeys(self):
        return iter([])
    __iter__ = iterkeys
    items = keys
    iteritems = iterkeys
    values = keys
    itervalues = iterkeys



def _hide_passwd(items):
    for k, v in items:
        if ('password' in k
            or 'passwd' in k
            or 'pwd' in k
        ):
            yield k, '******'
        else:
            yield k, v
