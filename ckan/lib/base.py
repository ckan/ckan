"""The base Controller API

Provides the BaseController class for subclassing.
"""
from datetime import datetime
from hashlib import md5
import logging
import os
import urllib

from paste.deploy.converters import asbool
from pylons import c, cache, config, g, request, response, session
from pylons.controllers import WSGIController
from pylons.controllers.util import abort as _abort
from pylons.controllers.util import redirect_to, redirect
from pylons.decorators import jsonify, validate
from pylons.i18n import _, ungettext, N_, gettext
from pylons.templating import cached_template, pylons_globals
from genshi.template import MarkupTemplate
from genshi.template.text import NewTextTemplate
from webhelpers.html import literal

import ckan.exceptions
import ckan
import ckan.authz as authz
from ckan.lib import i18n
import ckan.lib.helpers as h
from ckan.plugins import PluginImplementations, IGenshiStreamFilter
from ckan.lib.helpers import json
import ckan.model as model

log = logging.getLogger(__name__)

PAGINATE_ITEMS_PER_PAGE = 50

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'

ALLOWED_FIELDSET_PARAMS = ['package_form', 'restrict']


def abort(status_code=None, detail='', headers=None, comment=None):
    if detail and status_code != 503:
        h.flash_error(detail)
    # #1267 Convert detail to plain text, since WebOb 0.9.7.1 (which comes
    # with Lucid) causes an exception when unicode is received.
    detail = detail.encode('utf8')
    return _abort(status_code=status_code,
                  detail=detail,
                  headers=headers,
                  comment=comment)


def render_snippet(template_name, **kw):
    ''' Helper function for rendering snippets. Rendered html has
    comment tags added to show the template used. NOTE: unlike other
    render functions this takes a list of keywords instead of a dict for
    the extra template variables. '''
    # allow cache_force to be set in render function
    cache_force = kw.pop('cache_force', None)
    output = render(template_name, extra_vars=kw, cache_force=cache_force)
    output = '\n<!-- Snippet %s start -->\n%s\n<!-- Snippet %s end -->\n' % (
        template_name, output, template_name)
    return literal(output)


def render_text(template_name, extra_vars=None, cache_force=None):
    ''' Helper function to render a genshi NewTextTemplate without
    having to pass the loader_class or method. '''
    return render(template_name,
                  extra_vars=extra_vars,
                  cache_force=cache_force,
                  method='text',
                  loader_class=NewTextTemplate)


def render(template_name, extra_vars=None, cache_key=None, cache_type=None,
           cache_expire=None, method='xhtml', loader_class=MarkupTemplate,
           cache_force=None):
    ''' Main genshi template rendering function. '''

    def render_template():
        globs = extra_vars or {}
        globs.update(pylons_globals())
        globs['actions'] = model.Action
        # add the template name to the context to help us know where we are
        # used in depreciating functions etc
        c.__template_name = template_name

        # Using pylons.url() directly destroys the localisation stuff so
        # we remove it so any bad templates crash and burn
        del globs['url']

        template = globs['app_globals'].genshi_loader.load(template_name,
                                                           cls=loader_class)
        stream = template.generate(**globs)

        for item in PluginImplementations(IGenshiStreamFilter):
            stream = item.filter(stream)

        if loader_class == NewTextTemplate:
            return literal(stream.render(method="text", encoding=None))

        return literal(stream.render(method=method, encoding=None,
                                     strip_whitespace=True))

    if 'Pragma' in response.headers:
        del response.headers["Pragma"]

    ## Caching Logic
    allow_cache = True
    # Force cache or not if explicit.
    if cache_force is not None:
        allow_cache = cache_force
    # Do not allow caching of pages for logged in users/flash messages etc.
    elif session.last_accessed:
        allow_cache = False
    # Tests etc.
    elif 'REMOTE_USER' in request.environ:
        allow_cache = False
    # Don't cache if based on a non-cachable template used in this.
    elif request.environ.get('__no_cache__'):
        allow_cache = False
    # Don't cache if we have set the __no_cache__ param in the query string.
    elif request.params.get('__no_cache__'):
        allow_cache = False
    # Don't cache if we have extra vars containing data.
    elif extra_vars:
        for k, v in extra_vars.iteritems():
            allow_cache = False
            break
    # Record cachability for the page cache if enabled
    request.environ['CKAN_PAGE_CACHABLE'] = allow_cache

    if allow_cache:
        response.headers["Cache-Control"] = "public"
        try:
            cache_expire = int(config.get('ckan.cache_expires', 0))
            response.headers["Cache-Control"] += \
                ", max-age=%s, must-revalidate" % cache_expire
        except ValueError:
            pass
    else:
        # We do not want caching.
        response.headers["Cache-Control"] = "private"
        # Prevent any further rendering from being cached.
        request.environ['__no_cache__'] = True
    log.debug('Template cache-control: %s' % response.headers["Cache-Control"])

    # Render Time :)
    try:
        return cached_template(template_name, render_template,
                               loader_class=loader_class)
    except ckan.exceptions.CkanUrlException, e:
        raise ckan.exceptions.CkanUrlException(
            '\nAn Exception has been raised for template %s\n%s' %
            (template_name, e.message))


