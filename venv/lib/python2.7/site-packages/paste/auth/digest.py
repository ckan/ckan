# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Digest HTTP/1.1 Authentication

This module implements ``Digest`` authentication as described by
RFC 2617 [1]_ .

Basically, you just put this module before your application, and it
takes care of requesting and handling authentication requests.  This
module has been tested with several common browsers "out-in-the-wild".

>>> from paste.wsgilib import dump_environ
>>> from paste.httpserver import serve
>>> # from paste.auth.digest import digest_password, AuthDigestHandler
>>> realm = 'Test Realm'
>>> def authfunc(environ, realm, username):
...     return digest_password(realm, username, username)
>>> serve(AuthDigestHandler(dump_environ, realm, authfunc))
serving on...

This code has not been audited by a security expert, please use with
caution (or better yet, report security holes). At this time, this
implementation does not provide for further challenges, nor does it
support Authentication-Info header.  It also uses md5, and an option
to use sha would be a good thing.

.. [1] http://www.faqs.org/rfcs/rfc2617.html
"""
from paste.httpexceptions import HTTPUnauthorized
from paste.httpheaders import *
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import time, random
from urllib import quote as url_quote

def digest_password(realm, username, password):
    """ construct the appropriate hashcode needed for HTTP digest """
    return md5("%s:%s:%s" % (username, realm, password)).hexdigest()

class AuthDigestAuthenticator(object):
    """ implementation of RFC 2617 - HTTP Digest Authentication """
    def __init__(self, realm, authfunc):
        self.nonce    = {} # list to prevent replay attacks
        self.authfunc = authfunc
        self.realm    = realm

    def build_authentication(self, stale = ''):
        """ builds the authentication error """
        nonce  = md5(
            "%s:%s" % (time.time(), random.random())).hexdigest()
        opaque = md5(
            "%s:%s" % (time.time(), random.random())).hexdigest()
        self.nonce[nonce] = None
        parts = {'realm': self.realm, 'qop': 'auth',
                 'nonce': nonce, 'opaque': opaque }
        if stale:
            parts['stale'] = 'true'
        head = ", ".join(['%s="%s"' % (k, v) for (k, v) in parts.items()])
        head = [("WWW-Authenticate", 'Digest %s' % head)]
        return HTTPUnauthorized(headers=head)

    def compute(self, ha1, username, response, method,
                      path, nonce, nc, cnonce, qop):
        """ computes the authentication, raises error if unsuccessful """
        if not ha1:
            return self.build_authentication()
        ha2 = md5('%s:%s' % (method, path)).hexdigest()
        if qop:
            chk = "%s:%s:%s:%s:%s:%s" % (ha1, nonce, nc, cnonce, qop, ha2)
        else:
            chk = "%s:%s:%s" % (ha1, nonce, ha2)
        if response != md5(chk).hexdigest():
            if nonce in self.nonce:
                del self.nonce[nonce]
            return self.build_authentication()
        pnc = self.nonce.get(nonce,'00000000')
        if nc <= pnc:
            if nonce in self.nonce:
                del self.nonce[nonce]
            return self.build_authentication(stale = True)
        self.nonce[nonce] = nc
        return username

    def authenticate(self, environ):
        """ This function takes a WSGI environment and authenticates
            the request returning authenticated user or error.
        """
        method = REQUEST_METHOD(environ)
        fullpath = url_quote(SCRIPT_NAME(environ)) + url_quote(PATH_INFO(environ))
        authorization = AUTHORIZATION(environ)
        if not authorization:
            return self.build_authentication()
        (authmeth, auth) = authorization.split(" ", 1)
        if 'digest' != authmeth.lower():
            return self.build_authentication()
        amap = {}
        for itm in auth.split(", "):
            (k,v) = [s.strip() for s in itm.split("=", 1)]
            amap[k] = v.replace('"', '')
        try:
            username = amap['username']
            authpath = amap['uri']
            nonce    = amap['nonce']
            realm    = amap['realm']
            response = amap['response']
            assert authpath.split("?", 1)[0] in fullpath
            assert realm == self.realm
            qop      = amap.get('qop', '')
            cnonce   = amap.get('cnonce', '')
            nc       = amap.get('nc', '00000000')
            if qop:
                assert 'auth' == qop
                assert nonce and nc
        except:
            return self.build_authentication()
        ha1 = self.authfunc(environ, realm, username)
        return self.compute(ha1, username, response, method, authpath,
                            nonce, nc, cnonce, qop)

    __call__ = authenticate

class AuthDigestHandler(object):
    """
    middleware for HTTP Digest authentication (RFC 2617)

    This component follows the procedure below:

        0. If the REMOTE_USER environment variable is already populated;
           then this middleware is a no-op, and the request is passed
           along to the application.

        1. If the HTTP_AUTHORIZATION header was not provided or specifies
           an algorithem other than ``digest``, then a HTTPUnauthorized
           response is generated with the challenge.

        2. If the response is malformed or or if the user's credientials
           do not pass muster, another HTTPUnauthorized is raised.

        3. If all goes well, and the user's credintials pass; then
           REMOTE_USER environment variable is filled in and the
           AUTH_TYPE is listed as 'digest'.

    Parameters:

        ``application``

            The application object is called only upon successful
            authentication, and can assume ``environ['REMOTE_USER']``
            is set.  If the ``REMOTE_USER`` is already set, this
            middleware is simply pass-through.

        ``realm``

            This is a identifier for the authority that is requesting
            authorization.  It is shown to the user and should be unique
            within the domain it is being used.

        ``authfunc``

            This is a callback function which performs the actual
            authentication; the signature of this callback is:

              authfunc(environ, realm, username) -> hashcode

            This module provides a 'digest_password' helper function
            which can help construct the hashcode; it is recommended
            that the hashcode is stored in a database, not the user's
            actual password (since you only need the hashcode).
    """
    def __init__(self, application, realm, authfunc):
        self.authenticate = AuthDigestAuthenticator(realm, authfunc)
        self.application = application

    def __call__(self, environ, start_response):
        username = REMOTE_USER(environ)
        if not username:
            result = self.authenticate(environ)
            if isinstance(result, str):
                AUTH_TYPE.update(environ,'digest')
                REMOTE_USER.update(environ, result)
            else:
                return result.wsgi_application(environ, start_response)
        return self.application(environ, start_response)

middleware = AuthDigestHandler

__all__ = ['digest_password', 'AuthDigestHandler' ]

def make_digest(app, global_conf, realm, authfunc, **kw):
    """
    Grant access via digest authentication

    Config looks like this::

      [filter:grant]
      use = egg:Paste#auth_digest
      realm=myrealm
      authfunc=somepackage.somemodule:somefunction

    """
    from paste.util.import_string import eval_import
    import types
    authfunc = eval_import(authfunc)
    assert isinstance(authfunc, types.FunctionType), "authfunc must resolve to a function"
    return AuthDigestHandler(app, realm, authfunc)

if "__main__" == __name__:
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
