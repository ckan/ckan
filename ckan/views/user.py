# encoding: utf-8
import logging

from flask import Blueprint
from flask.views import MethodView
from paste.deploy.converters import asbool
from six import text_type

import ckan.lib.authenticator as authenticator
import ckan.lib.base as base
import ckan.lib.captcha as captcha
import ckan.lib.helpers as h
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.logic as logic
import ckan.logic.schema as schema
import ckan.model as model
import ckan.plugins as plugins
from ckan import authz
from ckan.common import _, config, g, request

log = logging.getLogger(__name__)

# hooks for subclasses
new_user_form = u'user/new_user_form.html'
edit_user_form = u'user/edit_user_form.html'

user = Blueprint(u'user', __name__, url_prefix=u'/user')


def _get_repoze_handler(handler_name):
    u'''Returns the URL that repoze.who will respond to and perform a
    login or logout.'''
    return getattr(request.environ[u'repoze.who.plugins'][u'friendlyform'],
                   handler_name)


def set_repoze_user(user_id, resp):
    u'''Set the repoze.who cookie to match a given user_id'''
    if u'repoze.who.plugins' in request.environ:
        rememberer = request.environ[u'repoze.who.plugins'][u'friendlyform']
        identity = {u'repoze.who.userid': user_id}
        resp.headers.extend(rememberer.remember(request.environ, identity))


def _edit_form_to_db_schema():
    return schema.user_edit_form_schema()


def _new_form_to_db_schema():
    return schema.user_new_form_schema()


def _extra_template_variables(context, data_dict):
    is_sysadmin = authz.is_sysadmin(g.user)
    try:
        user_dict = logic.get_action(u'user_show')(context, data_dict)
    except logic.NotFound:
        h.flash_error(_(u'Not authorized to see this page'))
        return
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    is_myself = user_dict[u'name'] == g.user
    about_formatted = h.render_markdown(user_dict[u'about'])
    extra = {
        u'is_sysadmin': is_sysadmin,
        u'user_dict': user_dict,
        u'is_myself': is_myself,
        u'about_formatted': about_formatted
    }
    return extra


@user.before_request
def before_request():
    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        blueprint, action = plugins.toolkit.get_endpoint()
        if action not in (
                u'login',
                u'request_reset',
                u'perform_reset',
        ):
            base.abort(403, _(u'Not authorized to see this page'))


def index():
    page_number = h.get_page_number(request.params)
    q = request.params.get(u'q', u'')
    order_by = request.params.get(u'order_by', u'name')
    limit = int(
        request.params.get(u'limit', config.get(u'ckan.user_list_limit', 20)))
    context = {
        u'return_query': True,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }

    data_dict = {
        u'q': q,
        u'order_by': order_by
    }

    try:
        logic.check_access(u'user_list', context, data_dict)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    users_list = logic.get_action(u'user_list')(context, data_dict)

    page = h.Page(
        collection=users_list,
        page=page_number,
        url=h.pager_url,
        item_count=users_list.count(),
        items_per_page=limit)

    extra_vars = {u'page': page, u'q': q, u'order_by': order_by}
    return base.render(u'user/list.html', extra_vars)


def me():
    route = u'dashboard.index' if g.user else u'user.login'
    return h.redirect_to(route)


def read(id):
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {
        u'id': id,
        u'user_obj': g.userobj,
        u'include_datasets': True,
        u'include_num_followers': True
    }
    # FIXME: line 331 in multilingual plugins expects facets to be defined.
    # any ideas?
    g.fields = []

    extra_vars = _extra_template_variables(context, data_dict)
    if extra_vars is None:
        return h.redirect_to(u'user.login')
    return base.render(u'user/read.html', extra_vars)


