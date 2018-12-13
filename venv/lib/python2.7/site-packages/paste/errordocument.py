# (c) 2005-2006 James Gardner <james@pythonweb.org>
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
"""
Middleware to display error documents for certain status codes

The middleware in this module can be used to intercept responses with
specified status codes and internally forward the request to an appropriate
URL where the content can be displayed to the user as an error document.
"""

import warnings
import sys
from urlparse import urlparse
from paste.recursive import ForwardRequestException, RecursiveMiddleware, RecursionLoop
from paste.util import converters
from paste.response import replace_header

def forward(app, codes):
    """
    Intercepts a response with a particular status code and returns the
    content from a specified URL instead.

    The arguments are:

    ``app``
        The WSGI application or middleware chain.

    ``codes``
        A dictionary of integer status codes and the URL to be displayed
        if the response uses that code.

    For example, you might want to create a static file to display a
    "File Not Found" message at the URL ``/error404.html`` and then use
    ``forward`` middleware to catch all 404 status codes and display the page
    you created. In this example ``app`` is your exisiting WSGI
    applicaiton::

        from paste.errordocument import forward
        app = forward(app, codes={404:'/error404.html'})

    """
    for code in codes:
        if not isinstance(code, int):
            raise TypeError('All status codes should be type int. '
                '%s is not valid'%repr(code))

    def error_codes_mapper(code, message, environ, global_conf, codes):
        if codes.has_key(code):
            return codes[code]
        else:
            return None

    #return _StatusBasedRedirect(app, error_codes_mapper, codes=codes)
    return RecursiveMiddleware(
        StatusBasedForward(
            app,
            error_codes_mapper,
            codes=codes,
        )
    )

class StatusKeeper(object):
    def __init__(self, app, status, url, headers):
        self.app = app
        self.status = status
        self.url = url
        self.headers = headers

    def __call__(self, environ, start_response):
        def keep_status_start_response(status, headers, exc_info=None):
            for header, value in headers:
                if header.lower() == 'set-cookie':
                    self.headers.append((header, value))
                else:
                    replace_header(self.headers, header, value)
            return start_response(self.status, self.headers, exc_info)
        parts = self.url.split('?')
        environ['PATH_INFO'] = parts[0]
        if len(parts) > 1:
            environ['QUERY_STRING'] = parts[1]
        else:
            environ['QUERY_STRING'] = ''
        #raise Exception(self.url, self.status)
        try:
            return self.app(environ, keep_status_start_response)
        except RecursionLoop, e:
            environ['wsgi.errors'].write('Recursion error getting error page: %s\n' % e)
            keep_status_start_response('500 Server Error', [('Content-type', 'text/plain')], sys.exc_info())
            return ['Error: %s.  (Error page could not be fetched)'
                    % self.status]


class StatusBasedForward(object):
    """
    Middleware that lets you test a response against a custom mapper object to
    programatically determine whether to internally forward to another URL and
    if so, which URL to forward to.

    If you don't need the full power of this middleware you might choose to use
    the simpler ``forward`` middleware instead.

    The arguments are:

    ``app``
        The WSGI application or middleware chain.

    ``mapper``
        A callable that takes a status code as the
        first parameter, a message as the second, and accepts optional environ,
        global_conf and named argments afterwards. It should return a
        URL to forward to or ``None`` if the code is not to be intercepted.

    ``global_conf``
        Optional default configuration from your config file. If ``debug`` is
        set to ``true`` a message will be written to ``wsgi.errors`` on each
        internal forward stating the URL forwarded to.

    ``**params``
        Optional, any other configuration and extra arguments you wish to
        pass which will in turn be passed back to the custom mapper object.

    Here is an example where a ``404 File Not Found`` status response would be
    redirected to the URL ``/error?code=404&message=File%20Not%20Found``. This
    could be useful for passing the status code and message into another
    application to display an error document:

    .. code-block:: python

        from paste.errordocument import StatusBasedForward
        from paste.recursive import RecursiveMiddleware
        from urllib import urlencode

        def error_mapper(code, message, environ, global_conf, kw)
            if code in [404, 500]:
                params = urlencode({'message':message, 'code':code})
                url = '/error?'%(params)
                return url
            else:
                return None

        app = RecursiveMiddleware(
            StatusBasedForward(app, mapper=error_mapper),
        )

    """

    def __init__(self, app, mapper, global_conf=None, **params):
        if global_conf is None:
            global_conf = {}
        # @@: global_conf shouldn't really come in here, only in a
        # separate make_status_based_forward function
        if global_conf:
            self.debug = converters.asbool(global_conf.get('debug', False))
        else:
            self.debug = False
        self.application = app
        self.mapper = mapper
        self.global_conf = global_conf
        self.params = params

    def __call__(self, environ, start_response):
        url = []
        writer = []

        def change_response(status, headers, exc_info=None):
            status_code = status.split(' ')
            try:
                code = int(status_code[0])
            except (ValueError, TypeError):
                raise Exception(
                    'StatusBasedForward middleware '
                    'received an invalid status code %s'%repr(status_code[0])
                )
            message = ' '.join(status_code[1:])
            new_url = self.mapper(
                code,
                message,
                environ,
                self.global_conf,
                **self.params
            )
            if not (new_url == None or isinstance(new_url, str)):
                raise TypeError(
                    'Expected the url to internally '
                    'redirect to in the StatusBasedForward mapper'
                    'to be a string or None, not %r' % new_url)
            if new_url:
                url.append([new_url, status, headers])
                # We have to allow the app to write stuff, even though
                # we'll ignore it:
                return [].append
            else:
                return start_response(status, headers, exc_info)

        app_iter = self.application(environ, change_response)
        if url:
            if hasattr(app_iter, 'close'):
                app_iter.close()

            def factory(app):
                return StatusKeeper(app, status=url[0][1], url=url[0][0],
                                    headers=url[0][2])
            raise ForwardRequestException(factory=factory)
        else:
            return app_iter

