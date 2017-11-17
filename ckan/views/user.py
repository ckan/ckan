# encoding: utf-8
import logging

from flask import Blueprint
from flask.views import MethodView
from paste.deploy.converters import asbool

import ckan.plugins as plugins
import ckan.lib.captcha as captcha
import ckan.lib.authenticator as authenticator
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.logic as logic
import ckan.logic.schema as schema
import ckan.model as model
from ckan import authz
from ckan.common import _, config, g, request
import ckan.lib.mailer as mailer

log = logging.getLogger(__name__)

# hooks for subclasses
new_user_form = 'user/new_user_form.html'
edit_user_form = 'user/edit_user_form.html'

user = Blueprint(u'user', __name__, url_prefix=u'/user')


def _get_repoze_handler(handler_name):
    '''Returns the URL that repoze.who will respond to and perform a
    login or logout.'''
    return getattr(request.environ['repoze.who.plugins']['friendlyform'],
                   handler_name)


def set_repoze_user(user_id, resp):
    '''Set the repoze.who cookie to match a given user_id'''
    if 'repoze.who.plugins' in request.environ:
        rememberer = request.environ['repoze.who.plugins']['friendlyform']
        identity = {'repoze.who.userid': user_id}
        resp.headers.extend(rememberer.remember(request.environ, identity))


def _edit_form_to_db_schema():
    return schema.user_edit_form_schema()


def _new_form_to_db_schema():
    return schema.user_new_form_schema()


def _extra_template_variables(context, data_dict):
    is_sysadmin = authz.is_sysadmin(g.user)
    try:
        user_dict = logic.get_action('user_show')(context, data_dict)
    except logic.NotFound:
        h.flash_error(_('Not authorized to see this page'))
        return
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    user_dict = user_dict
    is_myself = user_dict['name'] == g.user
    about_formatted = h.render_markdown(user_dict['about'])
    extra = {
        'is_sysadmin': is_sysadmin,
        'user_dict': user_dict,
        'is_myself': is_myself,
        'about_formatted': about_formatted
    }
    return extra


@user.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        _, action = request.url_rule.endpoint.split('.')
        if action not in (
                'login',
                'request_reset',
                'perform_reset',
        ):
            base.abort(403, _('Not authorized to see this page'))


def index():
    page_number = h.get_page_number(request.params)
    q = request.params.get('q', '')
    limit = int(
        request.params.get('limit', config.get('ckan.user_list_limit', 20)))
    context = {
        'return_query': True,
        'user': g.user,
        'auth_user_obj': g.userobj
    }

    data_dict = {'q': q, 'order_by': request.params.get('order_by', 'name')}

    try:
        logic.check_access('user_list', context, data_dict)
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    users_list = logic.get_action('user_list')(context, data_dict)

    page = h.Page(
        collection=users_list,
        page=page_number,
        url=h.pager_url,
        item_count=users_list.count(),
        items_per_page=limit)

    extra_vars = {'page': page, 'q': q}
    return base.render('user/list.html', extra_vars)


# TODO: update after dashboard blueprint finished
def me():
    action = 'dashboard' if g.user else 'login'
    return h.redirect_to(controller='user', action=action)


def read(id):
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj,
        'for_view': True
    }
    data_dict = {
        'id': id,
        'user_obj': g.userobj,
        'include_datasets': True,
        'include_num_followers': True
    }

    extra_vars = _extra_template_variables(context, data_dict)
    if extra_vars is None:
        return h.redirect_to('user.login')
    return base.render('user/read.html', extra_vars)


