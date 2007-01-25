import os.path
from paste import fileapp
from pylons.middleware import media_path, error_document_template
from pylons.util import get_prefix
from ckan.lib.base import *

class ErrorController(BaseController):
    """
    Class to generate error documents as and when they are required. This behaviour of this
    class can be altered by changing the parameters to the ErrorDocuments middleware in 
    your config/middleware.py file.
    """

    def document(self):
        """
        Change this method to change how error documents are displayed
        """
        page = error_document_template % {
            'prefix': get_prefix(request.environ),
            'code': request.params.get('code', ''),
            'message': request.params.get('message', ''),
        }
        return Response(page)

    def img(self, id):
        return self._serve_file(os.path.join(media_path, 'img', id))
        
    def style(self, id):
        return self._serve_file(os.path.join(media_path, 'style', id))

    def _serve_file(self, path):
        fapp = fileapp.FileApp(path)
        return fapp(request.environ, self.start_response)