def make_errordocument(app, global_conf, **kw):
    """
    Paste Deploy entry point to create a error document wrapper.

    Use like::

        [filter-app:main]
        use = egg:Paste#errordocument
        next = real-app
        500 = /lib/msg/500.html
        404 = /lib/msg/404.html
    """
    map = {}
    for status, redir_loc in kw.items():
        try:
            status = int(status)
        except ValueError:
            raise ValueError('Bad status code: %r' % status)
        map[status] = redir_loc
    forwarder = forward(app, map)
    return forwarder

__pudge_all__ = [
    'forward',
    'make_errordocument',
    'empty_error',
    'make_empty_error',
    'StatusBasedForward',
]


###############################################################################
## Deprecated
###############################################################################

def custom_forward(app, mapper, global_conf=None, **kw):
    """
    Deprectated; use StatusBasedForward instead.
    """
    warnings.warn(
        "errordocuments.custom_forward has been deprecated; please "
        "use errordocuments.StatusBasedForward",
        DeprecationWarning, 2)
    if global_conf is None:
        global_conf = {}
    return _StatusBasedRedirect(app, mapper, global_conf, **kw)

class _StatusBasedRedirect(object):
    """
    Deprectated; use StatusBasedForward instead.
    """
    def __init__(self, app, mapper, global_conf=None, **kw):

        warnings.warn(
            "errordocuments._StatusBasedRedirect has been deprecated; please "
            "use errordocuments.StatusBasedForward",
            DeprecationWarning, 2)

        if global_conf is None:
            global_conf = {}
        self.application = app
        self.mapper = mapper
        self.global_conf = global_conf
        self.kw = kw
        self.fallback_template = """
            <html>
            <head>
            <title>Error %(code)s</title>
            </html>
            <body>
            <h1>Error %(code)s</h1>
            <p>%(message)s</p>
            <hr>
            <p>
                Additionally an error occurred trying to produce an
                error document.  A description of the error was logged
                to <tt>wsgi.errors</tt>.
            </p>
            </body>
            </html>
        """

    def __call__(self, environ, start_response):
        url = []
        code_message = []
        try:
            def change_response(status, headers, exc_info=None):
                new_url = None
                parts = status.split(' ')
                try:
                    code = int(parts[0])
                except (ValueError, TypeError):
                    raise Exception(
                        '_StatusBasedRedirect middleware '
                        'received an invalid status code %s'%repr(parts[0])
                    )
                message = ' '.join(parts[1:])
                new_url = self.mapper(
                    code,
                    message,
                    environ,
                    self.global_conf,
                    self.kw
                )
                if not (new_url == None or isinstance(new_url, str)):
                    raise TypeError(
                        'Expected the url to internally '
                        'redirect to in the _StatusBasedRedirect error_mapper'
                        'to be a string or None, not %s'%repr(new_url)
                    )
                if new_url:
                    url.append(new_url)
                code_message.append([code, message])
                return start_response(status, headers, exc_info)
            app_iter = self.application(environ, change_response)
        except:
            try:
                import sys
                error = str(sys.exc_info()[1])
            except:
                error = ''
            try:
                code, message = code_message[0]
            except:
                code, message = ['', '']
            environ['wsgi.errors'].write(
                'Error occurred in _StatusBasedRedirect '
                'intercepting the response: '+str(error)
            )
            return [self.fallback_template
                    % {'message': message, 'code': code}]
        else:
            if url:
                url_ = url[0]
                new_environ = {}
                for k, v in environ.items():
                    if k != 'QUERY_STRING':
                        new_environ['QUERY_STRING'] = urlparse(url_)[4]
                    else:
                        new_environ[k] = v
                class InvalidForward(Exception):
                    pass
                def eat_start_response(status, headers, exc_info=None):
                    """
                    We don't want start_response to do anything since it
                    has already been called
                    """
                    if status[:3] != '200':
                        raise InvalidForward(
                            "The URL %s to internally forward "
                            "to in order to create an error document did not "
                            "return a '200' status code." % url_
                        )
                forward = environ['paste.recursive.forward']
                old_start_response = forward.start_response
                forward.start_response = eat_start_response
                try:
                    app_iter = forward(url_, new_environ)
                except InvalidForward, e:
                    code, message = code_message[0]
                    environ['wsgi.errors'].write(
                        'Error occurred in '
                        '_StatusBasedRedirect redirecting '
                        'to new URL: '+str(url[0])
                    )
                    return [
                        self.fallback_template%{
                            'message':message,
                            'code':code,
                        }
                    ]
                else:
                    forward.start_response = old_start_response
                    return app_iter
            else:
                return app_iter
