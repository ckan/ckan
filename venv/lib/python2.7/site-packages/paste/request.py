# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# (c) 2005 Ian Bicking and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
This module provides helper routines with work directly on a WSGI
environment to solve common requirements.

   * get_cookies(environ)
   * parse_querystring(environ)
   * parse_formvars(environ, include_get_vars=True)
   * construct_url(environ, with_query_string=True, with_path_info=True,
                   script_name=None, path_info=None, querystring=None)
   * path_info_split(path_info)
   * path_info_pop(environ)
   * resolve_relative_url(url, environ)

"""
import cgi
from Cookie import SimpleCookie, CookieError
from StringIO import StringIO
import urlparse
import urllib
try:
    from UserDict import DictMixin
except ImportError:
    from paste.util.UserDict24 import DictMixin
from paste.util.multidict import MultiDict

__all__ = ['get_cookies', 'get_cookie_dict', 'parse_querystring',
           'parse_formvars', 'construct_url', 'path_info_split',
           'path_info_pop', 'resolve_relative_url', 'EnvironHeaders']

def get_cookies(environ):
    """
    Gets a cookie object (which is a dictionary-like object) from the
    request environment; caches this value in case get_cookies is
    called again for the same request.

    """
    header = environ.get('HTTP_COOKIE', '')
    if environ.has_key('paste.cookies'):
        cookies, check_header = environ['paste.cookies']
        if check_header == header:
            return cookies
    cookies = SimpleCookie()
    try:
        cookies.load(header)
    except CookieError:
        pass
    environ['paste.cookies'] = (cookies, header)
    return cookies

def get_cookie_dict(environ):
    """Return a *plain* dictionary of cookies as found in the request.

    Unlike ``get_cookies`` this returns a dictionary, not a
    ``SimpleCookie`` object.  For incoming cookies a dictionary fully
    represents the information.  Like ``get_cookies`` this caches and
    checks the cache.
    """
    header = environ.get('HTTP_COOKIE')
    if not header:
        return {}
    if environ.has_key('paste.cookies.dict'):
        cookies, check_header = environ['paste.cookies.dict']
        if check_header == header:
            return cookies
    cookies = SimpleCookie()
    try:
        cookies.load(header)
    except CookieError:
        pass
    result = {}
    for name in cookies:
        result[name] = cookies[name].value
    environ['paste.cookies.dict'] = (result, header)
    return result

def parse_querystring(environ):
    """
    Parses a query string into a list like ``[(name, value)]``.
    Caches this value in case parse_querystring is called again
    for the same request.

    You can pass the result to ``dict()``, but be aware that keys that
    appear multiple times will be lost (only the last value will be
    preserved).

    """
    source = environ.get('QUERY_STRING', '')
    if not source:
        return []
    if 'paste.parsed_querystring' in environ:
        parsed, check_source = environ['paste.parsed_querystring']
        if check_source == source:
            return parsed
    parsed = cgi.parse_qsl(source, keep_blank_values=True,
                           strict_parsing=False)
    environ['paste.parsed_querystring'] = (parsed, source)
    return parsed

def parse_dict_querystring(environ):
    """Parses a query string like parse_querystring, but returns a MultiDict

    Caches this value in case parse_dict_querystring is called again
    for the same request.

    Example::

        >>> environ = {'QUERY_STRING': 'day=Monday&user=fred&user=jane'}
        >>> parsed = parse_dict_querystring(environ)

        >>> parsed['day']
        'Monday'
        >>> parsed['user']
        'fred'
        >>> parsed.getall('user')
        ['fred', 'jane']

    """
    source = environ.get('QUERY_STRING', '')
    if not source:
        return MultiDict()
    if 'paste.parsed_dict_querystring' in environ:
        parsed, check_source = environ['paste.parsed_dict_querystring']
        if check_source == source:
            return parsed
    parsed = cgi.parse_qsl(source, keep_blank_values=True,
                           strict_parsing=False)
    multi = MultiDict(parsed)
    environ['paste.parsed_dict_querystring'] = (multi, source)
    return multi

def parse_formvars(environ, include_get_vars=True):
    """Parses the request, returning a MultiDict of form variables.

    If ``include_get_vars`` is true then GET (query string) variables
    will also be folded into the MultiDict.

    All values should be strings, except for file uploads which are
    left as ``FieldStorage`` instances.

    If the request was not a normal form request (e.g., a POST with an
    XML body) then ``environ['wsgi.input']`` won't be read.
    """
    source = environ['wsgi.input']
    if 'paste.parsed_formvars' in environ:
        parsed, check_source = environ['paste.parsed_formvars']
        if check_source == source:
            if include_get_vars:
                parsed.update(parse_querystring(environ))
            return parsed
    # @@: Shouldn't bother FieldStorage parsing during GET/HEAD and
    # fake_out_cgi requests
    type = environ.get('CONTENT_TYPE', '').lower()
    if ';' in type:
        type = type.split(';', 1)[0]
    fake_out_cgi = type not in ('', 'application/x-www-form-urlencoded',
                                'multipart/form-data')
    # FieldStorage assumes a default CONTENT_LENGTH of -1, but a
    # default of 0 is better:
    if not environ.get('CONTENT_LENGTH'):
        environ['CONTENT_LENGTH'] = '0'
    # Prevent FieldStorage from parsing QUERY_STRING during GET/HEAD
    # requests
    old_query_string = environ.get('QUERY_STRING','')
    environ['QUERY_STRING'] = ''
    if fake_out_cgi:
        input = StringIO('')
        old_content_type = environ.get('CONTENT_TYPE')
        old_content_length = environ.get('CONTENT_LENGTH')
        environ['CONTENT_LENGTH'] = '0'
        environ['CONTENT_TYPE'] = ''    
    else:
        input = environ['wsgi.input']
    fs = cgi.FieldStorage(fp=input,
                          environ=environ,
                          keep_blank_values=1)
    environ['QUERY_STRING'] = old_query_string
    if fake_out_cgi:
        environ['CONTENT_TYPE'] = old_content_type
        environ['CONTENT_LENGTH'] = old_content_length
    formvars = MultiDict()
    if isinstance(fs.value, list):
        for name in fs.keys():
            values = fs[name]
            if not isinstance(values, list):
                values = [values]
            for value in values:
                if not value.filename:
                    value = value.value
                formvars.add(name, value)
    environ['paste.parsed_formvars'] = (formvars, source)
    if include_get_vars:
        formvars.update(parse_querystring(environ))
    return formvars

def construct_url(environ, with_query_string=True, with_path_info=True,
                  script_name=None, path_info=None, querystring=None):
    """Reconstructs the URL from the WSGI environment.

    You may override SCRIPT_NAME, PATH_INFO, and QUERYSTRING with
    the keyword arguments.

    """
    url = environ['wsgi.url_scheme']+'://'

    if environ.get('HTTP_HOST'):
        host = environ['HTTP_HOST']
        port = None
        if ':' in host:
            host, port = host.split(':', 1)
            if environ['wsgi.url_scheme'] == 'https':
                if port == '443':
                    port = None
            elif environ['wsgi.url_scheme'] == 'http':
                if port == '80':
                    port = None
        url += host
        if port:
            url += ':%s' % port
    else:
        url += environ['SERVER_NAME']
        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']

    if script_name is None:
        url += urllib.quote(environ.get('SCRIPT_NAME',''))
    else:
        url += urllib.quote(script_name)
    if with_path_info:
        if path_info is None:
            url += urllib.quote(environ.get('PATH_INFO',''))
        else:
            url += urllib.quote(path_info)
    if with_query_string:
        if querystring is None:
            if environ.get('QUERY_STRING'):
                url += '?' + environ['QUERY_STRING']
        elif querystring:
            url += '?' + querystring
    return url

def resolve_relative_url(url, environ):
    """
    Resolve the given relative URL as being relative to the
    location represented by the environment.  This can be used
    for redirecting to a relative path.  Note: if url is already
    absolute, this function will (intentionally) have no effect
    on it.

    """
    cur_url = construct_url(environ, with_query_string=False)
    return urlparse.urljoin(cur_url, url)

def path_info_split(path_info):
    """
    Splits off the first segment of the path.  Returns (first_part,
    rest_of_path).  first_part can be None (if PATH_INFO is empty), ''
    (if PATH_INFO is '/'), or a name without any /'s.  rest_of_path
    can be '' or a string starting with /.

    """
    if not path_info:
        return None, ''
    assert path_info.startswith('/'), (
        "PATH_INFO should start with /: %r" % path_info)
    path_info = path_info.lstrip('/')
    if '/' in path_info:
        first, rest = path_info.split('/', 1)
        return first, '/' + rest
    else:
        return path_info, ''

def path_info_pop(environ):
    """
    'Pops' off the next segment of PATH_INFO, pushing it onto
    SCRIPT_NAME, and returning that segment.

    For instance::

        >>> def call_it(script_name, path_info):
        ...     env = {'SCRIPT_NAME': script_name, 'PATH_INFO': path_info}
        ...     result = path_info_pop(env)
        ...     print 'SCRIPT_NAME=%r; PATH_INFO=%r; returns=%r' % (
        ...         env['SCRIPT_NAME'], env['PATH_INFO'], result)
        >>> call_it('/foo', '/bar')
        SCRIPT_NAME='/foo/bar'; PATH_INFO=''; returns='bar'
        >>> call_it('/foo/bar', '')
        SCRIPT_NAME='/foo/bar'; PATH_INFO=''; returns=None
        >>> call_it('/foo/bar', '/')
        SCRIPT_NAME='/foo/bar/'; PATH_INFO=''; returns=''
        >>> call_it('', '/1/2/3')
        SCRIPT_NAME='/1'; PATH_INFO='/2/3'; returns='1'
        >>> call_it('', '//1/2')
        SCRIPT_NAME='//1'; PATH_INFO='/2'; returns='1'

    """
    path = environ.get('PATH_INFO', '')
    if not path:
        return None
    while path.startswith('/'):
        environ['SCRIPT_NAME'] += '/'
        path = path[1:]
    if '/' not in path:
        environ['SCRIPT_NAME'] += path
        environ['PATH_INFO'] = ''
        return path
    else:
        segment, path = path.split('/', 1)
        environ['PATH_INFO'] = '/' + path
        environ['SCRIPT_NAME'] += segment
        return segment

_parse_headers_special = {
    # This is a Zope convention, but we'll allow it here:
    'HTTP_CGI_AUTHORIZATION': 'Authorization',
    'CONTENT_LENGTH': 'Content-Length',
    'CONTENT_TYPE': 'Content-Type',
    }

def parse_headers(environ):
    """
    Parse the headers in the environment (like ``HTTP_HOST``) and
    yield a sequence of those (header_name, value) tuples.
    """
    # @@: Maybe should parse out comma-separated headers?
    for cgi_var, value in environ.iteritems():
        if cgi_var in _parse_headers_special:
            yield _parse_headers_special[cgi_var], value
        elif cgi_var.startswith('HTTP_'):
            yield cgi_var[5:].title().replace('_', '-'), value

class EnvironHeaders(DictMixin):
    """An object that represents the headers as present in a
    WSGI environment.

    This object is a wrapper (with no internal state) for a WSGI
    request object, representing the CGI-style HTTP_* keys as a
    dictionary.  Because a CGI environment can only hold one value for
    each key, this dictionary is single-valued (unlike outgoing
    headers).
    """

    def __init__(self, environ):
        self.environ = environ

    def _trans_name(self, name):
        key = 'HTTP_'+name.replace('-', '_').upper()
        if key == 'HTTP_CONTENT_LENGTH':
            key = 'CONTENT_LENGTH'
        elif key == 'HTTP_CONTENT_TYPE':
            key = 'CONTENT_TYPE'
        return key

    def _trans_key(self, key):
        if key == 'CONTENT_TYPE':
            return 'Content-Type'
        elif key == 'CONTENT_LENGTH':
            return 'Content-Length'
        elif key.startswith('HTTP_'):
            return key[5:].replace('_', '-').title()
        else:
            return None
        
    def __getitem__(self, item):
        return self.environ[self._trans_name(item)]

    def __setitem__(self, item, value):
        # @@: Should this dictionary be writable at all?
        self.environ[self._trans_name(item)] = value

    def __delitem__(self, item):
        del self.environ[self._trans_name(item)]

    def __iter__(self):
        for key in self.environ:
            name = self._trans_key(key)
            if name is not None:
                yield name

    def keys(self):
        return list(iter(self))

    def __contains__(self, item):
        return self._trans_name(item) in self.environ

def _cgi_FieldStorage__repr__patch(self):
    """ monkey patch for FieldStorage.__repr__

    Unbelievely, the default __repr__ on FieldStorage reads
    the entire file content instead of being sane about it.
    This is a simple replacement that doesn't do that
    """
    if self.file:
        return "FieldStorage(%r, %r)" % (
                self.name, self.filename)
    return "FieldStorage(%r, %r, %r)" % (
             self.name, self.filename, self.value)

cgi.FieldStorage.__repr__ = _cgi_FieldStorage__repr__patch

if __name__ == '__main__':
    import doctest
    doctest.testmod()
