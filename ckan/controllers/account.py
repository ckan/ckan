from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

def login_form():
    return render('account/login_form').replace('FORM_ACTION', '%s')

class AccountController(CkanBaseController):

    def index(self):
        c.login_page = h.url_for(controller='account', action='login')
        return render('account/index')

#     def login_form(self, return_url=''):
#         return render('account/login_form')
# 
#     def openid_form(self, return_url=''):
#         return render('account/openid_form').replace('DOLAR', '$')
# 
    def login(self):
        if c.user:
             return render('account/logged_in')
        else:
            form = render('account/openid_form')
            # /login_openid page need not exist -- request gets intercepted by openid plugin
            form = form.replace('FORM_ACTION', '/login_openid')
            return form

    def logout(self):
        c.user = None
        return render('account/logout')

    def apikey(self):
        # logged in
        if not c.user:
            abort(401)
        else:
            username = c.author
            apikey_object = model.ApiKey.by_name(username)
            if apikey_object is None:
                apikey_object = model.ApiKey(name=username)
                model.Session.commit()
            c.api_key = apikey_object.key
        return render('account/apikey')

