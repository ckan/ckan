from ckan.lib.base import *
from genshi.template.loader import TemplateNotFound


class TemplateController(BaseController):

    def view(self, url):
        """By default, the final controller tried to fulfill the request
        when no other routes match. It may be used to display a template
        when all else fails, e.g.::

            def view(self, url):
                return render('/%s' % url)

        Or if you're using Mako and want to explicitly send a 404 (Not
        Found) response code when the requested template doesn't exist::

            import mako.exceptions

            def view(self, url):
                try:
                    return render('/%s' % url)
                except mako.exceptions.TopLevelLookupException:
                    abort(404)

        By default this controller aborts the request with a 404 (Not
        Found)
        """
        try:
            return render(url)
        except TemplateNotFound:
            if url.endswith('.html'):
                abort(404)
            url += '.html'
            try:
                return render(url)
            except TemplateNotFound:
                abort(404)
