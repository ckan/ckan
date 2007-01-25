from ckan.lib.base import *

class TemplateController(BaseController):
    def view(self, url):
        """
        This is the last place which is tried during a request to try to find a 
        file to serve. It could be used for example to display a template::
        
            def view(self, url):
                return render_response(url)
        
        Or, if you're using Myghty and would like to catch the component not
        found error which will occur when the template doesn't exist; you
        can use the following version which will provide a 404 if the template
        doesn't exist::
        
            import myghty.exception
            
            def view(self, url):
                try:
                    return render_response('/'+url)
                except myghty.exception.ComponentNotFound:
                    return Response(code=404)
        
        The default is just to abort the request with a 404 File not found
        status message.
        """
        abort(404)
