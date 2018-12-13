# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Middleware that displays everything that is printed inline in
application pages.

Anything printed during the request will get captured and included on
the page.  It will usually be included as a floating element in the
top right hand corner of the page.  If you want to override this
you can include a tag in your template where it will be placed::

  <pre id="paste-debug-prints"></pre>

You might want to include ``style="white-space: normal"``, as all the
whitespace will be quoted, and this allows the text to wrap if
necessary.

"""

from cStringIO import StringIO
import re
import cgi
from paste.util import threadedprint
from paste import wsgilib
from paste import response
import sys

_threadedprint_installed = False

__all__ = ['PrintDebugMiddleware']

class TeeFile(object):

    def __init__(self, files):
        self.files = files

    def write(self, v):
        if isinstance(v, unicode):
            # WSGI is picky in this case
            v = str(v)
        for file in self.files:
            file.write(v)

class PrintDebugMiddleware(object):

    """
    This middleware captures all the printed statements, and inlines
    them in HTML pages, so that you can see all the (debug-intended)
    print statements in the page itself.

    There are two keys added to the environment to control this:
    ``environ['paste.printdebug_listeners']`` is a list of functions
    that will be called everytime something is printed.

    ``environ['paste.remove_printdebug']`` is a function that, if
    called, will disable printing of output for that request.

    If you have ``replace_stdout=True`` then stdout is replaced, not
    captured.
    """

    log_template = (
        '<pre style="width: 40%%; border: 2px solid #000; white-space: normal; '
        'background-color: #ffd; color: #000; float: right;">'
        '<b style="border-bottom: 1px solid #000">Log messages</b><br>'
        '%s</pre>')

    def __init__(self, app, global_conf=None, force_content_type=False,
                 print_wsgi_errors=True, replace_stdout=False):
        # @@: global_conf should be handled separately and only for
        # the entry point
        self.app = app
        self.force_content_type = force_content_type
        if isinstance(print_wsgi_errors, basestring):
            from paste.deploy.converters import asbool
            print_wsgi_errors = asbool(print_wsgi_errors)
        self.print_wsgi_errors = print_wsgi_errors
        self.replace_stdout = replace_stdout
        self._threaded_print_stdout = None

    def __call__(self, environ, start_response):
        global _threadedprint_installed
        if environ.get('paste.testing'):
            # In a testing environment this interception isn't
            # useful:
            return self.app(environ, start_response)
        if (not _threadedprint_installed
            or self._threaded_print_stdout is not sys.stdout):
            # @@: Not strictly threadsafe
            _threadedprint_installed = True
            threadedprint.install(leave_stdout=not self.replace_stdout)
            self._threaded_print_stdout = sys.stdout
        removed = []
        def remove_printdebug():
            removed.append(None)
        environ['paste.remove_printdebug'] = remove_printdebug
        logged = StringIO()
        listeners = [logged]
        environ['paste.printdebug_listeners'] = listeners
        if self.print_wsgi_errors:
            listeners.append(environ['wsgi.errors'])
        replacement_stdout = TeeFile(listeners)
        threadedprint.register(replacement_stdout)
        try:
            status, headers, body = wsgilib.intercept_output(
                environ, self.app)
            if status is None:
                # Some error occurred
                status = '500 Server Error'
                headers = [('Content-type', 'text/html')]
                start_response(status, headers)
                if not body:
                    body = 'An error occurred'
            content_type = response.header_value(headers, 'content-type')
            if (removed or
                (not self.force_content_type and
                 (not content_type
                  or not content_type.startswith('text/html')))):
                if replacement_stdout == logged:
                    # Then the prints will be lost, unless...
                    environ['wsgi.errors'].write(logged.getvalue())
                start_response(status, headers)
                return [body]
            response.remove_header(headers, 'content-length')
            body = self.add_log(body, logged.getvalue())
            start_response(status, headers)
            return [body]
        finally:
            threadedprint.deregister()

    _body_re = re.compile(r'<body[^>]*>', re.I)
    _explicit_re = re.compile(r'<pre\s*[^>]*id="paste-debug-prints".*?>',
                              re.I+re.S)
    
    def add_log(self, html, log):
        if not log:
            return html
        text = cgi.escape(log)
        text = text.replace('\n', '<br>')
        text = text.replace('  ', '&nbsp; ')
        match = self._explicit_re.search(html)
        if not match:
            text = self.log_template % text
            match = self._body_re.search(html)
        if not match:
            return text + html
        else:
            return html[:match.end()] + text + html[match.end():]
