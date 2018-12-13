"""Utility functions used by various web helpers.

This module contains support functions used by other helpers, and functions for
URL manipulation. Most of these helpers predate the 0.6 reorganization; they
would have been put in other subpackages if they have been created later.
"""
import cgi
import copy
import sys
import urllib
import urlparse
from UserDict import DictMixin
from xml.sax.saxutils import XMLGenerator

try:
    from urlparse import parse_qs
except ImportError:   # Python < 2.6
    from cgi import parse_qs


def update_params(_url, _debug=False, **params):
    """Update query parameters in a URL.

    ``_url`` is any URL, with or without a query string.

    ``\*\*params`` are query parameters to add or replace. Each value may be a
    string, a list of strings, or None. Passing a list generates multiple
    values for the same parameter. Passing None deletes the corresponding
    parameter if present.

    Return the new URL.

    *Debug mode:* if a pseudo-parameter ``_debug=True`` is passed,
    return a tuple: ``[0]`` is the URL without query string or fragment,
    ``[1]`` is the final query parameters as a dict, and ``[2]`` is the
    fragment part of the original URL or the empty string.

    Usage:

    >>> update_params("foo", new1="NEW1")
    'foo?new1=NEW1'
    >>> update_params("foo?p=1", p="2")
    'foo?p=2'
    >>> update_params("foo?p=1", p=None)
    'foo'
    >>> update_params("http://example.com/foo?new1=OLD1#myfrag", new1="NEW1")
    'http://example.com/foo?new1=NEW1#myfrag'
    >>> update_params("http://example.com/foo?new1=OLD1#myfrag", new1="NEW1", _debug=True)
    ('http://example.com/foo', {'new1': 'NEW1'}, 'myfrag')
    >>> update_params("http://www.mau.de?foo=2", brrr=3)
    'http://www.mau.de?foo=2&brrr=3'
    >>> update_params("http://www.mau.de?foo=A&foo=B", foo=["C", "D"])
    'http://www.mau.de?foo=C&foo=D'

    """
    url, fragment = urlparse.urldefrag(_url)
    if "?" in url:
        url, qs = url.split("?", 1)
        query = parse_qs(qs)
    else:
        query = {}
    for key, value in params.iteritems():
        if value is not None:
            query[key] = value
        elif key in query:
            del query[key]
    if _debug:
        return url, query, fragment
    qs = urllib.urlencode(query, True)
    if qs:
        qs = "?" + qs
    if fragment:
        fragment = "#" + fragment
    return "%s%s%s" % (url, qs, fragment)

def cgi_escape(s, quote=False):
    """Replace special characters '&', '<' and '>' by SGML entities.

    This is a slightly more efficient version of the cgi.escape by
    using 'in' membership to test if the replace is needed.

    This function returns a plain string. Programs using the HTML builder
    should call ``webhelpers.html.builder.escape()`` instead of this to prevent
    double-escaping.

    Changed in WebHelpers 1.2: escape single-quote as well as double-quote.

    """
    if '&' in s:
        s = s.replace("&", "&amp;") # Must be done first!
    if '<' in s:
        s = s.replace("<", "&lt;")
    if '>' in s:
        s = s.replace(">", "&gt;")
    if quote:
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
    return s

def html_escape(s):
    """HTML-escape a string or object.
    
    This converts any non-string objects passed into it to strings
    (actually, using ``unicode()``).  All values returned are
    non-unicode strings (using ``&#num;`` entities for all non-ASCII
    characters).
    
    None is treated specially, and returns the empty string.
    
    This function returns a plain string. Programs using the HTML builder
    should wrap the result in ``literal()`` to prevent double-escaping.

    """
    if s is None:
        return ''
    if not isinstance(s, basestring):
        if hasattr(s, '__unicode__'):
            s = unicode(s)
        else:
            s = str(s)
    s = cgi_escape(s, True)
    if isinstance(s, unicode):
        s = s.encode('ascii', 'xmlcharrefreplace')
    return s


def iri_to_uri(iri):
    """
    Convert an IRI portion to a URI portion suitable for inclusion in a URL.

    (An IRI is an Internationalized Resource Identifier.)

    This is the algorithm from section 3.1 of RFC 3987.  However, since 
    we are assuming input is either UTF-8 or unicode already, we can 
    simplify things a little from the full method.

    Returns an ASCII string containing the encoded result.

    """
    # Called by webhelpers.feedgenerator
    #
    # The list of safe characters here is constructed from the printable ASCII
    # characters that are not explicitly excluded by the list at the end of
    # section 3.1 of RFC 3987.
    if iri is None:
        return iri
    return urllib.quote(iri, safe='/#%[]=:;$&()+,!?')


