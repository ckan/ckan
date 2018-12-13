# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Cookie "Saved" Authentication

This authentication middleware saves the current REMOTE_USER,
REMOTE_SESSION, and any other environment variables specified in a
cookie so that it can be retrieved during the next request without
requiring re-authentication. This uses a session cookie on the client
side (so it goes away when the user closes their window) and does
server-side expiration.

Following is a very simple example where a form is presented asking for
a user name (no actual checking), and dummy session identifier (perhaps
corresponding to a database session id) is stored in the cookie.

::

  >>> from paste.httpserver import serve
  >>> from paste.fileapp import DataApp
  >>> from paste.httpexceptions import *
  >>> from paste.auth.cookie import AuthCookieHandler
  >>> from paste.wsgilib import parse_querystring
  >>> def testapp(environ, start_response):
  ...     user = dict(parse_querystring(environ)).get('user','')
  ...     if user:
  ...         environ['REMOTE_USER'] = user
  ...         environ['REMOTE_SESSION'] = 'a-session-id'
  ...     if environ.get('REMOTE_USER'):
  ...         page = '<html><body>Welcome %s (%s)</body></html>'
  ...         page %= (environ['REMOTE_USER'], environ['REMOTE_SESSION'])
  ...     else:
  ...         page = ('<html><body><form><input name="user" />'
  ...                 '<input type="submit" /></form></body></html>')
  ...     return DataApp(page, content_type="text/html")(
  ...                    environ, start_response)
  >>> serve(AuthCookieHandler(testapp))
  serving on...

