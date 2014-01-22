import logging
from urllib import quote
from urlparse import urlparse

from pylons import config

import ckan.lib.base as base
import ckan.model as model
import ckan.lib.helpers as h
import ckan.new_authz as new_authz
import ckan.logic as logic
import ckan.logic.schema as schema
import ckan.lib.captcha as captcha
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.plugins as p

from ckan.common import _, c, g, request

log = logging.getLogger(__name__)


abort = base.abort
render = base.render
validate = base.validate

check_access = logic.check_access
get_action = logic.get_action
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError

DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten


class UserController(base.BaseController):
    def __before__(self, action, **env):
        base.BaseController.__before__(self, action, **env)
        try:
            context = {'model': model, 'user': c.user or c.author,
                       'auth_user_obj': c.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            if c.action not in ('login', 'request_reset', 'perform_reset',):
                abort(401, _('Not authorized to see this page'))

    ## hooks for subclasses
    new_user_form = 'user/new_user_form.html'
    edit_user_form = 'user/edit_user_form.html'

    def _new_form_to_db_schema(self):
        return schema.user_new_form_schema()

    def _db_to_new_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def _edit_form_to_db_schema(self):
        return schema.user_edit_form_schema()

    def _db_to_edit_form_schema(self):
        '''This is an interface to manipulate data from the database
        into a format suitable for the form (optional)'''

    def _setup_template_variables(self, context, data_dict):
        c.is_sysadmin = new_authz.is_sysadmin(c.user)
        try:
            user_dict = get_action('user_show')(context, data_dict)
        except NotFound:
            abort(404, _('User not found'))
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))
        c.user_dict = user_dict
        c.is_myself = user_dict['name'] == c.user
        c.about_formatted = h.render_markdown(user_dict['about'])

    ## end hooks

    def _get_repoze_handler(self, handler_name):
        '''Returns the URL that repoze.who will respond to and perform a
        login or logout.'''
        return getattr(request.environ['repoze.who.plugins']['friendlyform'],
                       handler_name)

    def index(self):
        LIMIT = 20

        page = int(request.params.get('page', 1))
        c.q = request.params.get('q', '')
        c.order_by = request.params.get('order_by', 'name')

        context = {'return_query': True, 'user': c.user or c.author,
                   'auth_user_obj': c.userobj}

        data_dict = {'q': c.q,
                     'order_by': c.order_by}
        try:
            check_access('user_list', context, data_dict)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        users_list = get_action('user_list')(context, data_dict)

        c.page = h.Page(
            collection=users_list,
            page=page,
            url=h.pager_url,
            item_count=users_list.count(),
            items_per_page=LIMIT
        )
        return render('user/list.html')

    def read(self, id=None):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'for_view': True}
        data_dict = {'id': id,
                     'user_obj': c.userobj}

        context['with_related'] = True

        self._setup_template_variables(context, data_dict)

        # The legacy templates have the user's activity stream on the user
        # profile page, new templates do not.
        if h.asbool(config.get('ckan.legacy_templates', False)):
            c.user_activity_stream = get_action('user_activity_list_html')(
                context, {'id': c.user_dict['id']})

        return render('user/read.html')

    def me(self, locale=None):
        if not c.user:
            h.redirect_to(locale=locale, controller='user', action='login',
                          id=None)
        user_ref = c.userobj.get_reference_preferred_for_uri()
        h.redirect_to(locale=locale, controller='user', action='dashboard',
                      id=user_ref)

    def register(self, data=None, errors=None, error_summary=None):
        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'auth_user_obj': c.userobj}
        try:
            check_access('user_create', context)
        except NotAuthorized:
            abort(401, _('Unauthorized to register as a user.'))

        return self.new(data, errors, error_summary)

    def new(self, data=None, errors=None, error_summary=None):
        '''GET to display a form for registering a new user.
           or POST the form data to actually do the user registration.
        '''
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'auth_user_obj': c.userobj,
                   'schema': self._new_form_to_db_schema(),
                   'save': 'save' in request.params}

        try:
            check_access('user_create', context)
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

        c.is_sysadmin = new_authz.is_sysadmin(c.user)
        c.form = render(self.new_user_form, extra_vars=vars)
        return render('user/new.html')

    def delete(self, id):
        '''Delete user with id passed as parameter'''
        context = {'model': model,
                   'session': model.Session,
                   'user': c.user,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id}

        try:
            get_action('user_delete')(context, data_dict)
            user_index = h.url_for(controller='user', action='index')
            h.redirect_to(user_index)
        except NotAuthorized:
            msg = _('Unauthorized to delete user with id "{user_id}".')
            abort(401, msg.format(user_id=id))

    def _save_new(self, context):
        try:
            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            captcha.check_recaptcha(request)
            user = get_action('user_create')(context, data_dict)
        except NotAuthorized:
            abort(401, _('Unauthorized to create user %s') % '')
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except captcha.CaptchaError:
            error_msg = _(u'Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.new(data_dict)
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)
        if not c.user:
            # Redirect to a URL picked up by repoze.who which performs the
            # login
            login_url = self._get_repoze_handler('login_handler_path')

            # We need to pass the logged in URL as came_from parameter
            # otherwise we lose the language setting
            came_from = h.url_for(controller='user', action='logged_in',
                                  __ckan_no_root=True)
            redirect_url = '{0}?login={1}&password={2}&came_from={3}'
            h.redirect_to(redirect_url.format(
                login_url,
                str(data_dict['name']),
                quote(data_dict['password1'].encode('utf-8')),
                came_from))
        else:
            # #1799 User has managed to register whilst logged in - warn user
            # they are not re-logged in as new user.
            h.flash_success(_('User "%s" is now registered but you are still '
                            'logged in as "%s" from before') %
                            (data_dict['name'], c.user))
            return render('user/logout_first.html')

    def edit(self, id=None, data=None, errors=None, error_summary=None):
        context = {'save': 'save' in request.params,
                   'schema': self._edit_form_to_db_schema(),
                   'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj
                   }
        if id is None:
            if c.userobj:
                id = c.userobj.id
            else:
                abort(400, _('No user specified'))
        data_dict = {'id': id}

        try:
            check_access('user_update', context, data_dict)
        except NotAuthorized:
            abort(401, _('Unauthorized to edit a user.'))

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
        except NotFound:
            abort(404, _('User not found'))

        user_obj = context.get('user_obj')

        if not (new_authz.is_sysadmin(c.user)
                or c.user == user_obj.name):
            abort(401, _('User %s not authorized to edit %s') %
                  (str(c.user), id))

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        self._setup_template_variables({'model': model,
                                        'session': model.Session,
                                        'user': c.user or c.author},
                                       data_dict)

        c.is_myself = True
        c.show_email_notifications = h.asbool(
            config.get('ckan.activity_streams_email_notifications'))
        c.form = render(self.edit_user_form, extra_vars=vars)

        return render('user/edit.html')

    def _save_edit(self, id, context):
        try:
            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            data_dict['id'] = id

            # MOAN: Do I really have to do this here?
            if 'activity_streams_email_notifications' not in data_dict:
                data_dict['activity_streams_email_notifications'] = False

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

    def login(self, error=None):
        # Do any plugin login stuff
        for item in p.PluginImplementations(p.IAuthenticator):
            item.login()

        if 'error' in request.params:
            h.flash_error(request.params['error'])

        if request.environ['SCRIPT_NAME'] and g.openid_enabled:
            # #1662 restriction
            log.warn('Cannot mount CKAN at a URL and login with OpenID.')
            g.openid_enabled = False

        if not c.user:
            came_from = request.params.get('came_from')
            if not came_from:
                came_from = h.url_for(controller='user', action='logged_in',
                                      __ckan_no_root=True)
            c.login_handler = h.url_for(
                self._get_repoze_handler('login_handler_path'),
                came_from=came_from)
            if error:
                vars = {'error_summary': {'': error}}
            else:
                vars = {}
            return render('user/login.html', extra_vars=vars)
        else:
            return render('user/logout_first.html')

    def logged_in(self):
        # redirect if needed
        came_from = request.params.get('came_from', '')
        if self._sane_came_from(came_from):
            return h.redirect_to(str(came_from))

        if c.user:
            context = None
            data_dict = {'id': c.user}

            user_dict = get_action('user_show')(context, data_dict)

            h.flash_success(_("%s is now logged in") %
                            user_dict['display_name'])
            return self.me()
        else:
            err = _('Login failed. Bad username or password.')
            if g.openid_enabled:
                err += _(' (Or if using OpenID, it hasn\'t been associated '
                         'with a user account.)')
            if h.asbool(config.get('ckan.legacy_templates', 'false')):
                h.flash_error(err)
                h.redirect_to(controller='user',
                              action='login', came_from=came_from)
            else:
                return self.login(error=err)

    def logout(self):
        # Do any plugin logout stuff
        for item in p.PluginImplementations(p.IAuthenticator):
            item.logout()
        url = h.url_for(controller='user', action='logged_out_page',
                        __ckan_no_root=True)
        h.redirect_to(self._get_repoze_handler('logout_handler_path') +
                      '?came_from=' + url)

    def logged_out(self):
        # redirect if needed
        came_from = request.params.get('came_from', '')
        if self._sane_came_from(came_from):
            return h.redirect_to(str(came_from))
        h.redirect_to(controller='user', action='logged_out_page')

    def logged_out_page(self):
        return render('user/logout.html')

    def request_reset(self):
        context = {'model': model, 'session': model.Session, 'user': c.user,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': request.params.get('user')}
        try:
            check_access('request_reset', context)
        except NotAuthorized:
            abort(401, _('Unauthorized to request reset password.'))

        if request.method == 'POST':
            id = request.params.get('user')

            context = {'model': model,
                       'user': c.user}

            data_dict = {'id': id}
            user_obj = None
            try:
                user_dict = get_action('user_show')(context, data_dict)
                user_obj = context['user_obj']
            except NotFound:
                # Try searching the user
                del data_dict['id']
                data_dict['q'] = id

                if id and len(id) > 2:
                    user_list = get_action('user_list')(context, data_dict)
                    if len(user_list) == 1:
                        # This is ugly, but we need the user object for the
                        # mailer,
                        # and user_list does not return them
                        del data_dict['q']
                        data_dict['id'] = user_list[0]['id']
                        user_dict = get_action('user_show')(context, data_dict)
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
                    h.flash_success(_('Please check your inbox for '
                                    'a reset code.'))
                    h.redirect_to('/')
                except mailer.MailerException, e:
                    h.flash_error(_('Could not send reset link: %s') %
                                  unicode(e))
        return render('user/request_reset.html')

    def perform_reset(self, id):
        # FIXME 403 error for invalid key is a non helpful page
        # FIXME We should reset the reset key when it is used to prevent
        # reuse of the url
        context = {'model': model, 'session': model.Session,
                   'user': id,
                   'keep_email': True}

        try:
            check_access('user_reset', context)
        except NotAuthorized:
            abort(401, _('Unauthorized to reset password.'))

        try:
            data_dict = {'id': id}
            user_dict = get_action('user_show')(context, data_dict)

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
                user_dict['state'] = model.State.ACTIVE
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
                h.flash_error(u'%r' % e.error_dict)
            except ValueError, ve:
                h.flash_error(unicode(ve))

        c.user_dict = user_dict
        return render('user/perform_reset.html')

    def _get_form_password(self):
        password1 = request.params.getone('password1')
        password2 = request.params.getone('password2')
        if (password1 is not None and password1 != ''):
            if not len(password1) >= 4:
                raise ValueError(_('Your password must be 4 '
                                 'characters or longer.'))
            elif not password1 == password2:
                raise ValueError(_('The passwords you entered'
                                 ' do not match.'))
            return password1
        raise ValueError(_('You must provide a password'))

    def followers(self, id=None):
        context = {'for_view': True, 'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id, 'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        f = get_action('user_follower_list')
        try:
            c.followers = f(context, {'id': c.user_dict['id']})
        except NotAuthorized:
            abort(401, _('Unauthorized to view followers %s') % '')
        return render('user/followers.html')

    def activity(self, id, offset=0):
        '''Render this user's public activity stream page.'''

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj}
        try:
            check_access('user_show', context, data_dict)
        except NotAuthorized:
            abort(401, _('Not authorized to see this page'))

        self._setup_template_variables(context, data_dict)

        c.user_activity_stream = get_action('user_activity_list_html')(
            context, {'id': c.user_dict['id'], 'offset': offset})

        return render('user/activity_stream.html')

    def _get_dashboard_context(self, filter_type=None, filter_id=None, q=None):
        '''Return a dict needed by the dashboard view to determine context.'''

        def display_name(followee):
            '''Return a display name for a user, group or dataset dict.'''
            display_name = followee.get('display_name')
            fullname = followee.get('fullname')
            title = followee.get('title')
            name = followee.get('name')
            return display_name or fullname or title or name

        if (filter_type and filter_id):
            context = {
                'model': model, 'session': model.Session,
                'user': c.user or c.author, 'auth_user_obj': c.userobj,
                'for_view': True
            }
            data_dict = {'id': filter_id}
            followee = None

            action_functions = {
                'dataset': 'package_show',
                'user': 'user_show',
                'group': 'group_show'
            }
            action_function = logic.get_action(
                action_functions.get(filter_type))
            # Is this a valid type?
            if action_function is None:
                abort(404, _('Follow item not found'))
            try:
                followee = action_function(context, data_dict)
            except NotFound:
                abort(404, _('{0} not found').format(filter_type))
            except NotAuthorized:
                abort(401, _('Unauthorized to read {0} {1}').format(
                    filter_type, id))

            if followee is not None:
                return {
                    'filter_type': filter_type,
                    'q': q,
                    'context': display_name(followee),
                    'selected_id': followee.get('id'),
                    'dict': followee,
                }

        return {
            'filter_type': filter_type,
            'q': q,
            'context': _('Everything'),
            'selected_id': False,
            'dict': None,
        }

    def dashboard(self, id=None, offset=0):
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'auth_user_obj': c.userobj,
                   'for_view': True}
        data_dict = {'id': id, 'user_obj': c.userobj, 'offset': offset}
        self._setup_template_variables(context, data_dict)

        q = request.params.get('q', u'')
        filter_type = request.params.get('type', u'')
        filter_id = request.params.get('name', u'')

        c.followee_list = get_action('followee_list')(
            context, {'id': c.userobj.id, 'q': q})
        c.dashboard_activity_stream_context = self._get_dashboard_context(
            filter_type, filter_id, q)
        c.dashboard_activity_stream = h.dashboard_activity_stream(
            c.userobj.id, filter_type, filter_id, offset
        )

        # Mark the user's new activities as old whenever they view their
        # dashboard page.
        get_action('dashboard_mark_activities_old')(context, {})

        return render('user/dashboard.html')

    def dashboard_datasets(self):
        context = {'for_view': True, 'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        data_dict = {'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        return render('user/dashboard_datasets.html')

    def dashboard_organizations(self):
        context = {'for_view': True, 'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        data_dict = {'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        return render('user/dashboard_organizations.html')

    def dashboard_groups(self):
        context = {'for_view': True, 'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        data_dict = {'user_obj': c.userobj}
        self._setup_template_variables(context, data_dict)
        return render('user/dashboard_groups.html')

    def follow(self, id):
        '''Start following this user.'''
        context = {'model': model,
                   'session': model.Session,
                   'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id}
        try:
            get_action('follow_user')(context, data_dict)
            user_dict = get_action('user_show')(context, data_dict)
            h.flash_success(_("You are now following {0}").format(
                user_dict['display_name']))
        except ValidationError as e:
            error_message = (e.extra_msg or e.message or e.error_summary
                             or e.error_dict)
            h.flash_error(error_message)
        except NotAuthorized as e:
            h.flash_error(e.extra_msg)
        h.redirect_to(controller='user', action='read', id=id)

    def unfollow(self, id):
        '''Stop following this user.'''
        context = {'model': model,
                   'session': model.Session,
                   'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        data_dict = {'id': id}
        try:
            get_action('unfollow_user')(context, data_dict)
            user_dict = get_action('user_show')(context, data_dict)
            h.flash_success(_("You are no longer following {0}").format(
                user_dict['display_name']))
        except (NotFound, NotAuthorized) as e:
            error_message = e.extra_msg or e.message
            h.flash_error(error_message)
        except ValidationError as e:
            error_message = (e.error_summary or e.message or e.extra_msg
                             or e.error_dict)
            h.flash_error(error_message)
        h.redirect_to(controller='user', action='read', id=id)

    def _sane_came_from(self, url):
        '''Returns True if came_from is local'''
        if not url or (len(url) >= 2 and url.startswith('//')):
            return False
        parsed = urlparse(url)
        if parsed.scheme:
            domain = urlparse(h.url_for('/', qualified=True)).netloc
            if domain != parsed.netloc:
                return False
        return True
