# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""WSGI Wrappers for a Request and Response

The WSGIRequest and WSGIResponse objects are light wrappers to make it easier
to deal with an incoming request and sending a response.
"""
import re
import warnings
from pprint import pformat
from Cookie import SimpleCookie
from paste.request import EnvironHeaders, get_cookie_dict, \
    parse_dict_querystring, parse_formvars
from paste.util.multidict import MultiDict, UnicodeMultiDict
from paste.registry import StackedObjectProxy
from paste.response import HeaderDict
from paste.wsgilib import encode_unicode_app_iter
from paste.httpheaders import ACCEPT_LANGUAGE
from paste.util.mimeparse import desired_matches

__all__ = ['WSGIRequest', 'WSGIResponse']

_CHARSET_RE = re.compile(r';\s*charset=([^;]*)', re.I)

class DeprecatedSettings(StackedObjectProxy):
    def _push_object(self, obj):
        warnings.warn('paste.wsgiwrappers.settings is deprecated: Please use '
                      'paste.wsgiwrappers.WSGIRequest.defaults instead',
                      DeprecationWarning, 3)
        WSGIResponse.defaults._push_object(obj)
        StackedObjectProxy._push_object(self, obj)

# settings is deprecated: use WSGIResponse.defaults instead
settings = DeprecatedSettings(default=dict())

class environ_getter(object):
    """For delegating an attribute to a key in self.environ."""
    # @@: Also __set__?  Should setting be allowed?
    def __init__(self, key, default='', default_factory=None):
        self.key = key
        self.default = default
        self.default_factory = default_factory
    def __get__(self, obj, type=None):
        if type is None:
            return self
        if self.key not in obj.environ:
            if self.default_factory:
                val = obj.environ[self.key] = self.default_factory()
                return val
            else:
                return self.default
        return obj.environ[self.key]

    def __repr__(self):
        return '<Proxy for WSGI environ %r key>' % self.key

class WSGIRequest(object):
    """WSGI Request API Object

    This object represents a WSGI request with a more friendly interface.
    This does not expose every detail of the WSGI environment, and attempts
    to express nothing beyond what is available in the environment
    dictionary.

    The only state maintained in this object is the desired ``charset``,
    its associated ``errors`` handler, and the ``decode_param_names``
    option.

    The incoming parameter values will be automatically coerced to unicode
    objects of the ``charset`` encoding when ``charset`` is set. The
    incoming parameter names are not decoded to unicode unless the
    ``decode_param_names`` option is enabled.

    When unicode is expected, ``charset`` will overridden by the the
    value of the ``Content-Type`` header's charset parameter if one was
    specified by the client.

    The class variable ``defaults`` specifies default values for
    ``charset``, ``errors``, and ``langauge``. These can be overridden for the
    current request via the registry.
        
    The ``language`` default value is considered the fallback during i18n
    translations to ensure in odd cases that mixed languages don't occur should
    the ``language`` file contain the string but not another language in the
    accepted languages list. The ``language`` value only applies when getting
    a list of accepted languages from the HTTP Accept header.
    
    This behavior is duplicated from Aquarium, and may seem strange but is
    very useful. Normally, everything in the code is in "en-us".  However, 
    the "en-us" translation catalog is usually empty.  If the user requests
    ``["en-us", "zh-cn"]`` and a translation isn't found for a string in
    "en-us", you don't want gettext to fallback to "zh-cn".  You want it to 
    just use the string itself.  Hence, if a string isn't found in the
    ``language`` catalog, the string in the source code will be used.

    *All* other state is kept in the environment dictionary; this is
    essential for interoperability.

    You are free to subclass this object.

    """
    defaults = StackedObjectProxy(default=dict(charset=None, errors='replace',
                                               decode_param_names=False,
                                               language='en-us'))
    def __init__(self, environ):
        self.environ = environ
        # This isn't "state" really, since the object is derivative:
        self.headers = EnvironHeaders(environ)
        
        defaults = self.defaults._current_obj()
        self.charset = defaults.get('charset')
        if self.charset:
            # There's a charset: params will be coerced to unicode. In that
            # case, attempt to use the charset specified by the browser
            browser_charset = self.determine_browser_charset()
            if browser_charset:
                self.charset = browser_charset
        self.errors = defaults.get('errors', 'strict')
        self.decode_param_names = defaults.get('decode_param_names', False)
        self._languages = None
    
    body = environ_getter('wsgi.input')
    scheme = environ_getter('wsgi.url_scheme')
    method = environ_getter('REQUEST_METHOD')
    script_name = environ_getter('SCRIPT_NAME')
    path_info = environ_getter('PATH_INFO')

    def urlvars(self):
        """
        Return any variables matched in the URL (e.g.,
        ``wsgiorg.routing_args``).
        """
        if 'paste.urlvars' in self.environ:
            return self.environ['paste.urlvars']
        elif 'wsgiorg.routing_args' in self.environ:
            return self.environ['wsgiorg.routing_args'][1]
        else:
            return {}
    urlvars = property(urlvars, doc=urlvars.__doc__)
    
    def is_xhr(self):
        """Returns a boolean if X-Requested-With is present and a XMLHttpRequest"""
        return self.environ.get('HTTP_X_REQUESTED_WITH', '') == 'XMLHttpRequest'
    is_xhr = property(is_xhr, doc=is_xhr.__doc__)
    
    def host(self):
        """Host name provided in HTTP_HOST, with fall-back to SERVER_NAME"""
        return self.environ.get('HTTP_HOST', self.environ.get('SERVER_NAME'))
    host = property(host, doc=host.__doc__)

    def languages(self):
        """Return a list of preferred languages, most preferred first.
        
        The list may be empty.
        """
        if self._languages is not None:
            return self._languages
        acceptLanguage = self.environ.get('HTTP_ACCEPT_LANGUAGE')
        langs = ACCEPT_LANGUAGE.parse(self.environ)
        fallback = self.defaults.get('language', 'en-us')
        if not fallback:
            return langs
        if fallback not in langs:
            langs.append(fallback)
        index = langs.index(fallback)
        langs[index+1:] = []
        self._languages = langs
        return self._languages
    languages = property(languages, doc=languages.__doc__)
    
    def _GET(self):
        return parse_dict_querystring(self.environ)

    def GET(self):
        """
        Dictionary-like object representing the QUERY_STRING
        parameters. Always present, if possibly empty.

        If the same key is present in the query string multiple times, a
        list of its values can be retrieved from the ``MultiDict`` via
        the ``getall`` method.

        Returns a ``MultiDict`` container or a ``UnicodeMultiDict`` when
        ``charset`` is set.
        """
        params = self._GET()
        if self.charset:
            params = UnicodeMultiDict(params, encoding=self.charset,
                                      errors=self.errors,
                                      decode_keys=self.decode_param_names)
        return params
    GET = property(GET, doc=GET.__doc__)

    def _POST(self):
        return parse_formvars(self.environ, include_get_vars=False)

    def POST(self):
        """Dictionary-like object representing the POST body.

        Most values are encoded strings, or unicode strings when
        ``charset`` is set. There may also be FieldStorage objects
        representing file uploads. If this is not a POST request, or the
        body is not encoded fields (e.g., an XMLRPC request) then this
        will be empty.

        This will consume wsgi.input when first accessed if applicable,
        but the raw version will be put in
        environ['paste.parsed_formvars'].

        Returns a ``MultiDict`` container or a ``UnicodeMultiDict`` when
        ``charset`` is set.
        """
        params = self._POST()
        if self.charset:
            params = UnicodeMultiDict(params, encoding=self.charset,
                                      errors=self.errors,
                                      decode_keys=self.decode_param_names)
        return params
    POST = property(POST, doc=POST.__doc__)

    def params(self):
        """Dictionary-like object of keys from POST, GET, URL dicts

        Return a key value from the parameters, they are checked in the
        following order: POST, GET, URL

        Additional methods supported:

        ``getlist(key)``
            Returns a list of all the values by that key, collected from
            POST, GET, URL dicts

        Returns a ``MultiDict`` container or a ``UnicodeMultiDict`` when
        ``charset`` is set.
        """
        params = MultiDict()
        params.update(self._POST())
        params.update(self._GET())
        if self.charset:
            params = UnicodeMultiDict(params, encoding=self.charset,
                                      errors=self.errors,
                                      decode_keys=self.decode_param_names)
        return params
    params = property(params, doc=params.__doc__)

    def cookies(self):
        """Dictionary of cookies keyed by cookie name.

        Just a plain dictionary, may be empty but not None.
        
        """
        return get_cookie_dict(self.environ)
    cookies = property(cookies, doc=cookies.__doc__)

    def determine_browser_charset(self):
        """
        Determine the encoding as specified by the browser via the
        Content-Type's charset parameter, if one is set
        """
        charset_match = _CHARSET_RE.search(self.headers.get('Content-Type', ''))
        if charset_match:
            return charset_match.group(1)

    def match_accept(self, mimetypes):
        """Return a list of specified mime-types that the browser's HTTP Accept
        header allows in the order provided."""
        return desired_matches(mimetypes, 
                               self.environ.get('HTTP_ACCEPT', '*/*'))

    def __repr__(self):
        """Show important attributes of the WSGIRequest"""
        pf = pformat
        msg = '<%s.%s object at 0x%x method=%s,' % \
            (self.__class__.__module__, self.__class__.__name__,
             id(self), pf(self.method))
        msg += '\nscheme=%s, host=%s, script_name=%s, path_info=%s,' % \
            (pf(self.scheme), pf(self.host), pf(self.script_name),
             pf(self.path_info))
        msg += '\nlanguages=%s,' % pf(self.languages)
        if self.charset:
            msg += ' charset=%s, errors=%s,' % (pf(self.charset),
                                                pf(self.errors))
        msg += '\nGET=%s,' % pf(self.GET)
        msg += '\nPOST=%s,' % pf(self.POST)
        msg += '\ncookies=%s>' % pf(self.cookies)
        return msg

class WSGIResponse(object):
    """A basic HTTP response with content, headers, and out-bound cookies

    The class variable ``defaults`` specifies default values for
    ``content_type``, ``charset`` and ``errors``. These can be overridden
    for the current request via the registry.

    """
    defaults = StackedObjectProxy(
        default=dict(content_type='text/html', charset='utf-8', 
                     errors='strict', headers={'Cache-Control':'no-cache'})
        )
    def __init__(self, content='', mimetype=None, code=200):
        self._iter = None
        self._is_str_iter = True

        self.content = content
        self.headers = HeaderDict()
        self.cookies = SimpleCookie()
        self.status_code = code

        defaults = self.defaults._current_obj()
        if not mimetype:
            mimetype = defaults.get('content_type', 'text/html')
            charset = defaults.get('charset')
            if charset:
                mimetype = '%s; charset=%s' % (mimetype, charset)
        self.headers.update(defaults.get('headers', {}))
        self.headers['Content-Type'] = mimetype
        self.errors = defaults.get('errors', 'strict')

    def __str__(self):
        """Returns a rendition of the full HTTP message, including headers.

        When the content is an iterator, the actual content is replaced with the
        output of str(iterator) (to avoid exhausting the iterator).
        """
        if self._is_str_iter:
            content = ''.join(self.get_content())
        else:
            content = str(self.content)
        return '\n'.join(['%s: %s' % (key, value)
            for key, value in self.headers.headeritems()]) \
            + '\n\n' + content
    
    def __call__(self, environ, start_response):
        """Convenience call to return output and set status information
        
        Conforms to the WSGI interface for calling purposes only.
        
        Example usage:
        
        .. code-block:: python

            def wsgi_app(environ, start_response):
                response = WSGIResponse()
                response.write("Hello world")
                response.headers['Content-Type'] = 'latin1'
                return response(environ, start_response)
        
        """
        status_text = STATUS_CODE_TEXT[self.status_code]
        status = '%s %s' % (self.status_code, status_text)
        response_headers = self.headers.headeritems()
        for c in self.cookies.values():
            response_headers.append(('Set-Cookie', c.output(header='')))
        start_response(status, response_headers)
        is_file = isinstance(self.content, file)
        if 'wsgi.file_wrapper' in environ and is_file:
            return environ['wsgi.file_wrapper'](self.content)
        elif is_file:
            return iter(lambda: self.content.read(), '')
        return self.get_content()
    
    def determine_charset(self):
        """
        Determine the encoding as specified by the Content-Type's charset
        parameter, if one is set
        """
        charset_match = _CHARSET_RE.search(self.headers.get('Content-Type', ''))
        if charset_match:
            return charset_match.group(1)
    
    def has_header(self, header):
        """
        Case-insensitive check for a header
        """
        warnings.warn('WSGIResponse.has_header is deprecated, use '
                      'WSGIResponse.headers.has_key instead', DeprecationWarning,
                      2)
        return self.headers.has_key(header)

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/',
                   domain=None, secure=None, httponly=None):
        """
        Define a cookie to be sent via the outgoing HTTP headers
        """
        self.cookies[key] = value
        for var_name, var_value in [
            ('max_age', max_age), ('path', path), ('domain', domain),
            ('secure', secure), ('expires', expires), ('httponly', httponly)]:
            if var_value is not None and var_value is not False:
                self.cookies[key][var_name.replace('_', '-')] = var_value

    def delete_cookie(self, key, path='/', domain=None):
        """
        Notify the browser the specified cookie has expired and should be
        deleted (via the outgoing HTTP headers)
        """
        self.cookies[key] = ''
        if path is not None:
            self.cookies[key]['path'] = path
        if domain is not None:
            self.cookies[key]['domain'] = domain
        self.cookies[key]['expires'] = 0
        self.cookies[key]['max-age'] = 0

    def _set_content(self, content):
        if hasattr(content, '__iter__'):
            self._iter = content
            if isinstance(content, list):
                self._is_str_iter = True
            else:
                self._is_str_iter = False
        else:
            self._iter = [content]
            self._is_str_iter = True
    content = property(lambda self: self._iter, _set_content,
                       doc='Get/set the specified content, where content can '
                       'be: a string, a list of strings, a generator function '
                       'that yields strings, or an iterable object that '
                       'produces strings.')

    def get_content(self):
        """
        Returns the content as an iterable of strings, encoding each element of
        the iterator from a Unicode object if necessary.
        """
        charset = self.determine_charset()
        if charset:
            return encode_unicode_app_iter(self.content, charset, self.errors)
        else:
            return self.content
    
    def wsgi_response(self):
        """
        Return this WSGIResponse as a tuple of WSGI formatted data, including:
        (status, headers, iterable)
        """
        status_text = STATUS_CODE_TEXT[self.status_code]
        status = '%s %s' % (self.status_code, status_text)
        response_headers = self.headers.headeritems()
        for c in self.cookies.values():
            response_headers.append(('Set-Cookie', c.output(header='')))
        return status, response_headers, self.get_content()
    
    # The remaining methods partially implement the file-like object interface.
    # See http://docs.python.org/lib/bltin-file-objects.html
    def write(self, content):
        if not self._is_str_iter:
            raise IOError, "This %s instance's content is not writable: (content " \
                'is an iterator)' % self.__class__.__name__
        self.content.append(content)

    def flush(self):
        pass

    def tell(self):
        if not self._is_str_iter:
            raise IOError, 'This %s instance cannot tell its position: (content ' \
                'is an iterator)' % self.__class__.__name__
        return sum([len(chunk) for chunk in self._iter])

    ########################################
    ## Content-type and charset

    def charset__get(self):
        """
        Get/set the charset (in the Content-Type)
        """
        header = self.headers.get('content-type')
        if not header:
            return None
        match = _CHARSET_RE.search(header)
        if match:
            return match.group(1)
        return None

    def charset__set(self, charset):
        if charset is None:
            del self.charset
            return
        try:
            header = self.headers.pop('content-type')
        except KeyError:
            raise AttributeError(
                "You cannot set the charset when no content-type is defined")
        match = _CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        header += '; charset=%s' % charset
        self.headers['content-type'] = header

    def charset__del(self):
        try:
            header = self.headers.pop('content-type')
        except KeyError:
            # Don't need to remove anything
            return
        match = _CHARSET_RE.search(header)
        if match:
            header = header[:match.start()] + header[match.end():]
        self.headers['content-type'] = header

    charset = property(charset__get, charset__set, charset__del, doc=charset__get.__doc__)

    def content_type__get(self):
        """
        Get/set the Content-Type header (or None), *without* the
        charset or any parameters.

        If you include parameters (or ``;`` at all) when setting the
        content_type, any existing parameters will be deleted;
        otherwise they will be preserved.
        """
        header = self.headers.get('content-type')
        if not header:
            return None
        return header.split(';', 1)[0]

    def content_type__set(self, value):
        if ';' not in value:
            header = self.headers.get('content-type', '')
            if ';' in header:
                params = header.split(';', 1)[1]
                value += ';' + params
        self.headers['content-type'] = value

    def content_type__del(self):
        try:
            del self.headers['content-type']
        except KeyError:
            pass

    content_type = property(content_type__get, content_type__set,
                            content_type__del, doc=content_type__get.__doc__)

## @@ I'd love to remove this, but paste.httpexceptions.get_exception
##    doesn't seem to work...
# See http://www.w3.org/Protocols/rfc2616/rfc2616-sec10.html
STATUS_CODE_TEXT = {
    100: 'CONTINUE',
    101: 'SWITCHING PROTOCOLS',
    200: 'OK',
    201: 'CREATED',
    202: 'ACCEPTED',
    203: 'NON-AUTHORITATIVE INFORMATION',
    204: 'NO CONTENT',
    205: 'RESET CONTENT',
    206: 'PARTIAL CONTENT',
    226: 'IM USED',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'FOUND',
    303: 'SEE OTHER',
    304: 'NOT MODIFIED',
    305: 'USE PROXY',
    306: 'RESERVED',
    307: 'TEMPORARY REDIRECT',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'PRECONDITION FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'REQUESTED RANGE NOT SATISFIABLE',
    417: 'EXPECTATION FAILED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'GATEWAY TIMEOUT',
    505: 'HTTP VERSION NOT SUPPORTED',
}
