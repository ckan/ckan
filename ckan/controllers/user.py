from ckan.lib.base import *
from ckan.controllers.base import CkanBaseController

def login_form():
    return render('user/login_form').replace('FORM_ACTION', '%s')

class UserController(CkanBaseController):

    def index(self, id):
        if not c.user or c.user != id:
            h.redirect_to(controller='user', action='login', id=None)
        return self.read()

    def read(self, id):
        if id:            
            user = model.User.query.get(id)
        else:
            user = model.User.by_name(c.user)
        if not user:
            h.redirect_to(controller='user', action='login', id=None)
        c.read_user = user.name
        c.is_myself = user.name == c.user
        revisions_q = model.Revision.query.filter_by(author=user.name)
        c.num_edits = revisions_q.count()
        c.num_pkg_admin = model.PackageRole.query.filter_by(user=user, role=model.Role.ADMIN).count()
        c.activity = revisions_q.limit(20).all()
        return render('user/read')

    def login(self):
        if c.user:
            userobj = model.User.by_name(c.user)
            if userobj is None:
                userobj = model.User(name=c.user)
                model.Session.commit()
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
            user = model.User.by_name(c.user)
            c.api_key = user.apikey
        return render('user/apikey')