class EditView(MethodView):
    def _prepare(self, id):
        context = {
            'save': 'save' in request.form,
            'schema': _edit_form_to_db_schema(),
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        if id is None:
            if g.userobj:
                id = g.userobj.id
            else:
                base.abort(400, _('No user specified'))
        data_dict = {'id': id}

        try:
            logic.check_access('user_update', context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to edit a user.'))
        return context, id

    def post(self, id=None):
        context, id = self._prepare(id)
        if not context['save']:
            return self.get(id)

        if id in (g.userobj.id, g.userobj.name):
            current_user = True
        else:
            current_user = False
        old_username = g.userobj.name

        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))

        context['message'] = data_dict.get('log_message', '')
        data_dict['id'] = id
        email_changed = data_dict['email'] != g.userobj.email

        if (data_dict['password1']
                and data_dict['password2']) or email_changed:
            identity = {'login': g.user, 'password': data_dict['old_password']}
            auth = authenticator.UsernamePasswordAuthenticator()

            if auth.authenticate(request.environ, identity) != g.user:
                errors = {'oldpassword': [_('Password entered was incorrect')]}
                error_summary = {_('Old Password'): _('incorrect password')}
                return self.get(id, data_dict, errors, error_summary)

        try:
            user = logic.get_action('user_update')(context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to edit user %s') % id)
        except logic.NotFound:
            base.abort(404, _('User not found'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, data_dict, errors, error_summary)

        h.flash_success(_('Profile updated'))
        resp = h.redirect_to('user.read', id=user['name'])
        if current_user and data_dict['name'] != old_username:
            # Changing currently logged in user's name.
            # Update repoze.who cookie to match
            set_repoze_user(data_dict['name'], resp)
        return resp

    def get(self, id=None, data=None, errors=None, error_summary=None):
        context, id = self._prepare(id)
        data_dict = {'id': id}
        try:
            old_data = logic.get_action('user_show')(context, data_dict)

            g.display_name = old_data.get('display_name')
            g.user_name = old_data.get('name')

            data = data or old_data

        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to edit user %s') % '')
        except logic.NotFound:
            base.abort(404, _('User not found'))
        user_obj = context.get('user_obj')

        if not (authz.is_sysadmin(g.user) or g.user == user_obj.name):
            msg = _('User %s not authorized to edit %s') % (str(g.user), id)
            base.abort(403, msg)

        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}

        extra_vars = _extra_template_variables({
            'model': model,
            'session': model.Session,
            'user': g.user
        }, data_dict)

        extra_vars['is_myself'] = True
        extra_vars['show_email_notifications'] = asbool(
            config.get('ckan.activity_streams_email_notifications'))
        vars.update(extra_vars)
        extra_vars['form'] = base.render(edit_user_form, extra_vars=vars)

        return base.render('user/edit.html', extra_vars)


class RegisterView(MethodView):
    def _prepare(self):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj,
            'schema': _new_form_to_db_schema(),
            'save': 'save' in request.form
        }
        try:
            logic.check_access('user_create', context)
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to register as a user.'))
        return context

    def post(self):
        context = self._prepare()
        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))

        context['message'] = data_dict.get('log_message', '')
        try:
            captcha.check_recaptcha(request)
        except captcha.CaptchaError:
            error_msg = _(u'Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.get(data_dict)

        try:
            logic.get_action('user_create')(context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to create user %s') % '')
        except logic.NotFound:
            base.abort(404, _('User not found'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict, errors, error_summary)

        if g.user:
            # #1799 User has managed to register whilst logged in - warn user
            # they are not re-logged in as new user.
            h.flash_success(
                _('User "%s" is now registered but you are still '
                  'logged in as "%s" from before') % (data_dict['name'],
                                                      g.user))
            if authz.is_sysadmin(g.user):
                # the sysadmin created a new user. We redirect him to the
                # activity page for the newly created user
                return h.redirect_to('user.activity', id=data_dict['name'])
            else:
                return base.render('user/logout_first.html')

        # log the user in programatically
        resp = h.redirect_to('user.me')
        set_repoze_user(data_dict['name'], resp)
        return resp

    def get(self, data=None, errors=None, error_summary=None):
        self._prepare()

        if g.user and not data and not authz.is_sysadmin(g.user):
            # #1799 Don't offer the registration form if already logged in
            return base.render('user/logout_first.html', {})

        form_vars = {
            'data': data or {},
            'errors': errors or {},
            'error_summary': error_summary or {}
        }

        extra_vars = {
            'is_sysadmin': authz.is_sysadmin(g.user),
            'form': base.render(new_user_form, form_vars)
        }
        return base.render('user/new.html', extra_vars)


def login():
    # Do any plugin login stuff
    for item in plugins.PluginImplementations(plugins.IAuthenticator):
        item.login()

    extra_vars = {}
    if g.user:
        return base.render('user/logout_first.html', extra_vars)

    came_from = request.params.get('came_from')
    if not came_from:
        came_from = h.url_for('user.logged_in')
    g.login_handler = h.url_for(
        _get_repoze_handler('login_handler_path'), came_from=came_from)
    return base.render('user/login.html', extra_vars)


def logged_in():
    # redirect if needed
    came_from = request.params.get('came_from', '')
    if h.url_is_local(came_from):
        return h.redirect_to(str(came_from))

    if g.user:
        return me()
    else:
        err = _('Login failed. Bad username or password.')
        h.flash_error(err)
        return login()


def logout():
    # Do any plugin logout stuff
    for item in plugins.PluginImplementations(plugins.IAuthenticator):
        item.logout()
    url = h.url_for('user.logged_out_page')
    return h.redirect_to(
        _get_repoze_handler('logout_handler_path') + '?came_from=' + url,
        parse_url=True)


def logged_out():
    # redirect if needed
    came_from = request.params.get('came_from', '')
    if h.url_is_local(came_from):
        return h.redirect_to(str(came_from))
    return h.redirect_to('user.logged_out_page')


def logged_out_page():
    return base.render('user/logout.html', {})


def delete(id):
    '''Delete user with id passed as parameter'''
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id}
    try:
        logic.get_action('user_delete')(context, data_dict)
    except logic.NotAuthorized:
        msg = _('Unauthorized to delete user with id "{user_id}".')
        base.abort(403, msg.format(user_id=id))

    user_index = h.url_for('user.index')
    return h.redirect_to(user_index)


def generate_apikey(id=None):
    '''Cycle the API key of a user'''
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj,
    }
    if id is None:
        if g.userobj:
            id = g.userobj.id
        else:
            base.abort(400, _('No user specified'))
    data_dict = {'id': id}

    try:
        result = logic.get_action('user_generate_apikey')(context, data_dict)
    except logic.NotAuthorized:
        base.abort(403, _('Unauthorized to edit user %s') % '')
    except logic.NotFound:
        base.abort(404, _('User not found'))

    h.flash_success(_('Profile updated'))
    return h.redirect_to('user.read', id=result['name'])


def activity(id, offset=0):
    '''Render this user's public activity stream page.'''

    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj,
        'for_view': True
    }
    data_dict = {
        'id': id,
        'user_obj': g.userobj,
        'include_num_followers': True
    }
    try:
        logic.check_access('user_show', context, data_dict)
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))

    extra_vars = _extra_template_variables(context, data_dict)

    try:
        g.user_activity_stream = logic.get_action('user_activity_list_html')(
            context, {
                'id': extra_vars['user_dict']['id'],
                'offset': offset
            })
    except logic.ValidationError:
        base.abort(400)

    return base.render('user/activity_stream.html', extra_vars)