class Partial(object):
    
    """
    A partial function object.

    Equivalent to functools.partial, which was introduced in Python 2.5.

    """
    
    def __init__(*args, **kw):
        self = args[0]
        self.fn, self.args, self.kw = (args[1], args[2:], kw)
    
    def __call__(self, *args, **kw):
        if kw and self.kw:
            d = self.kw.copy()
            d.update(kw)
        else:
            d = kw or self.kw
        return self.fn(*(self.args + args), **d)

class SimplerXMLGenerator(XMLGenerator):
    """A subclass of Python's SAX XMLGenerator."""

    # Used by webhelpers.feedgenerator

    def addQuickElement(self, name, contents=None, attrs=None):
        """Add an element with no children."""
        if attrs is None:
            attrs = {}
        self.startElement(name, attrs)
        if contents is not None:
            self.characters(contents)
        self.endElement(name)

class UnicodeMultiDict(DictMixin):
    
    """
    A MultiDict wrapper that decodes returned values to unicode on the fly. 
    
    Decoding is not applied to assigned values.

    The key/value contents are assumed to be ``str``/``strs`` or
    ``str``/``FieldStorages`` (as is returned by the :func:`paste.request.parse`
    functions).

    Can optionally also decode keys when the ``decode_keys`` argument is
    True.

    ``FieldStorage`` instances are cloned, and the clone's ``filename``
    variable is decoded. Its ``name`` variable is decoded when ``decode_keys``
    is enabled.

    """
    
    def __init__(self, multi=None, encoding=None, errors='strict',
                 decode_keys=False):
        self.multi = multi
        if encoding is None:
            encoding = sys.getdefaultencoding()
        self.encoding = encoding
        self.errors = errors
        self.decode_keys = decode_keys

    def _decode_key(self, key):
        if self.decode_keys:
            key = key.decode(self.encoding, self.errors)
        return key

    def _decode_value(self, value):
        """
        Decode the specified (``str`` or `FieldStorage``) value to unicode. 
        
        ``FieldStorage`` objects are specially handled.
        
        """
        if isinstance(value, cgi.FieldStorage):
            # decode FieldStorage's field name and filename
            value = copy.copy(value)
            if self.decode_keys:
                value.name = value.name.decode(self.encoding, self.errors)
            value.filename = value.filename.decode(self.encoding, self.errors)
        else:
            try:
                value = value.decode(self.encoding, self.errors)
            except AttributeError:
                pass
        return value

    def __getitem__(self, key):
        return self._decode_value(self.multi.__getitem__(key))

    def __setitem__(self, key, value):
        self.multi.__setitem__(key, value)

    def add(self, key, value):
        """Add the key and value, not overwriting any previous value."""
        self.multi.add(key, value)

    def getall(self, key):
        """Return list of all values matching the key (may be an empty list)."""
        return [self._decode_value(v) for v in self.multi.getall(key)]

    def getone(self, key):
        """Return one value matching key.  Raise KeyError if multiple matches."""
        return self._decode_value(self.multi.getone(key))

    def mixed(self):
        """Return dict where values are single values or a list of values.

        The value is a single value if key appears just once.  It is 
        a list of values when a key/value appears more than once in this 
        dictionary.  This is similar to the kind of dictionary often 
        used to represent the variables in a web request.
        
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
        """Return dict where each key is associated with a list of values."""
        unicode_dict = {}
        for key, value in self.multi.dict_of_lists().iteritems():
            value = [self._decode_value(value) for value in value]
            unicode_dict[self._decode_key(key)] = value
        return unicode_dict

    def __delitem__(self, key):
        self.multi.__delitem__(key)

    def __contains__(self, key):
        return self.multi.__contains__(key)

    has_key = __contains__

    def clear(self):
        self.multi.clear()

    def copy(self):
        return UnicodeMultiDict(self.multi.copy(), self.encoding, self.errors)

    def setdefault(self, key, default=None):
        return self._decode_value(self.multi.setdefault(key, default))

    def pop(self, key, *args):
        return self._decode_value(self.multi.pop(key, *args))

    def popitem(self):
        k, v = self.multi.popitem()
        return (self._decode_key(k), self._decode_value(v))

    def __repr__(self):
        items = ', '.join(['(%r, %r)' % v for v in self.items()])
        return '%s([%s])' % (self.__class__.__name__, items)

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
        return [(self._decode_key(k), self._decode_value(v)) for \
                    k, v in self.multi.iteritems()]

    def iteritems(self):
        for k, v in self.multi.iteritems():
            yield (self._decode_key(k), self._decode_value(v))

    def values(self):
        return [self._decode_value(v) for v in self.multi.itervalues()]

    def itervalues(self):
        for v in self.multi.itervalues():
            yield self._decode_value(v)