class EditView(MethodView):
    def _prepare(self, id):
        context = {
            u'save': u'save' in request.form,
            u'schema': _edit_form_to_db_schema(),
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        if id is None:
            if g.userobj:
                id = g.userobj.id
            else:
                base.abort(400, _(u'No user specified'))
        data_dict = {u'id': id}

        try:
            logic.check_access(u'user_update', context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit a user.'))
        return context, id

    def post(self, id=None):
        context, id = self._prepare(id)
        if not context[u'save']:
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
        data_dict.setdefault(u'activity_streams_email_notifications', False)

        context[u'message'] = data_dict.get(u'log_message', u'')
        data_dict[u'id'] = id
        email_changed = data_dict[u'email'] != g.userobj.email

        if (data_dict[u'password1']
                and data_dict[u'password2']) or email_changed:
            identity = {
                u'login': g.user,
                u'password': data_dict[u'old_password']
            }
            auth = authenticator.UsernamePasswordAuthenticator()

            if auth.authenticate(request.environ, identity) != g.user:
                errors = {
                    u'oldpassword': [_(u'Password entered was incorrect')]
                }
                error_summary = {_(u'Old Password'): _(u'incorrect password')}
                return self.get(id, data_dict, errors, error_summary)

        try:
            user = logic.get_action(u'user_update')(context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit user %s') % id)
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(id, data_dict, errors, error_summary)

        h.flash_success(_(u'Profile updated'))
        resp = h.redirect_to(u'user.read', id=user[u'name'])
        if current_user and data_dict[u'name'] != old_username:
            # Changing currently logged in user's name.
            # Update repoze.who cookie to match
            set_repoze_user(data_dict[u'name'], resp)
        return resp

    def get(self, id=None, data=None, errors=None, error_summary=None):
        context, id = self._prepare(id)
        data_dict = {u'id': id}
        try:
            old_data = logic.get_action(u'user_show')(context, data_dict)

            g.display_name = old_data.get(u'display_name')
            g.user_name = old_data.get(u'name')

            data = data or old_data

        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit user %s') % u'')
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        user_obj = context.get(u'user_obj')

        if not (authz.is_sysadmin(g.user) or g.user == user_obj.name):
            msg = _(u'User %s not authorized to edit %s') % (g.user, id)
            base.abort(403, msg)

        errors = errors or {}
        vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary
        }

        extra_vars = _extra_template_variables({
            u'model': model,
            u'session': model.Session,
            u'user': g.user
        }, data_dict)

        extra_vars[u'is_myself'] = True
        extra_vars[u'show_email_notifications'] = asbool(
            config.get(u'ckan.activity_streams_email_notifications'))
        vars.update(extra_vars)
        extra_vars[u'form'] = base.render(edit_user_form, extra_vars=vars)

        return base.render(u'user/edit.html', extra_vars)


class RegisterView(MethodView):
    def _prepare(self):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj,
            u'schema': _new_form_to_db_schema(),
            u'save': u'save' in request.form
        }
        try:
            logic.check_access(u'user_create', context)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to register as a user.'))
        return context

    def post(self):
        context = self._prepare()
        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))

        context[u'message'] = data_dict.get(u'log_message', u'')
        try:
            captcha.check_recaptcha(request)
        except captcha.CaptchaError:
            error_msg = _(u'Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.get(data_dict)

        try:
            logic.get_action(u'user_create')(context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to create user %s') % u'')
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict, errors, error_summary)

        if g.user:
            # #1799 User has managed to register whilst logged in - warn user
            # they are not re-logged in as new user.
            h.flash_success(
                _(u'User "%s" is now registered but you are still '
                  u'logged in as "%s" from before') % (data_dict[u'name'],
                                                       g.user))
            if authz.is_sysadmin(g.user):
                # the sysadmin created a new user. We redirect him to the
                # activity page for the newly created user
                return h.redirect_to(u'user.activity', id=data_dict[u'name'])
            else:
                return base.render(u'user/logout_first.html')

        # log the user in programatically
        resp = h.redirect_to(u'user.me')
        set_repoze_user(data_dict[u'name'], resp)
        return resp

    def get(self, data=None, errors=None, error_summary=None):
        self._prepare()

        if g.user and not data and not authz.is_sysadmin(g.user):
            # #1799 Don't offer the registration form if already logged in
            return base.render(u'user/logout_first.html', {})

        form_vars = {
            u'data': data or {},
            u'errors': errors or {},
            u'error_summary': error_summary or {}
        }

        extra_vars = {
            u'is_sysadmin': authz.is_sysadmin(g.user),
            u'form': base.render(new_user_form, form_vars)
        }
        return base.render(u'user/new.html', extra_vars)


def login():
    # Do any plugin login stuff
    for item in plugins.PluginImplementations(plugins.IAuthenticator):
        item.login()

    extra_vars = {}
    if g.user:
        return base.render(u'user/logout_first.html', extra_vars)

    came_from = request.params.get(u'came_from')
    if not came_from:
        came_from = h.url_for(u'user.logged_in')
    g.login_handler = h.url_for(
        _get_repoze_handler(u'login_handler_path'), came_from=came_from)
    return base.render(u'user/login.html', extra_vars)


def logged_in():
    # redirect if needed
    came_from = request.params.get(u'came_from', u'')
    if h.url_is_local(came_from):
        return h.redirect_to(str(came_from))

    if g.user:
        return me()
    else:
        err = _(u'Login failed. Bad username or password.')
        h.flash_error(err)
        return login()


def logout():
    # Do any plugin logout stuff
    for item in plugins.PluginImplementations(plugins.IAuthenticator):
        item.logout()
    url = h.url_for(u'user.logged_out_page')
    return h.redirect_to(
        _get_repoze_handler(u'logout_handler_path') + u'?came_from=' + url,
        parse_url=True)


def logged_out():
    # redirect if needed
    came_from = request.params.get(u'came_from', u'')
    if h.url_is_local(came_from):
        return h.redirect_to(str(came_from))
    return h.redirect_to(u'user.logged_out_page')


def logged_out_page():
    return base.render(u'user/logout.html', {})


def delete(id):
    u'''Delete user with id passed as parameter'''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id}

    try:
        logic.get_action(u'user_delete')(context, data_dict)
    except logic.NotAuthorized:
        msg = _(u'Unauthorized to delete user with id "{user_id}".')
        base.abort(403, msg.format(user_id=id))
    user_index = h.url_for(u'user.index')
    return h.redirect_to(user_index)


