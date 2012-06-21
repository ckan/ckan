import ckan.lib.base as base

class DevelopmentController(base.BaseController):
    ''' Controller for front end development pages '''

    def primer(self):
        ''' Render all html components out onto a single page '''
        return base.render('development/primer.html')

    def markup(self):
        ''' Render all html elements out onto a single page '''
        return base.render('development/markup.html')
