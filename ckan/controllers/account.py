from ckan.lib.base import *

class AccountController(BaseController):
    def index(self):
        c.login_page = h.url_for(controller='account', action='login')
        return render_response('account/index')

    def login(self, return_url=''):
        if request.environ.has_key('REMOTE_USER'):
            c.user = request.environ['REMOTE_USER']
            return render_response('account/logged_in')
        else:
            abort(401)

    def logout(self):
        return render_response('account/logout')

