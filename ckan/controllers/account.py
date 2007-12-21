from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

class AccountController(CkanBaseController):
    def index(self):
        c.login_page = h.url_for(controller='account', action='login')
        return render('account/index')

    def login(self, return_url=''):
        if request.environ.has_key('REMOTE_USER'):
            c.user = request.environ['REMOTE_USER']
            return render('account/logged_in')
        else:
            abort(401)

    def logout(self):
        return render('account/logout')

