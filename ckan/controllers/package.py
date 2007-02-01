from ckan.lib.base import *

class PackageController(BaseController):

    def index(self):
        c.package_count = 0
        return render_response('package/index')

    def list(self):
        packages = list(model.Package.select())
        c.package_count = len(packages)
        c.packages = packages
        return render_response('package/list')
