import logging

import genshi
from urllib import quote

import ckan.misc
from ckan.lib.base import *
from ckan.lib import mailer
from ckan.authz import Authorizer
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.logic.schema import user_form_schema

import ckan.logic.action.get as get
import ckan.logic.action.create as create

log = logging.getLogger(__name__)

def login_form():
    return render('user/login_form.html').replace('FORM_ACTION', '%s')

class UserController(BaseController):

    ## hooks for subclasses 
    user_form = 'user/new_user_form.html'

    def _form_to_db_schema(self):
        return user_form_schema()

    def _db_to_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def _setup_template_variables(self, context):
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

    ## end hooks

    def index(self):
        LIMIT = 20

        if not self.authorizer.am_authorized(c, model.Action.USER_READ, model.System):
            abort(401, _('Not authorized to see this page'))

        page = int(request.params.get('page', 1))
        c.q  = request.params.get('q', '')
        c.order_by = request.params.get('order_by', 'name')

        context = {'model': model,
                   'user': c.user or c.author}

        data_dict = {'q':c.q,
                     'order_by':c.order_by}

        users_list = get.user_list(context,data_dict)

        c.page = h.Page(
            collection=users_list,
            page=page,
            item_count=len(users_list),
            items_per_page=LIMIT
            )
        return render('user/list.html')

    def read(self, id=None):
        if not self.authorizer.am_authorized(c, model.Action.USER_READ, model.System):
            abort(401, _('Not authorized to see this page'))

        context = {'model': model,
                   'user': c.user or c.author}

        data_dict = {'id':id,
                     'user':c.userobj}
        try:
            user_dict = get.user_show(context,data_dict)
        except NotFound:
             abort(404, _('User not found'))
 
        if not user_dict:
            h.redirect_to(controller='user', action='login', id=None)

        c.user_dict = user_dict
        c.is_myself = user_dict['name'] == c.user
        c.about_formatted = self._format_about(user_dict['about'])

        return render('user/read.html')
    
    def me(self):
        if not c.user:
            h.redirect_to(controller='user', action='login', id=None)
        user_ref = c.userobj.get_reference_preferred_for_uri()
        h.redirect_to(controller='user', action='read', id=user_ref)

    def register(self, data=None, errors=None, error_summary=None):
        return self.new(data, errors, error_summary)

    def new(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._form_to_db_schema(),
                   'save': 'save' in request.params}

        auth_for_create = Authorizer().am_authorized(c, model.Action.USER_CREATE, model.System())
        if not auth_for_create:
            abort(401, _('Unauthorized to create a user'))

        if context['save'] and not data:
            return self._save_new(context)
        
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render(self.user_form, extra_vars=vars)
        return render('user/new.html')

    def _save_new(self, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            user = create.user_create(context, data_dict)
            h.redirect_to(controller='user', action='read', id=user['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to create user %s') % '')
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

    def login(self):
        return render('user/login.html')
    
    def logged_in(self):
        if c.user:
            context = {'model': model,
                       'user': c.user}

            data_dict = {'id':c.user}

            user_dict = get.user_show(context,data_dict)

            response.set_cookie("ckan_user", user_dict['name'])
            response.set_cookie("ckan_display_name", user_dict['display_name'])
            response.set_cookie("ckan_apikey", user_dict['apikey'])
            h.flash_success(_("Welcome back, %s") % user_dict['display_name'])
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
            user = model.User.by_name(c.user)
        if user is None:
            abort(404)
        currentuser = model.User.by_name(c.user)
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
            if user is None:
                h.flash_error(_('No such user: %s') % id)
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
            h.flash_error(_('Invalid reset key. Please try again.'))
            abort(403)
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
        
