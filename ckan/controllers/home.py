from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class HomeController(CkanBaseController):
    repo = model.repo

    def index(self):
        c.package_count = model.Package.query.count()
        return render('home')
