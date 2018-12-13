# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Authentication via Multiple Methods

In some environments, the choice of authentication method to be used
depends upon the environment and is not "fixed".  This middleware allows
N authentication methods to be registered along with a goodness function
which determines which method should be used. The following example
demonstrates how to use both form and digest authentication in a server
stack; by default it uses form-based authentication unless
``*authmeth=digest`` is specified as a query argument.

>>> from paste.auth import form, cookie, digest, multi
>>> from paste.wsgilib import dump_environ
>>> from paste.httpserver import serve
>>>
>>> multi = multi.MultiHandler(dump_environ)
>>> def authfunc(environ, realm, user):
...     return digest.digest_password(realm, user, user)
>>> multi.add_method('digest', digest.middleware, "Test Realm", authfunc)
>>> multi.set_query_argument('digest')
>>>
>>> def authfunc(environ, username, password):
...     return username == password
>>> multi.add_method('form', form.middleware, authfunc)
>>> multi.set_default('form')
>>> serve(cookie.middleware(multi))
serving on...

"""

class MultiHandler(object):
    """
    Multiple Authentication Handler

    This middleware provides two othogonal facilities:

      - a manner to register any number of authentication middlewares

      - a mechanism to register predicates which cause one of the
        registered middlewares to be used depending upon the request

    If none of the predicates returns True, then the application is
    invoked directly without middleware
    """
    def __init__(self, application):
        self.application = application
        self.default = application
        self.binding = {}
        self.predicate = []
    def add_method(self, name, factory, *args, **kwargs):
        self.binding[name] = factory(self.application, *args, **kwargs)
    def add_predicate(self, name, checker):
        self.predicate.append((checker, self.binding[name]))
    def set_default(self, name):
        """ set default authentication method """
        self.default = self.binding[name]
    def set_query_argument(self, name, key = '*authmeth', value = None):
        """ choose authentication method based on a query argument """
        lookfor = "%s=%s" % (key, value or name)
        self.add_predicate(name,
            lambda environ: lookfor in environ.get('QUERY_STRING',''))
    def __call__(self, environ, start_response):
        for (checker, binding) in self.predicate:
            if checker(environ):
                return binding(environ, start_response)
        return self.default(environ, start_response)

middleware = MultiHandler

__all__ = ['MultiHandler']

if "__main__" == __name__:
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)

