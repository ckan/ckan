# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
Authentication via HTML Form

This is a very simple HTML form login screen that asks for the username
and password.  This middleware component requires that an authorization
function taking the name and passsword and that it be placed in your
application stack. This class does not include any session management
code or way to save the user's authorization; however, it is easy enough
to put ``paste.auth.cookie`` in your application stack.

>>> from paste.wsgilib import dump_environ
>>> from paste.httpserver import serve
>>> from paste.auth.cookie import AuthCookieHandler
>>> from paste.auth.form import AuthFormHandler
>>> def authfunc(environ, username, password):
...    return username == password
>>> serve(AuthCookieHandler(
...           AuthFormHandler(dump_environ, authfunc)))
serving on...

"""
from paste.request import construct_url, parse_formvars

TEMPLATE = """\
<html>
  <head><title>Please Login!</title></head>
  <body>
    <h1>Please Login</h1>
    <form action="%s" method="post">
      <dl>
        <dt>Username:</dt>
        <dd><input type="text" name="username"></dd>
        <dt>Password:</dt>
        <dd><input type="password" name="password"></dd>
      </dl>
      <input type="submit" name="authform" />
      <hr />
    </form>
  </body>
</html>
"""

class AuthFormHandler(object):
    """
    HTML-based login middleware

    This causes a HTML form to be returned if ``REMOTE_USER`` is
    not found in the ``environ``.  If the form is returned, the
    ``username`` and ``password`` combination are given to a
    user-supplied authentication function, ``authfunc``.  If this
    is successful, then application processing continues.

    Parameters:

        ``application``

            The application object is called only upon successful
            authentication, and can assume ``environ['REMOTE_USER']``
            is set.  If the ``REMOTE_USER`` is already set, this
            middleware is simply pass-through.

        ``authfunc``

            This is a mandatory user-defined function which takes a
            ``environ``, ``username`` and ``password`` for its first
            three arguments.  It should return ``True`` if the user is
            authenticated.

        ``template``

            This is an optional (a default is provided) HTML
            fragment that takes exactly one ``%s`` substution
            argument; which *must* be used for the form's ``action``
            to ensure that this middleware component does not alter
            the current path.  The HTML form must use ``POST`` and
            have two input names:  ``username`` and ``password``.

    Since the authentication form is submitted (via ``POST``)
    neither the ``PATH_INFO`` nor the ``QUERY_STRING`` are accessed,
    and hence the current path remains _unaltered_ through the
    entire authentication process. If authentication succeeds, the
    ``REQUEST_METHOD`` is converted from a ``POST`` to a ``GET``,
    so that a redirect is unnecessary (unlike most form auth
    implementations)
    """

    def __init__(self, application, authfunc, template=None):
        self.application = application
        self.authfunc = authfunc
        self.template = template or TEMPLATE

    def __call__(self, environ, start_response):
        username = environ.get('REMOTE_USER','')
        if username:
            return self.application(environ, start_response)

        if 'POST' == environ['REQUEST_METHOD']:
            formvars = parse_formvars(environ, include_get_vars=False)
            username = formvars.get('username')
            password = formvars.get('password')
            if username and password:
                if self.authfunc(environ, username, password):
                    environ['AUTH_TYPE'] = 'form'
                    environ['REMOTE_USER'] = username
                    environ['REQUEST_METHOD'] = 'GET'
                    environ['CONTENT_LENGTH'] = ''
                    environ['CONTENT_TYPE'] = ''
                    del environ['paste.parsed_formvars']
                    return self.application(environ, start_response)

        content = self.template % construct_url(environ)
        start_response("200 OK", [('Content-Type', 'text/html'),
                                  ('Content-Length', str(len(content)))])
        return [content]

middleware = AuthFormHandler

__all__ = ['AuthFormHandler']

def make_form(app, global_conf, realm, authfunc, **kw):
    """
    Grant access via form authentication

    Config looks like this::

      [filter:grant]
      use = egg:Paste#auth_form
      realm=myrealm
      authfunc=somepackage.somemodule:somefunction
      
    """
    from paste.util.import_string import eval_import
    import types
    authfunc = eval_import(authfunc)
    assert isinstance(authfunc, types.FunctionType), "authfunc must resolve to a function"
    template = kw.get('template')
    if template is not None:
        template = eval_import(template)
        assert isinstance(template, str), "template must resolve to a string"

    return AuthFormHandler(app, authfunc, template)

if "__main__" == __name__:
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
