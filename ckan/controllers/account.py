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

    def apikey(self):
        import sqlobject 
        # logged in
        if c.user:
            try:
                c.api_key = model.ApiKey.byName(c.user).key
            except sqlobject.SQLObjectNotFound:
                import uuid
                key = str(uuid.uuid4())
                model.ApiKey(name=c.user, key=key)
                c.api_key = key
        else:
            c.error = 'You need to be logged in to access your API key.'
        return render('account/apikey')