def generate_apikey(id=None):
    u'''Cycle the API key of a user'''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
    }
    if id is None:
        if g.userobj:
            id = g.userobj.id
        else:
            base.abort(400, _(u'No user specified'))
    data_dict = {u'id': id}

    try:
        result = logic.get_action(u'user_generate_apikey')(context, data_dict)
    except logic.NotAuthorized:
        base.abort(403, _(u'Unauthorized to edit user %s') % u'')
    except logic.NotFound:
        base.abort(404, _(u'User not found'))

    h.flash_success(_(u'Profile updated'))
    return h.redirect_to(u'user.read', id=result[u'name'])


def activity(id, offset=0):
    u'''Render this user's public activity stream page.'''

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    }
    data_dict = {
        u'id': id,
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }
    try:
        logic.check_access(u'user_show', context, data_dict)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    extra_vars = _extra_template_variables(context, data_dict)

    try:
        g.user_activity_stream = logic.get_action(u'user_activity_list_html')(
            context, {
                u'id': extra_vars[u'user_dict'][u'id'],
                u'offset': offset
            })
    except logic.ValidationError:
        base.abort(400)

    return base.render(u'user/activity_stream.html', extra_vars)


class RequestResetView(MethodView):
    def _prepare(self):
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        try:
            logic.check_access(u'request_reset', context)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to request reset password.'))

    def post(self):
        self._prepare()
        id = request.form.get(u'user')
        if id in (None, u''):
            h.flash_error(_(u'Email is required'))
            return h.redirect_to(u'/user/reset')
        log.info(u'Password reset requested for user "{}"'.format(id))

        context = {u'model': model, u'user': g.user, u'ignore_auth': True}
        user_objs = []

        # Usernames cannot contain '@' symbols
        if u'@' in id:
            # Search by email address
            # (You can forget a user id, but you don't tend to forget your
            # email)
            user_list = logic.get_action(u'user_list')(context, {
                u'email': id
            })
            if user_list:
                # send reset emails for *all* user accounts with this email
                # (otherwise we'd have to silently fail - we can't tell the
                # user, as that would reveal the existence of accounts with
                # this email address)
                for user_dict in user_list:
                    # This is ugly, but we need the user object for the mailer,
                    # and user_list does not return them
                    logic.get_action(u'user_show')(
                        context, {u'id': user_dict[u'id']})
                    user_objs.append(context[u'user_obj'])

        else:
            # Search by user name
            # (this is helpful as an option for a user who has multiple
            # accounts with the same email address and they want to be
            # specific)
            try:
                logic.get_action(u'user_show')(context, {u'id': id})
                user_objs.append(context[u'user_obj'])
            except logic.NotFound:
                pass

        if not user_objs:
            log.info(u'User requested reset link for unknown user: {}'
                     .format(id))

        for user_obj in user_objs:
            log.info(u'Emailing reset link to user: {}'
                     .format(user_obj.name))
            try:
                # FIXME: How about passing user.id instead? Mailer already
                # uses model and it allow to simplify code above
                mailer.send_reset_link(user_obj)
            except mailer.MailerException as e:
                # SMTP is not configured correctly or the server is
                # temporarily unavailable
                h.flash_error(_(u'Error sending the email. Try again later '
                                'or contact an administrator for help'))
                log.exception(e)
                return h.redirect_to(u'/')

        # always tell the user it succeeded, because otherwise we reveal
        # which accounts exist or not
        h.flash_success(
            _(u'A reset link has been emailed to you '
              '(unless the account specified does not exist)'))
        return h.redirect_to(u'/')

    def get(self):
        self._prepare()
        return base.render(u'user/request_reset.html', {})


