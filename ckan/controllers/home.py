from ckan.lib.base import *

class HomeController(BaseController):
    repo = model.repo

    def index(self):
        c.package_count = model.Package.query.count()
        c.revisions = model.Revision.query.limit(10).all()
        return render('home/index')

    def license(self):
        return render('home/license')
    
    def guide(self):
        ckan_pkg = model.Package.by_name(u'ckan')
        if ckan_pkg:
            c.info = ckan_pkg.notes
        else:
            c.info = ''
        return render('home/guide')

    def about(self):
        return render('home/about')

