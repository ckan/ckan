from ckan.lib.base import *

class PackageController(BaseController):

    def index(self):
        c.package_count = model.Package.select().count()
        return render_response('package/index')

    def read(self, id):
        try:
            c.pkg = model.Package.byName(id)
        except:
            abort(404)
        return render_response('package/read')

    def list(self):
        packages = list(model.Package.select())
        c.package_count = len(packages)
        c.packages = packages
        return render_response('package/list')
