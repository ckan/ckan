from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class HomeController(CkanBaseController):
    def index(self):
        return render('home')
