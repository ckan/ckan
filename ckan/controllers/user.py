import logging

import genshi
from sqlalchemy import or_, func, desc
from urllib import quote

import ckan.misc
from ckan.lib.base import *
from ckan.lib import mailer

log = logging.getLogger(__name__)

def login_form():
    return render('user/login_form.html').replace('FORM_ACTION', '%s')

class UserController(BaseController):

    def index(self, id=None):
        LIMIT = 20

        if not self.authorizer.am_authorized(c, model.Action.USER_READ, model.System):
            abort(401, _('Not authorized to see this page'))

        page = int(request.params.get('page', 1))
        c.q  = request.params.get('q', '')
        c.order_by = request.params.get('order_by', 'name')

        query = model.Session.query(model.User, func.count(model.User.id))
        if c.q:
            query = model.User.search(c.q, query)

        if c.order_by == 'edits':
            query = query.join((model.Revision, or_(
                    model.Revision.author==model.User.name,
                    model.Revision.author==model.User.openid
                    )))
            query = query.group_by(model.User)
            query = query.order_by(desc(func.count(model.User.id)))
        else:
            query = query.group_by(model.User)
            query = query.order_by(model.User.name)

        c.page = h.Page(
            collection=query,
            page=page,
            item_count=query.count(),
            items_per_page=LIMIT
            )
        return render('user/list.html')

    def read(self, id=None):
        if not self.authorizer.am_authorized(c, model.Action.USER_READ, model.System):
            abort(401, _('Not authorized to see this page'))
        if id:
            user = model.User.get(id)
        else:
            user = c.userobj
        if not user:
            h.redirect_to(controller='user', action='login', id=None)
        c.read_user = user.display_name
        c.is_myself = user.name == c.user
        c.api_key = user.apikey
        c.about_formatted = self._format_about(user.about)
        revisions_q = model.Session.query(model.Revision
                ).filter_by(author=user.name)
        c.num_edits = user.number_of_edits()
        c.num_pkg_admin = user.number_administered_packages()
        c.activity = revisions_q.limit(20).all()
        return render('user/read.html')
    
    def me(self):
        if not c.user:
            h.redirect_to(controller='user', action='login', id=None)
        user_ref = c.userobj.get_reference_preferred_for_uri()
        h.redirect_to(controller='user', action='read', id=user_ref)

    def register(self):
        if not self.authorizer.am_authorized(c, model.Action.USER_CREATE, model.System):
            abort(401, _('Not authorized to see this page'))
        if request.method == 'POST':
            try:
                c.login = request.params.getone('login')
                c.fullname = request.params.getone('fullname')
                c.email = request.params.getone('email')
            except KeyError, e:
                abort(401, _('Missing parameter: %r') % e)
            if not c.login:
                h.flash_error(_("Please enter a login name."))
                return render("user/register.html")
            if not model.User.check_name_valid(c.login):
                h.flash_error(_('That login name is not valid. It must be at least 3 characters, restricted to alphanumerics and these symbols: %s') % '_\-')
                return render("user/register.html")
            if not model.User.check_name_available(c.login):
                h.flash_error(_("That login name is not available."))
                return render("user/register.html")
            if not request.params.getone('password1'):
                h.flash_error(_("Please enter a password."))
                return render("user/register.html")                
            try:
                password = self._get_form_password()
            except ValueError, ve:
                h.flash_error(ve)
                return render('user/register.html')
            user = model.User(name=c.login, fullname=c.fullname,
                              email=c.email, password=password)
            model.Session.add(user)
            model.Session.commit() 
            model.Session.remove()
            h.redirect_to('/login_generic?login=%s&password=%s' % (str(c.login), quote(password.encode('utf-8'))))

        return render('user/register.html')

    def login(self):
        if 'error' in request.params:
            h.flash_error(request.params['error'])
        return render('user/login.html')
    
    def logged_in(self):
        if c.userobj:
            response.set_cookie("ckan_user", c.userobj.name)
            response.set_cookie("ckan_display_name", c.userobj.display_name)
            response.set_cookie("ckan_apikey", c.userobj.apikey)
            h.flash_success(_("Welcome back, %s") % c.userobj.display_name)
            h.redirect_to(controller='user', action='me', id=None)
        else:
            h.flash_error('Login failed. Bad username or password.')
            h.redirect_to(controller='user', action='login')
          
    def logged_out(self):
        c.user = None
        response.delete_cookie("ckan_user")
        response.delete_cookie("ckan_display_name")
        response.delete_cookie("ckan_apikey")
        return render('user/logout.html')

    def edit(self, id=None):
        if id is not None:
            user = model.User.get(id)
        else:
            user = c.userobj
        if user is None:
            abort(404)
        currentuser = c.userobj
        if not (ckan.authz.Authorizer().is_sysadmin(unicode(c.user)) or user == currentuser):
            abort(401)
        c.userobj = user
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
                about = request.params.getone('about')
                if 'http://' in about or 'https://' in about:
                    msg = _('Edit not allowed as it looks like spam. Please avoid links in your description.')
                    h.flash_error(msg)
                    c.user_about = about
                    c.user_fullname = request.params.getone('fullname')
                    c.user_email = request.params.getone('email')
                    return render('user/edit.html')
                user.about = about
                user.fullname = request.params.getone('fullname')
                user.email = request.params.getone('email')
                try:
                    password = self._get_form_password()
                    if password: 
                        user.password = password
                except ValueError, ve:
                    h.flash_error(ve)
                    return render('user/edit.html')
            except Exception, inst:
                model.Session.rollback()
                raise
            else:
                model.Session.commit()
                h.flash_notice(_("Your account has been updated."))
            response.set_cookie("ckan_display_name", user.display_name)
            h.redirect_to(controller='user', action='read', id=user.id)
            
        return render('user/edit.html')
    
    def request_reset(self):
        if request.method == 'POST':
            id = request.params.get('user')
            user = model.User.get(id)
            if user is None and id and len(id)>2:
                q = model.User.search(id)
                if q.count() == 1:
                    user = q.one()
                elif q.count() > 1:
                    users = ' '.join([user.name for user in q])
                    h.flash_error(_('"%s" matched several users') % (id))
                    return render("user/request_reset.html")
            if user is None:
                h.flash_error(_('No such user: %s') % id)
                return render("user/request_reset.html")
            try:
                mailer.send_reset_link(user)
                h.flash_success(_('Please check your inbox for a reset code.'))
                redirect('/')
            except mailer.MailerException, e:
                h.flash_error(_('Could not send reset link: %s') % unicode(e))
        return render('user/request_reset.html')

    def perform_reset(self, id):
        user = model.User.get(id)
        if user is None:
            abort(404)
        c.reset_key = request.params.get('key')
        if not mailer.verify_reset_link(user, c.reset_key):
            msg = _('Invalid reset key. Please try again.')
            h.flash_error(msg)
            abort(403, msg.encode('utf8'))
        if request.method == 'POST':
            try:
                user.password = self._get_form_password()
                model.Session.add(user)
                model.Session.commit()
                h.flash_success(_("Your password has been reset."))
                redirect('/')
            except ValueError, ve:
                h.flash_error(unicode(ve))
        return render('user/perform_reset.html')

    def _format_about(self, about):
        about_formatted = ckan.misc.MarkdownFormat().to_html(about)
        try:
            html = genshi.HTML(about_formatted)
        except genshi.ParseError, e:
            log.error('Could not print "about" field Field: %r Error: %r', about, e)
            html = 'Error: Could not parse About text'
        return html
    
    def _get_form_password(self):
        password1 = request.params.getone('password1')
        password2 = request.params.getone('password2')
        if (password1 is not None and password1 != ''):
            if not len(password1) >= 4:
                raise ValueError(_("Your password must be 4 characters or longer."))
            elif not password1 == password2:
                raise ValueError(_("The passwords you entered do not match."))
            return password1
        