"""

import hmac, base64, random, time, warnings
try:
    from hashlib import sha1
except ImportError:
    # NOTE: We have to use the callable with hashlib (hashlib.sha1),
    # otherwise hmac only accepts the sha module object itself
    import sha as sha1
from paste.request import get_cookies

def make_time(value):
    return time.strftime("%Y%m%d%H%M", time.gmtime(value))
_signature_size = len(hmac.new('x', 'x', sha1).digest())
_header_size = _signature_size + len(make_time(time.time()))

# @@: Should this be using urllib.quote?
# build encode/decode functions to safely pack away values
_encode = [('\\', '\\x5c'), ('"', '\\x22'),
           ('=', '\\x3d'), (';', '\\x3b')]
_decode = [(v, k) for (k, v) in _encode]
_decode.reverse()
def encode(s, sublist = _encode):
    return reduce((lambda a, (b, c): a.replace(b, c)), sublist, str(s))
decode = lambda s: encode(s, _decode)

class CookieTooLarge(RuntimeError):
    def __init__(self, content, cookie):
        RuntimeError.__init__("Signed cookie exceeds maximum size of 4096")
        self.content = content
        self.cookie = cookie

_all_chars = ''.join([chr(x) for x in range(0, 255)])
def new_secret():
    """ returns a 64 byte secret """
    return ''.join(random.sample(_all_chars, 64))

class AuthCookieSigner(object):
    """
    save/restore ``environ`` entries via digially signed cookie

    This class converts content into a timed and digitally signed
    cookie, as well as having the facility to reverse this procedure.
    If the cookie, after the content is encoded and signed exceeds the
    maximum length (4096), then CookieTooLarge exception is raised.

    The timeout of the cookie is handled on the server side for a few
    reasons.  First, if a 'Expires' directive is added to a cookie, then
    the cookie becomes persistent (lasting even after the browser window
    has closed). Second, the user's clock may be wrong (perhaps
    intentionally). The timeout is specified in minutes; and expiration
    date returned is rounded to one second.

    Constructor Arguments:

        ``secret``

            This is a secret key if you want to syncronize your keys so
            that the cookie will be good across a cluster of computers.
            It is recommended via the HMAC specification (RFC 2104) that
            the secret key be 64 bytes since this is the block size of
            the hashing.  If you do not provide a secret key, a random
            one is generated each time you create the handler; this
            should be sufficient for most cases.

        ``timeout``

            This is the time (in minutes) from which the cookie is set
            to expire.  Note that on each request a new (replacement)
            cookie is sent, hence this is effectively a session timeout
            parameter for your entire cluster.  If you do not provide a
            timeout, it is set at 30 minutes.

        ``maxlen``

            This is the maximum size of the *signed* cookie; hence the
            actual content signed will be somewhat less.  If the cookie
            goes over this size, a ``CookieTooLarge`` exception is
            raised so that unexpected handling of cookies on the client
            side are avoided.  By default this is set at 4k (4096 bytes),
            which is the standard cookie size limit.

    """
    def __init__(self, secret = None, timeout = None, maxlen = None):
        self.timeout = timeout or 30
        if isinstance(timeout, basestring):
            raise ValueError(
                "Timeout must be a number (minutes), not a string (%r)"
                % timeout)
        self.maxlen  = maxlen or 4096
        self.secret = secret or new_secret()

    def sign(self, content):
        """
        Sign the content returning a valid cookie (that does not
        need to be escaped and quoted).  The expiration of this
        cookie is handled server-side in the auth() function.
        """
        cookie = base64.encodestring(
            hmac.new(self.secret, content, sha1).digest() +
            make_time(time.time() + 60*self.timeout) +
            content)
        cookie = cookie.replace("/", "_").replace("=", "~")
        cookie = cookie.replace('\n', '').replace('\r', '')
        if len(cookie) > self.maxlen:
            raise CookieTooLarge(content, cookie)
        return cookie

    def auth(self, cookie):
        """
        Authenticate the cooke using the signature, verify that it
        has not expired; and return the cookie's content
        """
        decode = base64.decodestring(
            cookie.replace("_", "/").replace("~", "="))
        signature = decode[:_signature_size]
        expires = decode[_signature_size:_header_size]
        content = decode[_header_size:]
        if signature == hmac.new(self.secret, content, sha1).digest():
            if int(expires) > int(make_time(time.time())):
                return content
            else:
                # This is the normal case of an expired cookie; just
                # don't bother doing anything here.
                pass
        else:
            # This case can happen if the server is restarted with a
            # different secret; or if the user's IP address changed
            # due to a proxy.  However, it could also be a break-in
            # attempt -- so should it be reported?
            pass

class AuthCookieEnviron(list):
    """
    a list of environment keys to be saved via cookie

    An instance of this object, found at ``environ['paste.auth.cookie']``
    lists the `environ` keys that were restored from or will be added
    to the digially signed cookie.  This object can be accessed from an
    `environ` variable by using this module's name.
    """
    def __init__(self, handler, scanlist):
        list.__init__(self, scanlist)
        self.handler = handler
    def append(self, value):
        if value in self:
            return
        list.append(self, str(value))

class AuthCookieHandler(object):
    """
    the actual handler that should be put in your middleware stack

    This middleware uses cookies to stash-away a previously authenticated
    user (and perhaps other variables) so that re-authentication is not
    needed.  This does not implement sessions; and therefore N servers
    can be syncronized to accept the same saved authentication if they
    all use the same cookie_name and secret.

    By default, this handler scans the `environ` for the REMOTE_USER
    and REMOTE_SESSION key; if found, it is stored. It can be
    configured to scan other `environ` keys as well -- but be careful
    not to exceed 2-3k (so that the encoded and signed cookie does not
    exceed 4k). You can ask it to handle other environment variables
    by doing:

       ``environ['paste.auth.cookie'].append('your.environ.variable')``


    Constructor Arguments:

        ``application``

            This is the wrapped application which will have access to
            the ``environ['REMOTE_USER']`` restored by this middleware.

        ``cookie_name``

            The name of the cookie used to store this content, by default
            it is ``PASTE_AUTH_COOKIE``.

        ``scanlist``

            This is the initial set of ``environ`` keys to
            save/restore to the signed cookie.  By default is consists
            only of ``REMOTE_USER`` and ``REMOTE_SESSION``; any tuple
            or list of environment keys will work.  However, be
            careful, as the total saved size is limited to around 3k.

        ``signer``

            This is the signer object used to create the actual cookie
            values, by default, it is ``AuthCookieSigner`` and is passed
            the remaining arguments to this function: ``secret``,
            ``timeout``, and ``maxlen``.

    At this time, each cookie is individually signed.  To store more
    than the 4k of data; it is possible to sub-class this object to
    provide different ``environ_name`` and ``cookie_name``
    """
    environ_name = 'paste.auth.cookie'
    cookie_name  = 'PASTE_AUTH_COOKIE'
    signer_class = AuthCookieSigner
    environ_class = AuthCookieEnviron

    def __init__(self, application, cookie_name=None, scanlist=None,
                 signer=None, secret=None, timeout=None, maxlen=None):
        if not signer:
            signer = self.signer_class(secret, timeout, maxlen)
        self.signer = signer
        self.scanlist = scanlist or ('REMOTE_USER','REMOTE_SESSION')
        self.application = application
        self.cookie_name = cookie_name or self.cookie_name

    def __call__(self, environ, start_response):
        if self.environ_name in environ:
            raise AssertionError("AuthCookie already installed!")
        scanlist = self.environ_class(self, self.scanlist)
        jar = get_cookies(environ)
        if jar.has_key(self.cookie_name):
            content = self.signer.auth(jar[self.cookie_name].value)
            if content:
                for pair in content.split(";"):
                    (k, v) = pair.split("=")
                    k = decode(k)
                    if k not in scanlist:
                        scanlist.append(k)
                    if k in environ:
                        continue
                    environ[k] = decode(v)
                    if 'REMOTE_USER' == k:
                        environ['AUTH_TYPE'] = 'cookie'
        environ[self.environ_name] = scanlist
        if "paste.httpexceptions" in environ:
            warnings.warn("Since paste.httpexceptions is hooked in your "
                "processing chain before paste.auth.cookie, if an "
                "HTTPRedirection is raised, the cookies this module sets "
                "will not be included in your response.\n")

        def response_hook(status, response_headers, exc_info=None):
            """
            Scan the environment for keys specified in the scanlist,
            pack up their values, signs the content and issues a cookie.
            """
            scanlist = environ.get(self.environ_name)
            assert scanlist and isinstance(scanlist, self.environ_class)
            content = []
            for k in scanlist:
                v = environ.get(k)
                if v is not None:
                    if type(v) is not str:
                        raise ValueError(
                            "The value of the environmental variable %r "
                            "is not a str (only str is allowed; got %r)"
                            % (k, v))
                    content.append("%s=%s" % (encode(k), encode(v)))
            if content:
                content = ";".join(content)
                content = self.signer.sign(content)
                cookie = '%s=%s; Path=/;' % (self.cookie_name, content)
                if 'https' == environ['wsgi.url_scheme']:
                    cookie += ' secure;'
                response_headers.append(('Set-Cookie', cookie))
            return start_response(status, response_headers, exc_info)
        return self.application(environ, response_hook)

middleware = AuthCookieHandler

# Paste Deploy entry point:
def make_auth_cookie(
    app, global_conf,
    # Should this get picked up from global_conf somehow?:
    cookie_name='PASTE_AUTH_COOKIE',
    scanlist=('REMOTE_USER', 'REMOTE_SESSION'),
    # signer cannot be set
    secret=None,
    timeout=30,
    maxlen=4096):
    """
    This middleware uses cookies to stash-away a previously
    authenticated user (and perhaps other variables) so that
    re-authentication is not needed.  This does not implement
    sessions; and therefore N servers can be syncronized to accept the
    same saved authentication if they all use the same cookie_name and
    secret.

    By default, this handler scans the `environ` for the REMOTE_USER
    and REMOTE_SESSION key; if found, it is stored. It can be
    configured to scan other `environ` keys as well -- but be careful
    not to exceed 2-3k (so that the encoded and signed cookie does not
    exceed 4k). You can ask it to handle other environment variables
    by doing:

       ``environ['paste.auth.cookie'].append('your.environ.variable')``

    Configuration:

        ``cookie_name``

            The name of the cookie used to store this content, by
            default it is ``PASTE_AUTH_COOKIE``.

        ``scanlist``

            This is the initial set of ``environ`` keys to
            save/restore to the signed cookie.  By default is consists
            only of ``REMOTE_USER`` and ``REMOTE_SESSION``; any
            space-separated list of environment keys will work.
            However, be careful, as the total saved size is limited to
            around 3k.

        ``secret``

            The secret that will be used to sign the cookies.  If you
            don't provide one (and none is set globally) then a random
            secret will be created.  Each time the server is restarted
            a new secret will then be created and all cookies will
            become invalid!  This can be any string value.

        ``timeout``

            The time to keep the cookie, expressed in minutes.  This
            is handled server-side, so a new cookie with a new timeout
            is added to every response.

        ``maxlen``

            The maximum length of the cookie that is sent (default 4k,
            which is a typical browser maximum)
        
    """
    if isinstance(scanlist, basestring):
        scanlist = scanlist.split()
    if secret is None and global_conf.get('secret'):
        secret = global_conf['secret']
    try:
        timeout = int(timeout)
    except ValueError:
        raise ValueError('Bad value for timeout (must be int): %r'
                         % timeout)
    try:
        maxlen = int(maxlen)
    except ValueError:
        raise ValueError('Bad value for maxlen (must be int): %r'
                         % maxlen)
    return AuthCookieHandler(
        app, cookie_name=cookie_name, scanlist=scanlist,
        secret=secret, timeout=timeout, maxlen=maxlen)

__all__ = ['AuthCookieHandler', 'AuthCookieSigner', 'AuthCookieEnviron']

if "__main__" == __name__:
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

