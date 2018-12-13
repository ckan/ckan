# (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
OpenID Authentication (Consumer)

OpenID is a distributed authentication system for single sign-on originally
developed at/for LiveJournal.com.

    http://openid.net/

URL. You can have multiple identities in the same way you can have multiple
URLs. All OpenID does is provide a way to prove that you own a URL (identity).
And it does this without passing around your password, your email address, or
anything you don't want it to. There's no profile exchange component at all:
your profiile is your identity URL, but recipients of your identity can then
learn more about you from any public, semantically interesting documents
linked thereunder (FOAF, RSS, Atom, vCARD, etc.).

``Note``: paste.auth.openid requires installation of the Python-OpenID
libraries::

    http://www.openidenabled.com/

This module is based highly off the consumer.py that Python OpenID comes with.

Using the OpenID Middleware
===========================

Using the OpenID middleware is fairly easy, the most minimal example using the
basic login form thats included::

    # Add to your wsgi app creation
    from paste.auth import open_id

    wsgi_app = open_id.middleware(wsgi_app, '/somewhere/to/store/openid/data')

You will now have the OpenID form available at /oid on your site. Logging in will
verify that the login worked.

A more complete login should involve having the OpenID middleware load your own
login page after verifying the OpenID URL so that you can retain the login
information in your webapp (session, cookies, etc.)::

    wsgi_app = open_id.middleware(wsgi_app, '/somewhere/to/store/openid/data',
                                  login_redirect='/your/login/code')

Your login code should then be configured to retrieve 'paste.auth.open_id' for
the users OpenID URL. If this key does not exist, the user has not logged in.

