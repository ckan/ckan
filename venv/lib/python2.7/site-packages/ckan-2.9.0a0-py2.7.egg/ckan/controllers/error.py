# encoding: utf-8

import cgi

from paste.urlparser import PkgResourcesParser
from pylons import request
from pylons.controllers.util import forward
from webhelpers.html.builder import literal

from ckan.common import c
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
        if (original_request and
                (original_request.path.startswith('/api') or
                 original_request.path.startswith('/fanstatic'))):
            return original_response.body
        # If the charset has been lost on the middleware stack, use the
        # default one (utf-8)
        if not original_response.charset and original_response.default_charset:
            original_response.charset = original_response.default_charset
        # Otherwise, decorate original response with error template.
        content = literal(original_response.unicode_body) or \
            cgi.escape(request.GET.get('message', ''))
        prefix = request.environ.get('SCRIPT_NAME', ''),
        code = cgi.escape(request.GET.get('code',
                          str(original_response.status_int))),
        extra_vars = {'code': code, 'content': content, 'prefix': prefix}
        return render('error_document_template.html', extra_vars=extra_vars)

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