class PerformResetView(MethodView):
    def _prepare(self, id):
        # FIXME 403 error for invalid key is a non helpful page
        context = {
            u'model': model,
            u'session': model.Session,
            u'user': id,
            u'keep_email': True
        }

        try:
            logic.check_access(u'user_reset', context)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to reset password.'))

        try:
            user_dict = logic.get_action(u'user_show')(context, {u'id': id})
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        user_obj = context[u'user_obj']
        g.reset_key = request.params.get(u'key')
        if not mailer.verify_reset_link(user_obj, g.reset_key):
            msg = _(u'Invalid reset key. Please try again.')
            h.flash_error(msg)
            base.abort(403, msg)
        return context, user_dict

    def _get_form_password(self):
        password1 = request.form.get(u'password1')
        password2 = request.form.get(u'password2')
        if (password1 is not None and password1 != u''):
            if len(password1) < 8:
                raise ValueError(
                    _(u'Your password must be 8 '
                      u'characters or longer.'))
            elif password1 != password2:
                raise ValueError(
                    _(u'The passwords you entered'
                      u' do not match.'))
            return password1
        msg = _(u'You must provide a password')
        raise ValueError(msg)

    def post(self, id):
        context, user_dict = self._prepare(id)
        context[u'reset_password'] = True
        user_state = user_dict[u'state']
        try:
            new_password = self._get_form_password()
            user_dict[u'password'] = new_password
            username = request.form.get(u'name')
            if (username is not None and username != u''):
                user_dict[u'name'] = username
            user_dict[u'reset_key'] = g.reset_key
            user_dict[u'state'] = model.State.ACTIVE
            logic.get_action(u'user_update')(context, user_dict)
            mailer.create_reset_key(context[u'user_obj'])

            h.flash_success(_(u'Your password has been reset.'))
            return h.redirect_to(u'home.index')
        except logic.NotAuthorized:
            h.flash_error(_(u'Unauthorized to edit user %s') % id)
        except logic.NotFound:
            h.flash_error(_(u'User not found'))
        except dictization_functions.DataError:
            h.flash_error(_(u'Integrity Error'))
        except logic.ValidationError as e:
            h.flash_error(u'%r' % e.error_dict)
        except ValueError as e:
            h.flash_error(text_type(e))
        user_dict[u'state'] = user_state
        return base.render(u'user/perform_reset.html', {
            u'user_dict': user_dict
        })

    def get(self, id):
        context, user_dict = self._prepare(id)
        return base.render(u'user/perform_reset.html', {
            u'user_dict': user_dict
        })


