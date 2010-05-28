import genshi

import ckan.misc
from ckan.lib.base import *

def login_form():
    return render('user/login_form').replace('FORM_ACTION', '%s')

class UserController(BaseController):

    def index(self, id):
        if not c.user or c.user != id:
            h.redirect_to(controller='user', action='login', id=None)
        return self.read()

    def read(self, id):
        if id:
            user = model.Session.query(model.User).get(id)
        else:
            user = model.User.by_name(c.user)
        if not user:
            h.redirect_to(controller='user', action='login', id=None)
        c.read_user = user.name
        c.is_myself = user.name == c.user
        c.about_formatted = self._format_about(user.about)
        revisions_q = model.Session.query(model.Revision).filter_by(author=user.name)
        c.num_edits = revisions_q.count()
        c.num_pkg_admin = model.Session.query(model.PackageRole).filter_by(user=user, role=model.Role.ADMIN).count()
        c.activity = revisions_q.limit(20).all()
        return render('user/read')

    def login(self):
        if c.user:
            userobj = model.User.by_name(c.user)
            if userobj is None:
                userobj = model.User(name=c.user)
                model.Session.add(userobj)
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

    def edit(self):
        # logged in
        if not c.user:
            abort(401)
        user = model.User.by_name(c.user)
        if not 'commit' in request.params and not 'preview' in request.params:
            c.user_about = user.about
        elif 'preview' in request.params:
            about = request.params.getone('about')
            c.preview = self._format_about(about)
            c.user_about = about
        elif 'commit' in request.params:
            about = request.params.getone('about')
            try:
                rev = model.repo.new_revision()
                rev.author = c.author
                rev.message = _(u'Changed user details')
                user.about = about
            except Exception, inst:
                model.Session.rollback()
                raise
            else:
                model.Session.commit()
            h.redirect_to(controller='user', action='read', id=user.id)
            
        return render('user/edit')
        
    def _format_about(self, about):
        about_formatted = ckan.misc.MarkdownFormat().to_html(about)
        return genshi.HTML(about_formatted)        

