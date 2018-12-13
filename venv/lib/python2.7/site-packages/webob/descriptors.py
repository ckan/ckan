import warnings
import re
from datetime import datetime, date

from webob.byterange import Range, ContentRange
from webob.etag import IfRange, NoIfRange
from webob.datetime_utils import parse_date, serialize_date
from webob.util import rfc_reference


CHARSET_RE = re.compile(r';\s*charset=([^;]*)', re.I)
QUOTES_RE = re.compile('"(.*)"')
SCHEME_RE = re.compile(r'^[a-z]+:', re.I)


_not_given = object()

def environ_getter(key, default=_not_given, rfc_section=None):
    doc = "Gets and sets the %r key in the environment." % key
    doc += rfc_reference(key, rfc_section)
    if default is _not_given:
        def fget(req):
            return req.environ[key]
        def fset(req, val):
            req.environ[key] = val
        fdel = None
    else:
        def fget(req):
            return req.environ.get(key, default)
        def fset(req, val):
            if val is None:
                if key in req.environ:
                    del req.environ[key]
            else:
                req.environ[key] = val
        def fdel(req):
            del req.environ[key]
    return property(fget, fset, fdel, doc=doc)


def upath_property(key):
    def fget(req):
        return req.environ.get(key, '').decode('UTF8', req.unicode_errors)
    def fset(req, val):
        req.environ[key] = val.encode('UTF8', req.unicode_errors)
    return property(fget, fset, doc='upath_property(%r)' % key)


def header_getter(header, rfc_section):
    doc = "Gets and sets and deletes the %s header." % header
    doc += rfc_reference(header, rfc_section)
    key = header.lower()

    def fget(r):
        for k, v in r._headerlist:
            if k.lower() == key:
                return v

    def fset(r, value):
        fdel(r)
        if value is not None:
            if isinstance(value, unicode):
                value = value.encode('ISO-8859-1') # standard encoding for headers
            r._headerlist.append((header, value))

    def fdel(r):
        items = r._headerlist
        for i in range(len(items)-1, -1, -1):
            if items[i][0].lower() == key:
                del items[i]

    return property(fget, fset, fdel, doc)




def converter(prop, parse, serialize, convert_name=None):
    assert isinstance(prop, property)
    convert_name = convert_name or "%r and %r" % (parse.__name__,
                                                  serialize.__name__)
    doc = prop.__doc__ or ''
    doc += "  Converts it using %s." % convert_name
    hget, hset = prop.fget, prop.fset
    def fget(r):
        return parse(hget(r))
    def fset(r, val):
        if val is not None:
            val = serialize(val)
        hset(r, val)
    return property(fget, fset, prop.fdel, doc)



def list_header(header, rfc_section):
    prop = header_getter(header, rfc_section)
    return converter(prop, parse_list, serialize_list, 'list')

def parse_list(value):
    if not value:
        return None
    return tuple(filter(None, [v.strip() for v in value.split(',')]))

def serialize_list(value):
    if isinstance(value, unicode):
        return str(value)
    elif isinstance(value, str):
        return value
    else:
        return ', '.join(map(str, value))




def converter_date(prop):
    return converter(prop, parse_date, serialize_date, 'HTTP date')

def date_header(header, rfc_section):
    return converter_date(header_getter(header, rfc_section))







class deprecated_property(object):
    """
    Wraps a descriptor, with a deprecation warning or error
    """
    def __init__(self, descriptor, attr, message, warning=True):
        self.descriptor = descriptor
        self.attr = attr
        self.message = message
        self.warning = warning

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        self.warn()
        return self.descriptor.__get__(obj, type)

    def __set__(self, obj, value):
        self.warn()
        self.descriptor.__set__(obj, value)

    def __delete__(self, obj):
        self.warn()
        self.descriptor.__delete__(obj)

    def __repr__(self):
        return '<Deprecated attribute %s: %r>' % (
            self.attr,
            self.descriptor)

    def warn(self):
        if not self.warning:
            raise DeprecationWarning(
                'The attribute %s is deprecated: %s' % (self.attr, self.message))
        else:
            warnings.warn(
                'The attribute %s is deprecated: %s' % (self.attr, self.message),
                DeprecationWarning,
                stacklevel=3)





########################
## Converter functions
########################


# FIXME: weak entity tags are not supported, would need special class
def parse_etag_response(value):
    """
    See:
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.19
        * http://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.11
    """
    if value is not None:
        unquote_match = QUOTES_RE.match(value)
        if unquote_match is not None:
            value = unquote_match.group(1)
            value = value.replace('\\"', '"')
        return value

def serialize_etag_response(value):
    return '"%s"' % value.replace('"', '\\"')

def parse_if_range(value):
    if not value:
        return NoIfRange
    else:
        return IfRange.parse(value)

def serialize_if_range(value):
    if isinstance(value, (datetime, date)):
        return serialize_date(value)
    if not isinstance(value, str):
        value = str(value)
    return value or None

def parse_range(value):
    if not value:
        return None
    # Might return None too:
    return Range.parse(value)

def serialize_range(value):
    if isinstance(value, (list, tuple)):
        if len(value) != 2:
            raise ValueError(
                "If setting .range to a list or tuple, it must be of length 2 (not %r)"
                % value)
        value = Range([value])
    if value is None:
        return None
    value = str(value)
    return value or None

def parse_int(value):
    if value is None or value == '':
        return None
    return int(value)

def parse_int_safe(value):
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        return None

serialize_int = str

def parse_content_range(value):
    if not value or not value.strip():
        return None
    # May still return None
    return ContentRange.parse(value)

def serialize_content_range(value):
    if isinstance(value, (tuple, list)):
        if len(value) not in (2, 3):
            raise ValueError(
                "When setting content_range to a list/tuple, it must "
                "be length 2 or 3 (not %r)" % value)
        if len(value) == 2:
            begin, end = value
            length = None
        else:
            begin, end, length = value
        value = ContentRange(begin, end, length)
    value = str(value).strip()
    if not value:
        return None
    return value




_rx_auth_param = re.compile(r'([a-z]+)=(".*?"|[^,]*)(?:\Z|, *)')

def parse_auth_params(params):
    r = {}
    for k, v in _rx_auth_param.findall(params):
        r[k] = v.strip('"')
    return r

# see http://lists.w3.org/Archives/Public/ietf-http-wg/2009OctDec/0297.html
known_auth_schemes = ['Basic', 'Digest', 'WSSE', 'HMACDigest', 'GoogleLogin', 'Cookie', 'OpenID']
known_auth_schemes = dict.fromkeys(known_auth_schemes, None)

def parse_auth(val):
    if val is not None:
        authtype, params = val.split(' ', 1)
        if authtype in known_auth_schemes:
            if authtype == 'Basic' and '"' not in params:
                # this is the "Authentication: Basic XXXXX==" case
                pass
            else:
                params = parse_auth_params(params)
        return authtype, params
    return val

def serialize_auth(val):
    if isinstance(val, (tuple, list)):
        authtype, params = val
        if isinstance(params, dict):
            params = ', '.join(map('%s="%s"'.__mod__, params.items()))
        assert isinstance(params, str)
        return '%s %s' % (authtype, params)
    return val