Once the login is retrieved, it should be saved in your webapp, and the user
should be redirected to wherever they would normally go after a successful
login.
"""

__all__ = ['AuthOpenIDHandler']

import cgi
import urlparse
import re

import paste.request
from paste import httpexceptions

def quoteattr(s):
    qs = cgi.escape(s, 1)
    return '"%s"' % (qs,)

# You may need to manually add the openid package into your
# python path if you don't have it installed with your system python.
# If so, uncomment the line below, and change the path where you have
# Python-OpenID.
# sys.path.append('/path/to/openid/')

from openid.store import filestore
from openid.consumer import consumer
from openid.oidutil import appendArgs

class AuthOpenIDHandler(object):
    """
    This middleware implements OpenID Consumer behavior to authenticate a
    URL against an OpenID Server.
    """

    def __init__(self, app, data_store_path, auth_prefix='/oid',
                 login_redirect=None, catch_401=False,
                 url_to_username=None):
        """
        Initialize the OpenID middleware

        ``app``
            Your WSGI app to call
            
        ``data_store_path``
            Directory to store crypto data in for use with OpenID servers.
            
        ``auth_prefix``
            Location for authentication process/verification
            
        ``login_redirect``
            Location to load after successful process of login
            
        ``catch_401``
            If true, then any 401 responses will turn into open ID login
            requirements.
            
        ``url_to_username``
            A function called like ``url_to_username(environ, url)``, which should
            return a string username.  If not given, the URL will be the username.
        """
        store = filestore.FileOpenIDStore(data_store_path)
        self.oidconsumer = consumer.OpenIDConsumer(store)

        self.app = app
        self.auth_prefix = auth_prefix
        self.data_store_path = data_store_path
        self.login_redirect = login_redirect
        self.catch_401 = catch_401
        self.url_to_username = url_to_username

    def __call__(self, environ, start_response):
        if environ['PATH_INFO'].startswith(self.auth_prefix):
            # Let's load everything into a request dict to pass around easier
            request = dict(environ=environ, start=start_response, body=[])
            request['base_url'] = paste.request.construct_url(environ, with_path_info=False,
                                                              with_query_string=False)

            path = re.sub(self.auth_prefix, '', environ['PATH_INFO'])
            request['parsed_uri'] = urlparse.urlparse(path)
            request['query'] = dict(paste.request.parse_querystring(environ))

            path = request['parsed_uri'][2]
            if path == '/' or not path:
                return self.render(request)
            elif path == '/verify':
                return self.do_verify(request)
            elif path == '/process':
                return self.do_process(request)
            else:
                return self.not_found(request)
        else:
            if self.catch_401:
                return self.catch_401_app_call(environ, start_response)
            return self.app(environ, start_response)

    def catch_401_app_call(self, environ, start_response):
        """
        Call the application, and redirect if the app returns a 401 response
        """
        was_401 = []
        def replacement_start_response(status, headers, exc_info=None):
            if int(status.split(None, 1)) == 401:
                # @@: Do I need to append something to go back to where we
                # came from?
                was_401.append(1)
                def dummy_writer(v):
                    pass
                return dummy_writer
            else:
                return start_response(status, headers, exc_info)
        app_iter = self.app(environ, replacement_start_response)
        if was_401:
            try:
                list(app_iter)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
            redir_url = paste.request.construct_url(environ, with_path_info=False,
                                                    with_query_string=False)
            exc = httpexceptions.HTTPTemporaryRedirect(redir_url)
            return exc.wsgi_application(environ, start_response)
        else:
            return app_iter

    def do_verify(self, request):
        """Process the form submission, initating OpenID verification.
        """

        # First, make sure that the user entered something
        openid_url = request['query'].get('openid_url')
        if not openid_url:
            return self.render(request, 'Enter an identity URL to verify.',
                        css_class='error', form_contents=openid_url)

        oidconsumer = self.oidconsumer

        # Then, ask the library to begin the authorization.
        # Here we find out the identity server that will verify the
        # user's identity, and get a token that allows us to
        # communicate securely with the identity server.
        status, info = oidconsumer.beginAuth(openid_url)

        # If the URL was unusable (either because of network
        # conditions, a server error, or that the response returned
        # was not an OpenID identity page), the library will return
        # an error code. Let the user know that that URL is unusable.
        if status in [consumer.HTTP_FAILURE, consumer.PARSE_ERROR]:
            if status == consumer.HTTP_FAILURE:
                fmt = 'Failed to retrieve <q>%s</q>'
            else:
                fmt = 'Could not find OpenID information in <q>%s</q>'

            message = fmt % (cgi.escape(openid_url),)
            return self.render(request, message, css_class='error', form_contents=openid_url)
        elif status == consumer.SUCCESS:
            # The URL was a valid identity URL. Now we construct a URL
            # that will get us to process the server response. We will
            # need the token from the beginAuth call when processing
            # the response. A cookie or a session object could be used
            # to accomplish this, but for simplicity here we just add
            # it as a query parameter of the return-to URL.
            return_to = self.build_url(request, 'process', token=info.token)

            # Now ask the library for the URL to redirect the user to
            # his OpenID server. It is required for security that the
            # return_to URL must be under the specified trust_root. We
            # just use the base_url for this server as a trust root.
            redirect_url = oidconsumer.constructRedirect(
                info, return_to, trust_root=request['base_url'])

            # Send the redirect response
            return self.redirect(request, redirect_url)
        else:
            assert False, 'Not reached'

    def do_process(self, request):
        """Handle the redirect from the OpenID server.
        """
        oidconsumer = self.oidconsumer

        # retrieve the token from the environment (in this case, the URL)
        token = request['query'].get('token', '')

        # Ask the library to check the response that the server sent
        # us.  Status is a code indicating the response type. info is
        # either None or a string containing more information about
        # the return type.
        status, info = oidconsumer.completeAuth(token, request['query'])

        css_class = 'error'
        openid_url = None
        if status == consumer.FAILURE and info:
            # In the case of failure, if info is non-None, it is the
            # URL that we were verifying. We include it in the error
            # message to help the user figure out what happened.
            openid_url = info
            fmt = "Verification of %s failed."
            message = fmt % (cgi.escape(openid_url),)
        elif status == consumer.SUCCESS:
            # Success means that the transaction completed without
            # error. If info is None, it means that the user cancelled
            # the verification.
            css_class = 'alert'
            if info:
                # This is a successful verification attempt. If this
                # was a real application, we would do our login,
                # comment posting, etc. here.
                openid_url = info
                if self.url_to_username:
                    username = self.url_to_username(request['environ'], openid_url)
                else:
                    username = openid_url
                if 'paste.auth_tkt.set_user' in request['environ']:
                    request['environ']['paste.auth_tkt.set_user'](username)
                if not self.login_redirect:
                    fmt = ("If you had supplied a login redirect path, you would have "
                           "been redirected there.  "
                           "You have successfully verified %s as your identity.")
                    message = fmt % (cgi.escape(openid_url),)
                else:
                    # @@: This stuff doesn't make sense to me; why not a remote redirect?
                    request['environ']['paste.auth.open_id'] = openid_url
                    request['environ']['PATH_INFO'] = self.login_redirect
                    return self.app(request['environ'], request['start'])
                    #exc = httpexceptions.HTTPTemporaryRedirect(self.login_redirect)
                    #return exc.wsgi_application(request['environ'], request['start'])
            else:
                # cancelled
                message = 'Verification cancelled'
        else:
            # Either we don't understand the code or there is no
            # openid_url included with the error. Give a generic
            # failure message. The library should supply debug
            # information in a log.
            message = 'Verification failed.'

        return self.render(request, message, css_class, openid_url)

    def build_url(self, request, action, **query):
        """Build a URL relative to the server base_url, with the given
        query parameters added."""
        base = urlparse.urljoin(request['base_url'], self.auth_prefix + '/' + action)
        return appendArgs(base, query)

    def redirect(self, request, redirect_url):
        """Send a redirect response to the given URL to the browser."""
        response_headers = [('Content-type', 'text/plain'),
                            ('Location', redirect_url)]
        request['start']('302 REDIRECT', response_headers)
        return ["Redirecting to %s" % redirect_url]

    def not_found(self, request):
        """Render a page with a 404 return code and a message."""
        fmt = 'The path <q>%s</q> was not understood by this server.'
        msg = fmt % (request['parsed_uri'],)
        openid_url = request['query'].get('openid_url')
        return self.render(request, msg, 'error', openid_url, status='404 Not Found')

    def render(self, request, message=None, css_class='alert', form_contents=None,
               status='200 OK', title="Python OpenID Consumer"):
        """Render a page."""
        response_headers = [('Content-type', 'text/html')]
        request['start'](str(status), response_headers)

        self.page_header(request, title)
        if message:
            request['body'].append("<div class='%s'>" % (css_class,))
            request['body'].append(message)
            request['body'].append("</div>")
        self.page_footer(request, form_contents)
        return request['body']

    def page_header(self, request, title):
        """Render the page header"""
        request['body'].append('''\
<html>
  <head><title>%s</title></head>
  <style type="text/css">
      * {
        font-family: verdana,sans-serif;
      }
      body {
        width: 50em;
        margin: 1em;
      }
      div {
        padding: .5em;
      }
      table {
        margin: none;
        padding: none;
      }
      .alert {
        border: 1px solid #e7dc2b;
        background: #fff888;
      }
      .error {
        border: 1px solid #ff0000;
        background: #ffaaaa;
      }
      #verify-form {
        border: 1px solid #777777;
        background: #dddddd;
        margin-top: 1em;
        padding-bottom: 0em;
      }
  </style>
  <body>
    <h1>%s</h1>
    <p>
      This example consumer uses the <a
      href="http://openid.schtuff.com/">Python OpenID</a> library. It
      just verifies that the URL that you enter is your identity URL.
    </p>
''' % (title, title))

    def page_footer(self, request, form_contents):
        """Render the page footer"""
        if not form_contents:
            form_contents = ''

        request['body'].append('''\
    <div id="verify-form">
      <form method="get" action=%s>
        Identity&nbsp;URL:
        <input type="text" name="openid_url" value=%s />
        <input type="submit" value="Verify" />
      </form>
    </div>
  </body>
</html>
''' % (quoteattr(self.build_url(request, 'verify')), quoteattr(form_contents)))


middleware = AuthOpenIDHandler

def make_open_id_middleware(
    app,
    global_conf,
    # Should this default to something, or inherit something from global_conf?:
    data_store_path,
    auth_prefix='/oid',
    login_redirect=None,
    catch_401=False,
    url_to_username=None,
    apply_auth_tkt=False,
    auth_tkt_logout_path=None):
    from paste.deploy.converters import asbool
    from paste.util import import_string
    catch_401 = asbool(catch_401)
    if url_to_username and isinstance(url_to_username, basestring):
        url_to_username = import_string.eval_import(url_to_username)
    apply_auth_tkt = asbool(apply_auth_tkt)
    new_app = AuthOpenIDHandler(
        app, data_store_path=data_store_path, auth_prefix=auth_prefix,
        login_redirect=login_redirect, catch_401=catch_401,
        url_to_username=url_to_username or None)
    if apply_auth_tkt:
        from paste.auth import auth_tkt
        new_app = auth_tkt.make_auth_tkt_middleware(
            new_app, global_conf, logout_path=auth_tkt_logout_path)
    return new_app
