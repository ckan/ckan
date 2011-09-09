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
from ckan.logic.schema import user_new_form_schema, user_edit_form_schema 

import ckan.logic.action.get as get
import ckan.logic.action.create as create
import ckan.logic.action.update as update

log = logging.getLogger(__name__)

def login_form():
    return render('user/login_form.html').replace('FORM_ACTION', '%s')

class UserController(BaseController):

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
                     'user_obj':c.userobj}
        try:
            user_dict = get.user_show(context,data_dict)
        except NotFound:
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
        '''GET to display a form for registering a new user.
           or POST the form data to actually do the user registration.
        '''
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'schema': self._new_form_to_db_schema(),
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
        c.form = render(self.new_user_form, extra_vars=vars)
        return render('user/new.html')

    def _save_new(self, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            user = create.user_create(context, data_dict)
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
        # Redirect to a URL picked up by repoze.who which performs the login
        h.redirect_to('/login_generic?login=%s&password=%s' % (
            str(data_dict['name']),
            quote(data_dict['password1'].encode('utf-8'))))


    def edit(self, id=None, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'preview': 'preview' in request.params,
                   'save': 'save' in request.params,
                   'schema': self._edit_form_to_db_schema(),
                   }
        if id is None:
            if c.userobj:
                id = c.userobj.id
            else:
                abort(400, _('No user specified'))
        data_dict = {'id': id}

        if (context['save'] or context['preview']) and not data:
            return self._save_edit(id, context)

        try:
            old_data = get.user_show(context, data_dict)

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

        c.form = render(self.edit_user_form, extra_vars=vars)

        return render('user/edit.html')

    def _save_edit(self, id, context):
        try:
            data_dict = clean_dict(unflatten(
                tuplize_dict(parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id
            user = update.user_update(context, data_dict)

            if context['preview']:
                about = request.params.getone('about')
                c.preview = self._format_about(about)
                c.user_about = about
                c.full_name = request.params.get('fullname','')
                c.email = request.params.getone('email')

                return self.edit(id, data_dict)

            h.redirect_to(controller='user', action='read', id=user['id'])
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
            return self.me()
        else:
            h.flash_error('Login failed. Bad username or password.')
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
                user_dict = get.user_show(context,data_dict)
                user_obj = context['user_obj']
            except NotFound:
                # Try searching the user
                del data_dict['id']
                data_dict['q'] = id

                if id and len(id) > 2:
                    user_list = get.user_list(context,data_dict)
                    if len(user_list) == 1:
                        # This is ugly, but we need the user object for the mailer,
                        # and user_list does not return them
                        del data_dict['q']
                        data_dict['id'] = user_list[0]['id']
                        user_dict = get.user_show(context,data_dict)
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
                    redirect('/')
                except mailer.MailerException, e:
                    h.flash_error(_('Could not send reset link: %s') % unicode(e))
        return render('user/request_reset.html')

    def perform_reset(self, id):
        context = {'model': model, 'session': model.Session,
                   'user': c.user}

        data_dict = {'id':id}

        try:
            user_dict = get.user_show(context,data_dict)
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
                user = update.user_update(context, user_dict)

                h.flash_success(_("Your password has been reset."))
                redirect('/')
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
        
