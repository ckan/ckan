from ckan.lib.base import *

class PackageController(BaseController):

    def index(self):
        c.package_count = 0
        return render_response('package/index')
