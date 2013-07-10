import simplejson as json
import simplejson.encoder as json_encoder


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
           '__ne__', '__setitem__', 'clear', 'copy', 'fromkeys', 'get',
           'has_key', 'items', 'iteritems', 'iterkeys', 'itervalues', 'keys',
           'pop', 'popitem', 'setdefault', 'update', 'values']:
    setattr(LazyJSONObject, fn, _loads_method(fn))


class JSONString(str):
    '''a type for already-encoded JSON'''
    pass


def _encode_jsonstring(s):
    if isinstance(s, JSONString):
        return s
    return json_encoder.encode_basestring(s)


class LazyJSONEncoder(json.JSONEncoder):
    '''JSON encoder that handles LazyJSONObject elements'''
    def iterencode(self, o, _one_shot=False):
        '''
        most of JSONEncoder.iterencode() copied so that _encode_jsonstring
        may be used instead of encode_basestring
        '''
        if self.check_circular:
            markers = {}
        else:
            markers = None

        def floatstr(o, allow_nan=self.allow_nan,
                     _repr=json_encoder.FLOAT_REPR,
                     _inf=json_encoder.PosInf,
                     _neginf=-json_encoder.PosInf):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text
        _iterencode = json_encoder._make_iterencode(
            markers, self.default, _encode_jsonstring, self.indent, floatstr,
            self.key_separator, self.item_separator, self.sort_keys,
            self.skipkeys, _one_shot, self.use_decimal,
            self.namedtuple_as_object, self.tuple_as_array,
            self.bigint_as_string, self.item_sort_key,
            self.encoding, Decimal=json_encoder.Decimal)
        return _iterencode(o, 0)

    def default(self, o):
        if hasattr(o, 'to_json_string'):
            return JSONString(o.to_json_string())
        return json.JSONEncoder.default(self, o)
