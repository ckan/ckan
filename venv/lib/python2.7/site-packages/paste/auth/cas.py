# (c) 2005 Clark C. Evans
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# This code was written with funding by http://prometheusresearch.com
"""
CAS 1.0 Authentication

The Central Authentication System is a straight-forward single sign-on
mechanism developed by Yale University's ITS department.  It has since
enjoyed widespread success and is deployed at many major universities
and some corporations.

    https://clearinghouse.ja-sig.org/wiki/display/CAS/Home
    http://www.yale.edu/tp/auth/usingcasatyale.html

This implementation has the goal of maintaining current path arguments
passed to the system so that it can be used as middleware at any stage
of processing.  It has the secondary goal of allowing for other
authentication methods to be used concurrently.
"""
import urllib
from paste.request import construct_url
from paste.httpexceptions import HTTPSeeOther, HTTPForbidden

class CASLoginFailure(HTTPForbidden):
    """ The exception raised if the authority returns 'no' """

class CASAuthenticate(HTTPSeeOther):
    """ The exception raised to authenticate the user """

def AuthCASHandler(application, authority):
    """
    middleware to implement CAS 1.0 authentication

    There are several possible outcomes:

    0. If the REMOTE_USER environment variable is already populated;
       then this middleware is a no-op, and the request is passed along
       to the application.

    1. If a query argument 'ticket' is found, then an attempt to
       validate said ticket /w the authentication service done.  If the
       ticket is not validated; an 403 'Forbidden' exception is raised.
       Otherwise, the REMOTE_USER variable is set with the NetID that
       was validated and AUTH_TYPE is set to "cas".

    2. Otherwise, a 303 'See Other' is returned to the client directing
       them to login using the CAS service.  After logon, the service
       will send them back to this same URL, only with a 'ticket' query
       argument.

    Parameters:

        ``authority``

            This is a fully-qualified URL to a CAS 1.0 service. The URL
            should end with a '/' and have the 'login' and 'validate'
            sub-paths as described in the CAS 1.0 documentation.

    """
    assert authority.endswith("/") and authority.startswith("http")
    def cas_application(environ, start_response):
        username = environ.get('REMOTE_USER','')
        if username:
            return application(environ, start_response)
        qs = environ.get('QUERY_STRING','').split("&")
        if qs and qs[-1].startswith("ticket="):
            # assume a response from the authority
            ticket = qs.pop().split("=", 1)[1]
            environ['QUERY_STRING'] = "&".join(qs)
            service = construct_url(environ)
            args = urllib.urlencode(
                    {'service': service,'ticket': ticket})
            requrl = authority + "validate?" + args
            result = urllib.urlopen(requrl).read().split("\n")
            if 'yes' == result[0]:
                environ['REMOTE_USER'] = result[1]
                environ['AUTH_TYPE'] = 'cas'
                return application(environ, start_response)
            exce = CASLoginFailure()
        else:
            service = construct_url(environ)
            args = urllib.urlencode({'service': service})
            location = authority + "login?" + args
            exce = CASAuthenticate(location)
        return exce.wsgi_application(environ, start_response)
    return cas_application

middleware = AuthCASHandler

__all__ = ['CASLoginFailure', 'CASAuthenticate', 'AuthCASHandler' ]

if '__main__' == __name__:
    authority = "https://secure.its.yale.edu/cas/servlet/"
    from paste.wsgilib import dump_environ
    from paste.httpserver import serve
    from paste.httpexceptions import *
    serve(HTTPExceptionHandler(
             AuthCASHandler(dump_environ, authority)))
