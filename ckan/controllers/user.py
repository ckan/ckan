from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

def login_form():
    return render('user/login_form').replace('FORM_ACTION', '%s')

class UserController(CkanBaseController):

    def index(self):
        if not c.user:
            h.redirect_to(controller='user', action='login', id=None)
        else:
            q = model.Revision.query.filter_by(author=c.user).limit(20)
            c.activity = q.limit(20).all()            
            return render('user/index')

#     def login_form(self, return_url=''):
#         return render('user/login_form')
# 
#     def openid_form(self, return_url=''):
#         return render('user/openid_form').replace('DOLAR', '$')
# 
    def login(self):
        if c.user:
            h.redirect_to(controller='user', action=None, id=None)
        else:
            form = render('user/openid_form')
            # /login_openid page need not exist -- request gets intercepted by openid plugin
            form = form.replace('FORM_ACTION', '/login_openid')
            return form

    def logout(self):
        c.user = None
        return render('user/logout')

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
        return render('user/apikey')

