try:
    STRING_TYPES = (str, unicode)
except NameError: #pragma NO COVER Python >= 3.0
    STRING_TYPES = (str,)

try:
    u = unicode
except NameError: #pragma NO COVER Python >= 3.0
    u = str
    b = bytes
else: #pragma NO COVER Python < 3.0
    b = str

import base64
if 'decodebytes' in base64.__dict__: #pragma NO COVER Python >= 3.0
    decodebytes = base64.decodebytes
    encodebytes = base64.encodebytes
    def decodestring(value):
        return base64.decodebytes(bytes(value, 'ascii')).decode('ascii')
    def encodestring(value):
        return base64.encodebytes(bytes(value, 'ascii')).decode('ascii')
else: #pragma NO COVER Python < 3.0
    decodebytes = base64.decodestring
    encodebytes = base64.encodestring
    decodestring = base64.decodestring
    encodestring = base64.encodestring

try:
    from urllib.parse import parse_qs
except ImportError: #pragma NO COVER Python < 3.0
    from cgi import parse_qs
    from cgi import parse_qsl
else: #pragma NO COVER Python >= 3.0
    from urllib.parse import parse_qsl

try:
    import ConfigParser
except ImportError: #pragma NO COVER Python >= 3.0
    from configparser import ConfigParser
    from configparser import ParsingError
else: #pragma NO COVER Python < 3.0
    from ConfigParser import SafeConfigParser as ConfigParser
    from ConfigParser import ParsingError

try:
    from Cookie import SimpleCookie
except ImportError: #pragma NO COVER Python >= 3.0
    from http.cookies import SimpleCookie
    from http.cookies import CookieError
else: #pragma NO COVER Python < 3.0
    from Cookie import CookieError

try:
    from itertools import izip_longest
except ImportError: #pragma NO COVER Python >= 3.0
    from itertools import zip_longest as izip_longest

try:
    from StringIO import StringIO
except ImportError: #pragma NO COVER Python >= 3.0
    from io import StringIO

try:
    from urllib import urlencode
except ImportError: #pragma NO COVER Python >= 3.0
    from urllib.parse import urlencode
    from urllib.parse import quote as url_quote
    from urllib.parse import unquote as url_unquote
else: #pragma NO COVER Python < 3.0
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote

try:
    from urlparse import urlparse
except ImportError: #pragma NO COVER Python >= 3.0
    from urllib.parse import urlparse
    from urllib.parse import urlunparse
else: #pragma NO COVER Python < 3.0
    from urlparse import urlunparse

import wsgiref.util
import wsgiref.headers

def REQUEST_METHOD(environ):
    return environ['REQUEST_METHOD']

def CONTENT_TYPE(environ):
    return environ.get('CONTENT_TYPE', '')

def USER_AGENT(environ):
    return environ.get('HTTP_USER_AGENT')

def AUTHORIZATION(environ):
    return environ.get('HTTP_AUTHORIZATION', '')

def get_cookies(environ):
    header = environ.get('HTTP_COOKIE', '')
    if 'paste.cookies' in environ:
        cookies, check_header = environ['paste.cookies']
        if check_header == header:
            return cookies
    cookies = SimpleCookie()
    try:
        cookies.load(header)
    except CookieError: #pragma NO COVER (can't see how to provoke this)
        pass
    environ['paste.cookies'] = (cookies, header)
    return cookies

def construct_url(environ):
    return wsgiref.util.request_uri(environ)

def header_value(environ, key):
    headers = wsgiref.headers.Headers(environ)
    values = headers.get(key)
    if not values:
        return ""
    if isinstance(values, list): #pragma NO COVER can't be true under Py3k.
        return ",".join(values)
    else:
        return values

def must_decode(value):
    if type(value) is b:
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return value.decode('latin1')
    return value

def must_encode(value):
    if type(value) is u:
        return value.encode('utf-8')
    return value