class RequestResetView(MethodView):
    def _prepare(self):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        data_dict = {'id': request.form.get('user')}
        try:
            logic.check_access('request_reset', context)
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to request reset password.'))
        return context, data_dict

    def post(self):
        context, data_dict = self._prepare()
        id = data_dict['id']

        context = {'model': model, 'user': g.user}
        user_obj = None
        try:
            logic.get_action('user_show')(context, data_dict)
            user_obj = context['user_obj']
        except logic.NotFound:
            # Try searching the user
            if id and len(id) > 2:
                user_list = logic.get_action('user_list')(context, {'id': id})
                if len(user_list) == 1:
                    # This is ugly, but we need the user object for the
                    # mailer,
                    # and user_list does not return them
                    data_dict['id'] = user_list[0]['id']
                    logic.get_action('user_show')(context, data_dict)
                    user_obj = context['user_obj']
                elif len(user_list) > 1:
                    h.flash_error(_('"%s" matched several users') % (id))
                else:
                    h.flash_error(_('No such user: %s') % id)
            else:
                h.flash_error(_('No such user: %s') % id)

        if user_obj:
            try:
                # FIXME: How about passing user.id instead? Mailer already
                # uses model and it allow to simplify code above
                mailer.send_reset_link(user_obj)
                h.flash_success(
                    _('Please check your inbox for '
                      'a reset code.'))
                return h.redirect_to('/')
            except mailer.MailerException, e:
                h.flash_error(_('Could not send reset link: %s') % unicode(e))
        return self.get()

    def get(self):
        context, data_dict = self._prepare()
        return base.render('user/request_reset.html', {})


