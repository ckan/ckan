from ckan.lib.base import *

class HomeController(BaseController):
    repo = model.repo

    def index(self):
        c.package_count = model.Session.query(model.Package).count()
        c.revisions = model.Session.query(model.Revision).limit(10).all()
        return render('home')

    def license(self):
        return render('license')
    
    def guide(self):
        ckan_pkg = model.Package.by_name(u'ckan')
        if ckan_pkg:
            c.info = ckan_pkg.notes
        else:
            c.info = ''
        return render('guide')

    def about(self):
        return render('about')

