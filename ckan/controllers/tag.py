from ckan.lib.base import *

class TagController(BaseController):

    def index(self):
        return render_response('tag/index')