def follow(id):
    u'''Start following this user.'''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id, u'include_num_followers': True}
    try:
        logic.get_action(u'follow_user')(context, data_dict)
        user_dict = logic.get_action(u'user_show')(context, data_dict)
        h.flash_success(
            _(u'You are now following {0}').format(user_dict[u'display_name']))
    except logic.ValidationError as e:
        error_message = (e.message or e.error_summary or e.error_dict)
        h.flash_error(error_message)
    except logic.NotAuthorized as e:
        h.flash_error(e.message)
    return h.redirect_to(u'user.read', id=id)


def unfollow(id):
    u'''Stop following this user.'''
    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj
    }
    data_dict = {u'id': id, u'include_num_followers': True}
    try:
        logic.get_action(u'unfollow_user')(context, data_dict)
        user_dict = logic.get_action(u'user_show')(context, data_dict)
        h.flash_success(
            _(u'You are no longer following {0}').format(
                user_dict[u'display_name']))
    except (logic.NotFound, logic.NotAuthorized) as e:
        error_message = e.message
        h.flash_error(error_message)
    except logic.ValidationError as e:
        error_message = (e.error_summary or e.message or e.error_dict)
        h.flash_error(error_message)
    return h.redirect_to(u'user.read', id=id)


def followers(id):
    context = {u'for_view': True, u'user': g.user, u'auth_user_obj': g.userobj}
    data_dict = {
        u'id': id,
        u'user_obj': g.userobj,
        u'include_num_followers': True
    }
    extra_vars = _extra_template_variables(context, data_dict)
    f = logic.get_action(u'user_follower_list')
    try:
        extra_vars[u'followers'] = f(context, {
            u'id': extra_vars[u'user_dict'][u'id']
        })
    except logic.NotAuthorized:
        base.abort(403, _(u'Unauthorized to view followers %s') % u'')
    return base.render(u'user/followers.html', extra_vars)


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

user.add_url_rule(u'/delete/<id>', view_func=delete, methods=(u'POST', ))

user.add_url_rule(
    u'/generate_key', view_func=generate_apikey, methods=(u'POST', ))
user.add_url_rule(
    u'/generate_key/<id>', view_func=generate_apikey, methods=(u'POST', ))

user.add_url_rule(u'/activity/<id>', view_func=activity)
user.add_url_rule(u'/activity/<id>/<int:offset>', view_func=activity)

user.add_url_rule(
    u'/reset', view_func=RequestResetView.as_view(str(u'request_reset')))
user.add_url_rule(
    u'/reset/<id>', view_func=PerformResetView.as_view(str(u'perform_reset')))

user.add_url_rule(u'/follow/<id>', view_func=follow, methods=(u'POST', ))
user.add_url_rule(u'/unfollow/<id>', view_func=unfollow, methods=(u'POST', ))
user.add_url_rule(u'/followers/<id>', view_func=followers)

user.add_url_rule(u'/<id>', view_func=read)
