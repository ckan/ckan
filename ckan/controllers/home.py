from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class HomeController(CkanBaseController):
    repo = model.repo

    def index(self):
        rev = self.repo.youngest_revision()
        c.package_count = len(rev.model.packages)
        return render('home')