class ValidationException(Exception):
    pass


class BaseController(WSGIController):
    repo = model.repo
    authorizer = authz.Authorizer()
    log = logging.getLogger(__name__)

    def __before__(self, action, **params):
        c.__version__ = ckan.__version__
        self._identify_user()
        i18n.handle_request(request, c)

    def _identify_user(self):
        '''
        Identifies the user using two methods:
        a) If he has logged into the web interface then repoze.who will
           set REMOTE_USER.
        b) For API calls he may set a header with his API key.
        If the user is identified then:
          c.user = user name (unicode)
          c.userobj = user object
          c.author = user name
        otherwise:
          c.user = None
          c.userobj = None
          c.author = user\'s IP address (unicode)
        '''
        # see if it was proxied first
        c.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR', '')
        if not c.remote_addr:
            c.remote_addr = request.environ.get('REMOTE_ADDR',
                                                'Unknown IP Address')

        # environ['REMOTE_USER'] is set by repoze.who if it authenticates
        # a user's cookie or OpenID. But repoze.who doesn't check the user
        # (still) exists in our database - we need to do that here. (Another
        # way would be with an userid_checker, but that would mean another db
        # access.
        # See: http://docs.repoze.org/who/1.0/narr.html#module-repoze.who\
        # .plugins.sql )
        c.user = request.environ.get('REMOTE_USER', '')
        if c.user:
            c.user = c.user.decode('utf8')
            c.userobj = model.User.by_name(c.user)
            if c.userobj is None:
                # This occurs when you are logged in, clean db
                # and then restart (or when you change your username)
                # There is no user object, so even though repoze thinks you
                # are logged in and your cookie has ckan_display_name, we
                # need to force user to logout and login again to get the
                # User object.
                session['lang'] = request.environ.get('CKAN_LANG')
                session.save()

                ev = request.environ
                if 'repoze.who.plugins' in ev:
                    pth = getattr(ev['repoze.who.plugins']['friendlyform'],
                                  'logout_handler_path')
                    h.redirect_to(pth)
        else:
            c.userobj = self._get_user_for_apikey()
            if c.userobj is not None:
                c.user = c.userobj.name
        if c.user:
            c.author = c.user
        else:
            c.author = c.remote_addr
        c.author = unicode(c.author)

    def __call__(self, environ, start_response):
        """Invoke the Controller"""
        # WSGIController.__call__ dispatches to the Controller method
        # the request is routed to. This routing information is
        # available in environ['pylons.routes_dict']

        try:
            res = WSGIController.__call__(self, environ, start_response)
        finally:
            model.Session.remove()

        # Clean out any old cookies as they may contain api keys etc
        # This also improves the cachability of our pages as cookies
        # prevent proxy servers from caching content unless they have
        # been configured to ignore them.
        for cookie in request.cookies:
            if cookie.startswith('ckan') and cookie not in ['ckan']:
                response.delete_cookie(cookie)
            # Remove the ckan session cookie if not used e.g. logged out
            elif cookie == 'ckan' and not c.user:
                # Check session for valid data (including flash messages)
                # (DGU also uses session for a shopping basket-type behaviour)
                is_valid_cookie_data = False
                for key, value in session.items():
                    if not key.startswith('_') and value:
                        is_valid_cookie_data = True
                        break
                if not is_valid_cookie_data:
                    if session.id:
                        if not session.get('lang'):
                            self.log.debug('No session data any more - '
                                           'deleting session')
                            self.log.debug('Session: %r', session.items())
                            session.delete()
                    else:
                        response.delete_cookie(cookie)
                        self.log.debug('No session data any more - '
                                       'deleting session cookie')
            # Remove auth_tkt repoze.who cookie if user not logged in.
            elif cookie == 'auth_tkt' and not session.id:
                response.delete_cookie(cookie)

        return res

    def __after__(self, action, **params):
        self._set_cors()

    def _set_cors(self):
        response.headers['Access-Control-Allow-Origin'] = "*"
        response.headers['Access-Control-Allow-Methods'] = \
            "POST, PUT, GET, DELETE, OPTIONS"
        response.headers['Access-Control-Allow-Headers'] = \
            "X-CKAN-API-KEY, Authorization, Content-Type"

    def _get_user(self, reference):
        return model.User.by_name(reference)

    def _get_pkg(self, reference):
        return model.Package.get(reference)

    def _get_group(self, reference):
        return model.Group.get(reference)

    def _get_tag(self, reference):
        return model.Tag.get(reference)

    @classmethod
    def _get_request_data(cls, try_url_params=False):
        '''Returns a dictionary, extracted from a request.

        If there is no data, None or "" is returned.
        ValueError will be raised if the data is not a JSON-formatted dict.

        The data is retrieved as a JSON-encoded dictionary from the request
        body.  Or, if the `try_url_params` argument is True and the request is
        a GET request, then an attempt is made to read the data from the url
        parameters of the request.

        try_url_params
            If try_url_params is False, then the data_dict is read from the
            request body.

            If try_url_params is True and the request is a GET request then the
            data is read from the url parameters.  The resulting dict will only
            be 1 level deep, with the url-param fields being the keys.  If a
            single key has more than one value specified, then the value will
            be a list of strings, otherwise just a string.

        This function is only used by the API, so no strings need to be
        translated.

        TODO: If this is only used by the API, then perhaps it should be
              moved to the api controller class?
        '''
        cls.log.debug('Retrieving request params: %r' % request.params)
        cls.log.debug('Retrieving request POST: %r' % request.POST)
        cls.log.debug('Retrieving request GET: %r' % request.GET)
        request_data = None
        if request.POST:
            try:
                keys = request.POST.keys()
                # Parsing breaks if there is a = in the value, so for now
                # we will check if the data is actually all in a single key
                if keys and request.POST[keys[0]] in [u'1', u'']:
                    request_data = keys[0]
                else:
                    request_data = urllib.unquote_plus(request.body)
            except Exception, inst:
                msg = "Could not find the POST data: %r : %s" % \
                      (request.POST, inst)
                raise ValueError(msg)

        elif try_url_params and request.GET:
            return request.GET.mixed()

        else:
            try:
                if request.method in ['POST', 'PUT']:
                    request_data = request.body
                else:
                    request_data = None
            except Exception, inst:
                msg = "Could not extract request body data: %s" % \
                      (inst)
                raise ValueError(msg)
            cls.log.debug('Retrieved request body: %r' % request.body)
            if not request_data:
                msg = "No request body data"
                raise ValueError(msg)
        if request_data:
            try:
                request_data = json.loads(request_data, encoding='utf8')
            except ValueError, e:
                raise ValueError('Error decoding JSON data. '
                                 'Error: %r '
                                 'JSON data extracted from the request: %r' %
                                 (e, request_data))
            if not isinstance(request_data, dict):
                raise ValueError('Request data JSON decoded to %r but '
                                 'it needs to be a dictionary.' % request_data)
            # ensure unicode values
            for key, val in request_data.items():
                # if val is str then assume it is ascii, since json converts
                # utf8 encoded JSON to unicode
                request_data[key] = cls._make_unicode(val)
        cls.log.debug('Request data extracted: %r' % request_data)
        return request_data

    @classmethod
    def _make_unicode(cls, entity):
        """Cast bare strings and strings in lists or dicts to Unicode
        """
        if isinstance(entity, str):
            return unicode(entity)
        elif isinstance(entity, list):
            new_items = []
            for item in entity:
                new_items.append(cls._make_unicode(item))
            return new_items
        elif isinstance(entity, dict):
            new_dict = {}
            for key, val in entity.items():
                new_dict[key] = cls._make_unicode(val)
            return new_dict
        else:
            return entity

    def _get_user_for_apikey(self):
        apikey_header_name = config.get(APIKEY_HEADER_NAME_KEY,
                                        APIKEY_HEADER_NAME_DEFAULT)
        apikey = request.headers.get(apikey_header_name, '')
        if not apikey:
            apikey = request.environ.get(apikey_header_name, '')
        if not apikey:
            # For misunderstanding old documentation (now fixed).
            apikey = request.environ.get('HTTP_AUTHORIZATION', '')
        if not apikey:
            apikey = request.environ.get('Authorization', '')
            # Forget HTTP Auth credentials (they have spaces).
            if ' ' in apikey:
                apikey = ''
        if not apikey:
            return None
        self.log.debug("Received API Key: %s" % apikey)
        apikey = unicode(apikey)
        query = model.Session.query(model.User)
        user = query.filter_by(apikey=apikey).first()
        return user

    def _get_timing_cache_path(self):

        return path

    @classmethod
    def _get_user_editable_groups(cls):
        if not hasattr(c, 'user'):
            c.user = model.PSEUDO_USER__VISITOR
        import ckan.authz   # Todo: Move import to top of this file?
        groups = ckan.authz.Authorizer.authorized_query(
            c.user, model.Group, action=model.Action.EDIT).all()
        return [g for g in groups if g.state == model.State.ACTIVE]

    def _get_package_dict(self, *args, **kwds):
        import ckan.forms
        user_editable_groups = self._get_user_editable_groups()
        package_dict = ckan.forms.get_package_dict(
            user_editable_groups=user_editable_groups,
            *args, **kwds
        )
        return package_dict

    def _edit_package_dict(self, *args, **kwds):
        import ckan.forms
        return ckan.forms.edit_package_dict(*args, **kwds)

    @classmethod
    def _get_package_fieldset(cls, is_admin=False, **kwds):
        kwds.update(request.params)
        kwds['user_editable_groups'] = cls._get_user_editable_groups()
        kwds['is_admin'] = is_admin
        from ckan.forms import GetPackageFieldset
        return GetPackageFieldset(**kwds).fieldset

    def _get_standard_package_fieldset(self):
        import ckan.forms
        user_editable_groups = self._get_user_editable_groups()
        fieldset = ckan.forms.get_standard_fieldset(
            user_editable_groups=user_editable_groups
        )
        return fieldset

    def _handle_update_of_authz(self, domain_object):
        '''In the event of a post request to a domain object\'s authz form,
        work out which of the four possible actions is to be done,
        and do it before displaying the page.

        Returns the updated roles for the domain_object.
        '''
        from ckan.logic import NotFound, get_action

        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author}
        data_dict = {'domain_object': domain_object.id}

        # Work out actions needed, depending on which button was pressed
        if 'save' in request.POST:
            user_or_authgroup = 'user'
            update_or_add = 'update'
        elif 'add' in request.POST:
            user_or_authgroup = 'user'
            update_or_add = 'add'
        elif 'authz_save' in request.POST:
            user_or_authgroup = 'authorization_group'
            update_or_add = 'update'
        elif 'authz_add' in request.POST:
            user_or_authgroup = 'authorization_group'
            update_or_add = 'add'
        else:
            user_or_authgroup = None
            update_or_add = None

        # Work out what role checkboxes are checked or unchecked
        checked_roles = [box_id for (box_id, value) in request.params.items()
                         if (value == u'on')]
        unchecked_roles = [box_id for (box_id, value) in request.params.items()
                           if (value == u'submitted')]

        action = None
        if update_or_add is 'update':
            # Get user_roles by decoding the checkbox grid - user$role strings
            user_roles = {}
            for checked_role in checked_roles:
                user_or_authgroup_id, role = checked_role.split('$')
                if user_or_authgroup_id not in user_roles:
                    user_roles[user_or_authgroup_id] = []
                user_roles[user_or_authgroup_id].append(role)
            # Users without roles need adding to the user_roles too to make
            # their roles be deleted
            for unchecked_role in unchecked_roles:
                user_or_authgroup_id, role = unchecked_role.split('$')
                if user_or_authgroup_id not in user_roles:
                    user_roles[user_or_authgroup_id] = []
            # Convert user_roles to role dictionaries
            role_dicts = []
            for user, roles in user_roles.items():
                role_dicts.append({user_or_authgroup: user, 'roles': roles})
            data_dict['user_roles'] = role_dicts

            action = 'user_role_bulk_update'
            success_message = _('Updated')
        elif update_or_add is 'add':
            # Roles for this new user is a simple list from the checkbox row
            data_dict['roles'] = checked_roles

            # User (or "user group" aka AuthorizationGroup) comes from
            # the input box.
            new_user = request.params.get('new_user_name')
            if new_user:
                data_dict[user_or_authgroup] = new_user

                action = 'user_role_update'
                success_message = _('User role(s) added')
            else:
                h.flash_error(_('Please supply a user name'))

        if action:
            try:
                roles = get_action(action)(context, data_dict)
            except NotFound, e:
                h.flash_error(_('Not found') + (': %s' % e if str(e) else ''))
            else:
                h.flash_success(success_message)

        # Return roles for all users on this domain object
        if update_or_add is 'add':
            if user_or_authgroup in data_dict:
                del data_dict[user_or_authgroup]
        return get_action('roles_show')(context, data_dict)

    def _prepare_authz_info_for_render(self, user_object_roles):
        # =================
        # Display the page

        # Find out all the possible roles. At the moment, any role can be
        # associated with any object, so that's easy:
        possible_roles = model.Role.get_all()

        # uniquify and sort
        users = sorted(list(set([uor['user_id']
                                 for uor in user_object_roles['roles']
                                 if uor['user_id']])))
        authz_groups = sorted(list(set([uor['authorized_group_id']
                                        for uor in user_object_roles['roles']
                                        if uor['authorized_group_id']])))

        # make a dictionary from (user, role) to True, False
        users_roles = [(uor['user_id'], uor['role'])
                       for uor in user_object_roles['roles']
                       if uor['user_id']]
        user_role_dict = {}
        for u in users:
            for r in possible_roles:
                user_role_dict[(u, r)] = (u, r) in users_roles

        # and similarly make a dictionary from (authz_group, role) to True
        # , False
        authz_groups_roles = [(uor['authorized_group_id'], uor['role'])
                              for uor in user_object_roles['roles']
                              if uor['authorized_group_id']]
        authz_groups_role_dict = {}
        for u in authz_groups:
            for r in possible_roles:
                if (u, r) in authz_groups_roles:
                    authz_groups_role_dict[(u, r)] = True
                else:
                    authz_groups_role_dict[(u, r)] = False

        c.roles = possible_roles
        c.users = users
        c.user_role_dict = user_role_dict
        c.authz_groups = authz_groups
        c.authz_groups_role_dict = authz_groups_role_dict
        c.are_any_authz_groups = bool(model.Session.query(
            model.AuthorizationGroup).count())

# Include the '_' function in the public names
__all__ = [__name for __name in locals().keys() if not __name.startswith('_')
           or __name == '_']
