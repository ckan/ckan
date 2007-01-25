from ckan.lib.base import *

class HomeController(BaseController):
    def index(self):
        return render_response('home')
