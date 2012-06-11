import ckan.lib.base as base

class UtilController(base.BaseController):
    ''' Controller for functionality that has no real home'''

    def redirect(self):
        ''' redirect to the url parameter. '''
        url = base.request.params.get('url')
        return base.redirect(url)
