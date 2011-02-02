import genshi

import ckan.misc
from ckan.lib.base import *

def login_form():
    return render('user/login_form.html').replace('FORM_ACTION', '%s')

class UserController(BaseController):

    def index(self, id=None):
        if not c.user:
            h.redirect_to(controller='user', action='login', id=None)
        return self.read()

    def read(self, id=None):
        if id:
            user = model.User.get(id)
        else:
            user = model.User.by_name(c.user)
        if not user:
            h.redirect_to(controller='user', action='login', id=None)
        c.read_user = user.display_name
        c.is_myself = user.name == c.user
        c.about_formatted = self._format_about(user.about)
        revisions_q = model.Session.query(model.Revision).filter_by(author=user.name)
        c.num_edits = revisions_q.count()
        c.num_pkg_admin = model.Session.query(model.PackageRole).filter_by(user=user, role=model.Role.ADMIN).count()
        c.activity = revisions_q.limit(20).all()
        return render('user/read.html')
    
    def login(self):
        form = render('user/openid_form.html')
        # /login_openid page need not exist -- request gets intercepted by openid plugin
        form = form.replace('FORM_ACTION', '/login_openid')
        return form
    
    def openid(self):
        if c.user:
            print c.user
            userobj = model.User.by_name(c.user)
            response.set_cookie("ckan_user", userobj.name)
            response.set_cookie("ckan_display_name", userobj.display_name)
            response.set_cookie("ckan_apikey", userobj.apikey)
            h.redirect_to(controller='user', action=None, id=None)
        else:
            self.login()
          
    def logout(self):
        c.user = None
        response.delete_cookie("ckan_user")
        response.delete_cookie("ckan_display_name")
        response.delete_cookie("ckan_apikey")
        return render('user/logout.html')

    def apikey(self):
        # logged in
        if not c.user:
            abort(401)
        else:
            user = model.User.by_name(c.user)
            c.api_key = user.apikey
        return render('user/apikey.html')

    def edit(self):
        # logged in
        if not c.user:
            abort(401)
        user = model.User.by_name(c.user)
        if not 'save' in request.params and not 'preview' in request.params:
            c.user_about = user.about
            c.user_fullname = user.fullname
            c.user_email = user.email
        elif 'preview' in request.params:
            about = request.params.getone('about')
            c.preview = self._format_about(about)
            c.user_about = about
            c.user_fullname = request.params.getone('fullname')
            c.user_email = request.params.getone('email')
        elif 'save' in request.params:
            try:
                rev = model.repo.new_revision()
                rev.author = c.author
                rev.message = _(u'Changed user details')
                user.about = request.params.getone('about')
                user.fullname = request.params.getone('fullname')
                user.email = request.params.getone('email')
                password1 = request.params.getone('password1')
                password2 = request.params.getone('password2')
                if password1:
                    if not len(password1) >= 4:
                        h.flash_error(_("Your password must be 4 characters or longer."))
                        return render('user/edit.html')
                    elif not password1 == password2:
                        h.flash_error(_("The passwords you entered do not match."))
                        return render('user/edit.html')
                    else:
                        user.password = password1
            except Exception, inst:
                model.Session.rollback()
                raise
            else:
                model.Session.commit()
                h.flash_notice(_("Your account has been updated."))
            response.set_cookie("ckan_display_name", user.display_name)
            h.redirect_to(controller='user', action='read', id=user.id)
            
        return render('user/edit.html')
        
    def _format_about(self, about):
        about_formatted = ckan.misc.MarkdownFormat().to_html(about)
        return genshi.HTML(about_formatted)        

