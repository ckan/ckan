# encoding: utf-8

from sqlalchemy import inspect
from ckan.common import asbool
import six
from six import text_type
from six.moves.urllib.parse import quote
from werkzeug.utils import import_string, cached_property

import ckan.model as model
import ckan.lib.api_token as api_token
from ckan.common import g, request, config, session
from ckan.lib.helpers import redirect_to as redirect
from ckan.lib.i18n import get_locales_from_config
import ckan.plugins as p

import logging
log = logging.getLogger(__name__)

APIKEY_HEADER_NAME_KEY = 'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = 'X-CKAN-API-Key'


class LazyView(object):

    def __init__(self, import_name, view_name=None):
        self.__module__, self.__name__ = import_name.rsplit('.', 1)
        self.import_name = import_name
        self.view_name = view_name

    @cached_property
    def view(self):
        actual_view = import_string(self.import_name)
        if self.view_name:
            actual_view = actual_view.as_view(self.view_name)
        return actual_view

    def __call__(self, *args, **kwargs):
        return self.view(*args, **kwargs)


def check_session_cookie(response):
    '''
    The cookies for auth (auth_tkt) and session (ckan) are separate. This
    checks whether a user is logged in, and determines the validity of the
    session cookie, removing it if necessary.
    '''
    for cookie in request.cookies:
        # Remove the ckan session cookie if logged out.
        if cookie == 'ckan' and not getattr(g, 'user', None):
            # Check session for valid data (including flash messages)
            is_valid_cookie_data = False
            for key, value in session.items():
                if not key.startswith('_') and value:
                    is_valid_cookie_data = True
                    break
            if not is_valid_cookie_data:
                if session.id:
                    log.debug('No valid session data - deleting session')
                    log.debug('Session: %r', session.items())
                    session.delete()
                else:
                    log.debug('No session id - deleting session cookie')
                    response.delete_cookie(cookie)
        # Remove auth_tkt repoze.who cookie if user not logged in.
        elif cookie == 'auth_tkt' and not session.id:
            response.delete_cookie(cookie)

    return response


def set_cors_headers_for_response(response):
    '''
    Set up Access Control Allow headers if either origin_allow_all is True, or
    the request Origin is in the origin_whitelist.
    '''
    if config.get('ckan.cors.origin_allow_all') \
       and request.headers.get('Origin'):

        cors_origin_allowed = None
        if asbool(config.get('ckan.cors.origin_allow_all')):
            cors_origin_allowed = b'*'
        elif config.get('ckan.cors.origin_whitelist') and \
                request.headers.get('Origin') \
                in config['ckan.cors.origin_whitelist'].split(' '):
            # set var to the origin to allow it.
            cors_origin_allowed = request.headers.get('Origin')

        if cors_origin_allowed is not None:
            response.headers[b'Access-Control-Allow-Origin'] = \
                cors_origin_allowed
            response.headers[b'Access-Control-Allow-Methods'] = \
                b'POST, PUT, GET, DELETE, OPTIONS'
            response.headers[b'Access-Control-Allow-Headers'] = \
                b'X-CKAN-API-KEY, Authorization, Content-Type'

    return response


def set_cache_control_headers_for_response(response):

    # __no_cache__ should not be present when caching is allowed
    allow_cache = '__no_cache__' not in request.environ

    if 'Pragma' in response.headers:
        del response.headers["Pragma"]

    if allow_cache:
        response.cache_control.public = True
        try:
            cache_expire = int(config.get('ckan.cache_expires', 0))
            response.cache_control.max_age = cache_expire
            response.cache_control.must_revalidate = True
        except ValueError:
            pass
    else:
        response.cache_control.private = True

    return response


