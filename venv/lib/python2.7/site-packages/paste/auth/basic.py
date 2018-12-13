# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Basic HTTP/1.0 Authentication

This module implements ``Basic`` authentication as described in
HTTP/1.0 specification [1]_ .  Do not use this module unless you
are using SSL or need to work with very out-dated clients, instead
use ``digest`` authentication.

>>> from paste.wsgilib import dump_environ
>>> from paste.httpserver import serve
>>> # from paste.auth.basic import AuthBasicHandler
>>> realm = 'Test Realm'
>>> def authfunc(environ, username, password):
...     return username == password
>>> serve(AuthBasicHandler(dump_environ, realm, authfunc))
serving on...

.. [1] http://www.w3.org/Protocols/HTTP/1.0/draft-ietf-http-spec.html#BasicAA
"""
from paste.httpexceptions import HTTPUnauthorized
from paste.httpheaders import *

class AuthBasicAuthenticator(object):
    """
    implements ``Basic`` authentication details
    """
    type = 'basic'
    def __init__(self, realm, authfunc):
        self.realm = realm
        self.authfunc = authfunc

    def build_authentication(self):
        head = WWW_AUTHENTICATE.tuples('Basic realm="%s"' % self.realm)
        return HTTPUnauthorized(headers=head)

    def authenticate(self, environ):
        authorization = AUTHORIZATION(environ)
        if not authorization:
            return self.build_authentication()
        (authmeth, auth) = authorization.split(' ', 1)
        if 'basic' != authmeth.lower():
            return self.build_authentication()
        auth = auth.strip().decode('base64')
        username, password = auth.split(':', 1)
        if self.authfunc(environ, username, password):
            return username
        return self.build_authentication()

    __call__ = authenticate

class AuthBasicHandler(object):
    """
    HTTP/1.0 ``Basic`` authentication middleware

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

            This is a mandatory user-defined function which takes a
            ``environ``, ``username`` and ``password`` for its first
            three arguments.  It should return ``True`` if the user is
            authenticated.

    """
    def __init__(self, application, realm, authfunc):
        self.application = application
        self.authenticate = AuthBasicAuthenticator(realm, authfunc)

    def __call__(self, environ, start_response):
        username = REMOTE_USER(environ)
        if not username:
            result = self.authenticate(environ)
            if isinstance(result, str):
                AUTH_TYPE.update(environ, 'basic')
                REMOTE_USER.update(environ, result)
            else:
                return result.wsgi_application(environ, start_response)
        return self.application(environ, start_response)

middleware = AuthBasicHandler

__all__ = ['AuthBasicHandler']

def make_basic(app, global_conf, realm, authfunc, **kw):
    """
    Grant access via basic authentication

    Config looks like this::

      [filter:grant]
      use = egg:Paste#auth_basic
      realm=myrealm
      authfunc=somepackage.somemodule:somefunction
      
    """
    from paste.util.import_string import eval_import
    import types
    authfunc = eval_import(authfunc)
    assert isinstance(authfunc, types.FunctionType), "authfunc must resolve to a function"
    return AuthBasicHandler(app, realm, authfunc)
    

if "__main__" == __name__:
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
