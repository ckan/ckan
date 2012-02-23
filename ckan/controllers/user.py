import logging

import genshi
from urllib import quote

import ckan.misc
from ckan.lib.base import *
from ckan.lib import mailer
from ckan.authz import Authorizer
from ckan.lib.navl.dictization_functions import DataError, unflatten
from ckan.logic import NotFound, NotAuthorized, ValidationError
from ckan.logic import check_access, get_action
from ckan.logic import tuplize_dict, clean_dict, parse_params
from ckan.logic.schema import user_new_form_schema, user_edit_form_schema 
from ckan.logic.action.get import user_activity_list_html
from ckan.lib.captcha import check_recaptcha, CaptchaError

log = logging.getLogger(__name__)

class UserController(BaseController):

    def __before__(self, action, **env):
        BaseController.__before__(self, action, **env)
        try:
            context = {'model':model,'user': c.user or c.author}
            check_access('site_read',context)
        except NotAuthorized:
            if c.action not in ('login','request_reset','perform_reset',):
                abort(401, _('Not authorized to see this page'))

    ## hooks for subclasses 
    new_user_form = 'user/new_user_form.html'
    edit_user_form = 'user/edit_user_form.html'

    def _new_form_to_db_schema(self):
        return user_new_form_schema()

    def _db_to_new_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def _edit_form_to_db_schema(self):
        return user_edit_form_schema()

    def _db_to_edit_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def _setup_template_variables(self, context):
        c.is_sysadmin = Authorizer().is_sysadmin(c.user)

    ## end hooks

    def index(self):
        LIMIT = 20

        page = int(request.params.get('page', 1))
        c.q  = request.params.get('q', '')
        c.order_by = request.params.get('order_by', 'name')

        context = {'model': model,
                   'user': c.user or c.author,
                   'return_query': True}

        data_dict = {'q':c.q,
                     'order_by':c.order_by}
        try:
            check_access('user_list',context, data_dict)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        users_list = get_action('user_list')(context,data_dict)

        c.page = h.Page(
            collection=users_list,
            page=page,
            url=h.pager_url,
            item_count=users_list.count(),
            items_per_page=LIMIT
        )
        return render('user/list.html')

    def read(self, id=None):
        context = {'model': model,
                   'user': c.user or c.author}
        data_dict = {'id':id,
                     'user_obj':c.userobj}
        try:
            check_access('user_show',context, data_dict)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        try:
            user_dict = get_action('user_show')(context,data_dict)
        except NotFound:
            h.redirect_to(controller='user', action='login', id=None)

        c.user_dict = user_dict
        c.is_myself = user_dict['name'] == c.user
        c.about_formatted = self._format_about(user_dict['about'])
        c.user_activity_stream = user_activity_list_html(context,
            {'id':c.user_dict['id']})
        return render('user/read.html')

    def me(self):
        if not c.user:
            h.redirect_to(controller='user', action='login', id=None)
        user_ref = c.userobj.get_reference_preferred_for_uri()
        h.redirect_to(controller='user', action='read', id=user_ref)

    def register(self, data=None, errors=None, error_summary=None):
        return self.new(data, errors, error_summary)

    def new(self, data=None, errors=None, error_summary=None):
        '''GET to display a form for registering a new user.
           or POST the form data to actually do the user registration.
        '''
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._new_form_to_db_schema(),
                   'save': 'save' in request.params}

        try:
            check_access('user_create',context)
        except NotAuthorized:
            abort(401, _('Unauthorized to create a user'))

        if context['save'] and not data:
            return self._save_new(context)

        if c.user and not data:
            # #1799 Don't offer the registration form if already logged in
            return render('user/logout_first.html')            
        
        data = data or {}
        errors = errors or {}
        error_summary = error_summary or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)
        c.form = render(self.new_user_form, extra_vars=vars)
        return render('user/new.html')

    def _save_new(self, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            check_recaptcha(request)
            user = get_action('user_create')(context, data_dict)
        except NotAuthorized:
            abort(401, _('Unauthorized to create user %s') % '')
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except CaptchaError:
            error_msg = _(u'Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.new(data_dict)
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)
        if not c.user:
            # Redirect to a URL picked up by repoze.who which performs the login
            h.redirect_to('/login_generic?login=%s&password=%s' % (
                str(data_dict['name']),
                quote(data_dict['password1'].encode('utf-8'))))
        else:
            # #1799 User has managed to register whilst logged in - warn user
            # they are not re-logged in as new user.
            h.flash_success(_('User "%s" is now registered but you are still logged in as "%s" from before') % (data_dict['name'], c.user))
            return render('user/logout_first.html')

    def edit(self, id=None, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'save': 'save' in request.params,
                   'schema': self._edit_form_to_db_schema(),
                   }
        if id is None:
            if c.userobj:
                id = c.userobj.id
            else:
                abort(400, _('No user specified'))
        data_dict = {'id': id}

        if (context['save']) and not data:
            return self._save_edit(id, context)

        try:
            old_data = get_action('user_show')(context, data_dict)

            schema = self._db_to_edit_form_schema()
            if schema:
                old_data, errors = validate(old_data, schema)

            c.display_name = old_data.get('display_name')
            c.user_name = old_data.get('name')

            data = data or old_data

        except NotAuthorized:
            abort(401, _('Unauthorized to edit user %s') % '')
        except NotFound, e:
            abort(404, _('User not found'))

        user_obj = context.get('user_obj')
        
        if not (ckan.authz.Authorizer().is_sysadmin(unicode(c.user)) or c.user == user_obj.name):
            abort(401, _('User %s not authorized to edit %s') % (str(c.user), id))
        
        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables(context)

        c.is_myself = True
        c.form = render(self.edit_user_form, extra_vars=vars)

        return render('user/edit.html')

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            user = get_action('user_update')(context, data_dict)
            h.flash_success(_('Profile updated'))
            h.redirect_to(controller='user', action='read', id=user['name'])
        except NotAuthorized:
            abort(401, _('Unauthorized to edit user %s') % id)
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.edit(id, data_dict, errors, error_summary)


    def login(self):
        if 'error' in request.params:
            h.flash_error(request.params['error'])

        if request.environ['SCRIPT_NAME'] and g.openid_enabled:
            # #1662 restriction
            log.warn('Cannot mount CKAN at a URL and login with OpenID.')
            g.openid_enabled = False

        if not c.user:
            return render('user/login.html')
        else:
            return render('user/logout_first.html')
    
    def logged_in(self):
        if c.user:
            context = {'model': model,
                       'user': c.user}

            data_dict = {'id':c.user}

            user_dict = get_action('user_show')(context,data_dict)

            # Max age of cookies: 50 years. Matches time set in templates/user/login.html
            cookie_timeout=50*365*24*60*60

            response.set_cookie("ckan_user", user_dict['name'], max_age=cookie_timeout)
            response.set_cookie("ckan_display_name", user_dict['display_name'], max_age=cookie_timeout)
            response.set_cookie("ckan_apikey", user_dict['apikey'], max_age=cookie_timeout)
            h.flash_success(_("%s is now logged in") % user_dict['display_name'])
            return self.me()
        else:
            h.flash_error('Login failed. Bad username or password.' + \
                          ' (Or if using OpenID, it hasn\'t been associated with a user account.)')
            h.redirect_to(controller='user', action='login')
          
    def logged_out(self):
        c.user = None
        response.delete_cookie("ckan_user")
        response.delete_cookie("ckan_display_name")
        response.delete_cookie("ckan_apikey")
        return render('user/logout.html')
    
    def request_reset(self):
        if request.method == 'POST':
            id = request.params.get('user')

            context = {'model': model,
                       'user': c.user}

            data_dict = {'id':id}
            user_obj = None
            try:
                user_dict = get_action('user_show')(context,data_dict)
                user_obj = context['user_obj']
            except NotFound:
                # Try searching the user
                del data_dict['id']
                data_dict['q'] = id

                if id and len(id) > 2:
                    user_list = get_action('user_list')(context,data_dict)
                    if len(user_list) == 1:
                        # This is ugly, but we need the user object for the mailer,
                        # and user_list does not return them
                        del data_dict['q']
                        data_dict['id'] = user_list[0]['id']
                        user_dict = get_action('user_show')(context,data_dict)
                        user_obj = context['user_obj']
                    elif len(user_list) > 1:
                        h.flash_error(_('"%s" matched several users') % (id))
                    else:
                        h.flash_error(_('No such user: %s') % id)
                else:
                    h.flash_error(_('No such user: %s') % id)

            if user_obj:
                try:
                    mailer.send_reset_link(user_obj)
                    h.flash_success(_('Please check your inbox for a reset code.'))
                    h.redirect_to('/')
                except mailer.MailerException, e:
                    h.flash_error(_('Could not send reset link: %s') % unicode(e))
        return render('user/request_reset.html')

    def perform_reset(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        data_dict = {'id':id}

        try:
            user_dict = get_action('user_show')(context,data_dict)
            user_obj = context['user_obj']
        except NotFound, e:
            abort(404, _('User not found'))

        c.reset_key = request.params.get('key')
        if not mailer.verify_reset_link(user_obj, c.reset_key):
            h.flash_error(_('Invalid reset key. Please try again.'))
            abort(403)

        if request.method == 'POST':
            try:
                context['reset_password'] = True 
                new_password = self._get_form_password()
                user_dict['password'] = new_password
                user_dict['reset_key'] = c.reset_key
                user = get_action('user_update')(context, user_dict)

                h.flash_success(_("Your password has been reset."))
                h.redirect_to('/')
            except NotAuthorized:
                h.flash_error(_('Unauthorized to edit user %s') % id)
            except NotFound, e:
                h.flash_error(_('User not found'))
            except DataError:
                h.flash_error(_(u'Integrity Error'))
            except ValidationError, e:
                h.flash_error(u'%r'% e.error_dict)
            except ValueError, ve:
                h.flash_error(unicode(ve))
        return render('user/perform_reset.html')

    def _format_about(self, about):
        about_formatted = ckan.misc.MarkdownFormat().to_html(about)
        try:
            html = genshi.HTML(about_formatted)
        except genshi.ParseError, e:
            log.error('Could not print "about" field Field: %r Error: %r', about, e)
            html = _('Error: Could not parse About text')
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
        