def identify_user():
    '''Try to identify the user
    If the user is identified then:
      g.user = user name (unicode)
      g.userobj = user object
      g.author = user name
    otherwise:
      g.user = None
      g.userobj = None
      g.author = user's IP address (unicode)

    Note: Remember, when running under Pylons, `g` is the Pylons `c` object
    '''
    # see if it was proxied first
    g.remote_addr = request.environ.get('HTTP_X_FORWARDED_FOR', '')
    if not g.remote_addr:
        g.remote_addr = request.environ.get('REMOTE_ADDR',
                                            'Unknown IP Address')

    # Authentication plugins get a chance to run here break as soon as a user
    # is identified or a response is returned
    authenticators = p.PluginImplementations(p.IAuthenticator)
    if authenticators:
        for item in authenticators:
            response = item.identify()
            if response:
                return response
            try:
                if g.user:
                    break
            except AttributeError:
                continue

    # We haven't identified the user so try the default methods
    if not getattr(g, 'user', None):
        _identify_user_default()

    # If we have a user but not the userobj let's get the userobj. This means
    # that IAuthenticator extensions do not need to access the user model
    # directly.
    if g.user:
        if not getattr(g, 'userobj', None) or inspect(g.userobj).expired:
            g.userobj = model.User.by_name(g.user)

    # general settings
    if g.user:
        g.author = g.user
    else:
        g.author = g.remote_addr
    g.author = text_type(g.author)


def _identify_user_default():
    '''
    Identifies the user using two methods:
    a) If they logged into the web interface then repoze.who will
       set REMOTE_USER.
    b) For API calls they may set a header with an API key.
    '''

    # environ['REMOTE_USER'] is set by repoze.who if it authenticates a
    # user's cookie. But repoze.who doesn't check the user (still) exists
    # in our database - we need to do that here. (Another way would be
    # with an userid_checker, but that would mean another db access.
    # See: http://docs.repoze.org/who/1.0/narr.html#module-repoze.who\
    # .plugins.sql )
    g.user = six.ensure_text(request.environ.get('REMOTE_USER', ''))
    if g.user:
        g.userobj = model.User.by_name(g.user)

        if g.userobj is None or not g.userobj.is_active():

            # This occurs when a user that was still logged in is deleted, or
            # when you are logged in, clean db and then restart (or when you
            # change your username). There is no user object, so even though
            # repoze thinks you are logged in and your cookie has
            # ckan_display_name, we need to force user to logout and login
            # again to get the User object.

            ev = request.environ
            if 'repoze.who.plugins' in ev:
                pth = getattr(ev['repoze.who.plugins']['friendlyform'],
                              'logout_handler_path')
                redirect(pth)
    else:
        g.userobj = _get_user_for_apikey()
        if g.userobj is not None:
            g.user = g.userobj.name


def _get_user_for_apikey():
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
    apikey = six.ensure_text(apikey, errors="ignore")
    log.debug('Received API Key: %s' % apikey)
    query = model.Session.query(model.User)
    user = query.filter_by(apikey=apikey).first()

    if not user:
        user = api_token.get_user_from_token(apikey)
    return user


def set_controller_and_action():
    g.controller, g.action = p.toolkit.get_endpoint()


def handle_i18n(environ=None):
    '''
    Strips the locale code from the requested url
    (eg '/sk/about' -> '/about') and sets environ variables for the
    language selected:

        * CKAN_LANG is the language code eg en, fr
        * CKAN_LANG_IS_DEFAULT is set to True or False
        * CKAN_CURRENT_URL is set to the current application url
    '''
    environ = environ or request.environ
    locale_list = get_locales_from_config()
    default_locale = config.get('ckan.locale_default', 'en')

    # We only update once for a request so we can keep
    # the language and original url which helps with 404 pages etc
    if 'CKAN_LANG' not in environ:
        path_parts = environ['PATH_INFO'].split('/')
        if len(path_parts) > 1 and path_parts[1] in locale_list:
            environ['CKAN_LANG'] = path_parts[1]
            environ['CKAN_LANG_IS_DEFAULT'] = False
            # rewrite url
            if len(path_parts) > 2:
                environ['PATH_INFO'] = '/'.join([''] + path_parts[2:])
            else:
                environ['PATH_INFO'] = '/'
        else:
            environ['CKAN_LANG'] = default_locale
            environ['CKAN_LANG_IS_DEFAULT'] = True

        set_ckan_current_url(environ)


def set_ckan_current_url(environ):
    # Current application url
    path_info = environ['PATH_INFO']
    # sort out weird encodings
    path_info = \
        '/'.join(quote(pce, '') for pce in path_info.split('/'))

    qs = environ.get('QUERY_STRING')
    if qs:
        # sort out weird encodings
        qs = quote(qs, '')
        environ['CKAN_CURRENT_URL'] = '%s?%s' % (path_info, qs)
    else:
        environ['CKAN_CURRENT_URL'] = path_info
