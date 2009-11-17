import cgi
import os.path

import paste.fileapp
from pylons.middleware import error_document_template, media_path

from ckan.lib.base import *

class ErrorController(BaseController):
    """Generates error documents as and when they are required.

    The ErrorDocuments middleware forwards to ErrorController when error
    related status codes are returned from the application.

    This behaviour can be altered by changing the parameters to the
    ErrorDocuments middleware in your config/middleware.py file.
    """

    def document(self):
        """Render the error document"""
        ckan_template = render("error_document_template")
        ckan_template = ckan_template.decode('utf8')
        response = request.environ.get('pylons.original_response')
        page = ckan_template % \
            dict(prefix=request.environ.get('SCRIPT_NAME', ''),
                 code=cgi.escape(request.GET.get('code', str(response.status_int))),
                 message=h.literal(response.body) or cgi.escape(request.GET.get('message', '')))
        return page

    def img(self, id):
        """Serve Pylons' stock images"""
        return self._serve_file(os.path.join(media_path, 'img', id))

    def style(self, id):
        """Serve Pylons' stock stylesheets"""
        return self._serve_file(os.path.join(media_path, 'style', id))

    def _serve_file(self, path):
        """Call Paste's FileApp (a WSGI application) to serve the file
        at the specified path
        """
        fapp = paste.fileapp.FileApp(path)
        return fapp(request.environ, self.start_response)
