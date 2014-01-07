import cgi

from paste.urlparser import PkgResourcesParser
from pylons import request, tmpl_context as c
from pylons.controllers.util import forward
from webhelpers.html.builder import literal

from ckan.lib.base import BaseController
from ckan.lib.base import render


class ErrorController(BaseController):
    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.

    """

    def document(self):
        """Render the error document"""
        original_request = request.environ.get('pylons.original_request')
        original_response = request.environ.get('pylons.original_response')
        # When a request (e.g. from a web-bot) is direct, not a redirect
        # from a page. #1176
        if not original_response:
            return 'There is no error.'
        # Bypass error template for API operations.
        if original_request and original_request.path.startswith('/api'):
            return original_response.body
        # Otherwise, decorate original response with error template.
        c.content = literal(original_response.unicode_body) or \
            cgi.escape(request.GET.get('message', ''))
        c.prefix = request.environ.get('SCRIPT_NAME', ''),
        c.code = cgi.escape(request.GET.get('code',
                            str(original_response.status_int))),
        return render('error_document_template.html')

    def img(self, id):
        """Serve Pylons' stock images"""
        return self._serve_file('/'.join(['media/img', id]))

    def style(self, id):
        """Serve Pylons' stock stylesheets"""
        return self._serve_file('/'.join(['media/style', id]))

    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        request.environ['PATH_INFO'] = '/%s' % path
        return forward(PkgResourcesParser('pylons', 'pylons'))