class PerformResetView(MethodView):
    def _prepare(self, id):
        # FIXME 403 error for invalid key is a non helpful page
        context = {
            'model': model,
            'session': model.Session,
            'user': id,
            'keep_email': True
        }

        try:
            logic.check_access('user_reset', context)
        except logic.NotAuthorized:
            base.abort(403, _('Unauthorized to reset password.'))

        try:
            user_dict = logic.get_action('user_show')(context, {'id': id})
        except logic.NotFound:
            base.abort(404, _('User not found'))
        user_obj = context['user_obj']
        g.reset_key = request.params.get('key')
        if not mailer.verify_reset_link(user_obj, g.reset_key):
            msg = _('Invalid reset key. Please try again.')
            h.flash_error(msg)
            base.abort(403, msg)
        return context, user_dict

    def _get_form_password(self):
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        if (password1 is not None and password1 != ''):
            if len(password1) < 8:
                raise ValueError(
                    _('Your password must be 8 '
                      'characters or longer.'))
            elif password1 != password2:
                raise ValueError(
                    _('The passwords you entered'
                      ' do not match.'))
            return password1
        raise ValueError(_('You must provide a password'))

    def post(self, id):
        context, user_dict = self._prepare(id)
        context['reset_password'] = True
        user_state = user_dict['state']
        try:
            new_password = self._get_form_password()
            user_dict['password'] = new_password
            username = request.form.get('name')
            if (username is not None and username != ''):
                user_dict['name'] = username
            user_dict['reset_key'] = g.reset_key
            user_dict['state'] = model.State.ACTIVE
            logic.get_action('user_update')(context, user_dict)
            mailer.create_reset_key(context['user_obj'])

            h.flash_success(_("Your password has been reset."))
            return h.redirect_to('/')
        except logic.NotAuthorized:
            h.flash_error(_('Unauthorized to edit user %s') % id)
        except logic.NotFound:
            h.flash_error(_('User not found'))
        except dictization_functions.DataError:
            h.flash_error(_(u'Integrity Error'))
        except logic.ValidationError, e:
            h.flash_error(u'%r' % e.error_dict)
        except ValueError as e:
            h.flash_error(unicode(e))
        user_dict['state'] = user_state
        return base.render('user/perform_reset.html', {'user_dict': user_dict})

    def get(self, id):
        context, user_dict = self._prepare(id)
        return base.render('user/perform_reset.html', {'user_dict': user_dict})


def follow(id):
    '''Start following this user.'''
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id, 'include_num_followers': True}
    try:
        logic.get_action('follow_user')(context, data_dict)
        user_dict = logic.get_action('user_show')(context, data_dict)
        h.flash_success(
            _("You are now following {0}").format(user_dict['display_name']))
    except logic.ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except logic.NotAuthorized as e:
        h.flash_error(e.message)
    return h.redirect_to('user.read', id=id)


def unfollow(id):
    '''Stop following this user.'''
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj
    }
    data_dict = {'id': id, 'include_num_followers': True}
    try:
        logic.get_action('unfollow_user')(context, data_dict)
        user_dict = logic.get_action('user_show')(context, data_dict)
        h.flash_success(
            _("You are no longer following {0}").format(
                user_dict['display_name']))
    except (logic.NotFound, logic.NotAuthorized) as e:
        error_message = e.message
        h.flash_error(error_message)
    except logic.ValidationError as e:
        error_message = (e.error_summary or e.message or e.error_dict)
        h.flash_error(error_message)
    return h.redirect_to('user.read', id=id)


def followers(id):
    context = {'for_view': True, 'user': g.user, 'auth_user_obj': g.userobj}
    data_dict = {
        'id': id,
        'user_obj': g.userobj,
        'include_num_followers': True
    }
    extra_vars = _extra_template_variables(context, data_dict)
    f = logic.get_action('user_follower_list')
    try:
        extra_vars['followers'] = f(context, {
            'id': extra_vars['user_dict']['id']
        })
    except logic.NotAuthorized:
        base.abort(403, _('Unauthorized to view followers %s') % '')
    return base.render('user/followers.html', extra_vars)


user.add_url_rule(u'/', view_func=index, strict_slashes=False)
user.add_url_rule(u'/me', view_func=me)

_edit_view = EditView.as_view(str(u'edit'))
user.add_url_rule(u'/edit', view_func=_edit_view)
user.add_url_rule(u'/edit/<id>', view_func=_edit_view)

user.add_url_rule(
    u'/register', view_func=RegisterView.as_view(str(u'register')))

user.add_url_rule(u'/login', view_func=login)
user.add_url_rule(u'/logged_in', view_func=logged_in)
user.add_url_rule(u'/_logout', view_func=logout)
user.add_url_rule(u'/logged_out', view_func=logged_out)
user.add_url_rule(u'/logged_out_redirect', view_func=logged_out_page)

user.add_url_rule(u'/delete/<id>', view_func=delete, methods=('POST', ))

user.add_url_rule(
    '/generate_key', view_func=generate_apikey, methods=('POST', ))
user.add_url_rule(
    '/generate_key/<id>', view_func=generate_apikey, methods=('POST', ))

user.add_url_rule('/activity/<id>', view_func=activity)
user.add_url_rule('/activity/<id>/<int:offset>', view_func=activity)

user.add_url_rule(
    '/reset', view_func=RequestResetView.as_view(str(u'request_reset')))
user.add_url_rule(
    '/reset/<id>', view_func=PerformResetView.as_view(str(u'perform_reset')))

user.add_url_rule('/follow/<id>', view_func=follow)
user.add_url_rule('/unfollow/<id>', view_func=unfollow)
user.add_url_rule('/followers/<id>', view_func=followers)

user.add_url_rule(u'/<id>', view_func=read)
