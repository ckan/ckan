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

APIKEY_HEADER_NAME_KEY = u'apikey_header_name'
APIKEY_HEADER_NAME_DEFAULT = u'X-CKAN-API-Key'


class LazyView(object):

    def __init__(self, import_name, view_name=None):
        self.__module__, self.__name__ = import_name.rsplit(u'.', 1)
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
    u'''
    The cookies for auth (auth_tkt) and session (ckan) are separate. This
    checks whether a user is logged in, and determines the validity of the
    session cookie, removing it if necessary.
    '''
    for cookie in request.cookies:
        # Remove the ckan session cookie if logged out.
        if cookie == u'ckan' and not getattr(g, u'user', None):
            # Check session for valid data (including flash messages)
            is_valid_cookie_data = False
            for key, value in session.items():
                if not key.startswith(u'_') and value:
                    is_valid_cookie_data = True
                    break
            if not is_valid_cookie_data:
                if session.id:
                    log.debug(u'No valid session data - deleting session')
                    log.debug(u'Session: %r', session.items())
                    session.delete()
                else:
                    log.debug(u'No session id - deleting session cookie')
                    response.delete_cookie(cookie)
        # Remove auth_tkt repoze.who cookie if user not logged in.
        elif cookie == u'auth_tkt' and not session.id:
            response.delete_cookie(cookie)

    return response


def set_cors_headers_for_response(response):
    u'''
    Set up Access Control Allow headers if either origin_allow_all is True, or
    the request Origin is in the origin_whitelist.
    '''
    if config.get(u'ckan.cors.origin_allow_all') \
       and request.headers.get(u'Origin'):

        cors_origin_allowed = None
        if asbool(config.get(u'ckan.cors.origin_allow_all')):
            cors_origin_allowed = b'*'
        elif config.get(u'ckan.cors.origin_whitelist') and \
                request.headers.get(u'Origin') \
                in config[u'ckan.cors.origin_whitelist'].split(u' '):
            # set var to the origin to allow it.
            cors_origin_allowed = request.headers.get(u'Origin')

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
    allow_cache = u'__no_cache__' not in request.environ

    if u'Pragma' in response.headers:
        del response.headers["Pragma"]

    if allow_cache:
        response.cache_control.public = True
        try:
            cache_expire = int(config.get(u'ckan.cache_expires', 0))
            response.cache_control.max_age = cache_expire
            response.cache_control.must_revalidate = True
        except ValueError:
            pass
    else:
        response.cache_control.private = True

    return response


def identify_user():
    u'''Try to identify the user
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
    g.remote_addr = request.environ.get(u'HTTP_X_FORWARDED_FOR', u'')
    if not g.remote_addr:
        g.remote_addr = request.environ.get(u'REMOTE_ADDR',
                                            u'Unknown IP Address')

    # Authentication plugins get a chance to run here break as soon as a user
    # is identified.

    authenticators = p.PluginImplementations(p.IAuthenticator)
    if authenticators:
        for item in authenticators:
            item.identify()
            try:
                if g.user:
                    break
            except AttributeError:
                continue

    # We haven't identified the user so try the default methods
    if not getattr(g, u'user', None):
        _identify_user_default()

    # If we have a user but not the userobj let's get the userobj. This means
    # that IAuthenticator extensions do not need to access the user model
    # directly.
    if g.user:
        if not getattr(g, u'userobj', None) or inspect(g.userobj).expired:
            g.userobj = model.User.by_name(g.user)

    # general settings
    if g.user:
        g.author = g.user
    else:
        g.author = g.remote_addr
    g.author = text_type(g.author)


def _identify_user_default():
    u'''
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
    g.user = six.ensure_text(request.environ.get(u'REMOTE_USER', u''))
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
            if u'repoze.who.plugins' in ev:
                pth = getattr(ev[u'repoze.who.plugins'][u'friendlyform'],
                              u'logout_handler_path')
                redirect(pth)
    else:
        g.userobj = _get_user_for_apikey()
        if g.userobj is not None:
            g.user = g.userobj.name


def _get_user_for_apikey():
    apikey_header_name = config.get(APIKEY_HEADER_NAME_KEY,
                                    APIKEY_HEADER_NAME_DEFAULT)
    apikey = request.headers.get(apikey_header_name, u'')
    if not apikey:
        apikey = request.environ.get(apikey_header_name, u'')
    if not apikey:
        # For misunderstanding old documentation (now fixed).
        apikey = request.environ.get(u'HTTP_AUTHORIZATION', u'')
    if not apikey:
        apikey = request.environ.get(u'Authorization', u'')
        # Forget HTTP Auth credentials (they have spaces).
        if u' ' in apikey:
            apikey = u''
    if not apikey:
        return None
    apikey = six.ensure_text(apikey, errors=u"ignore")
    log.debug(u'Received API Key: %s' % apikey)
    query = model.Session.query(model.User)
    user = query.filter_by(apikey=apikey).first()

    if not user:
        user = api_token.get_user_from_token(apikey)
    return user


def set_controller_and_action():
    g.controller, g.action = p.toolkit.get_endpoint()


def handle_i18n(environ=None):
    u'''
    Strips the locale code from the requested url
    (eg '/sk/about' -> '/about') and sets environ variables for the
    language selected:

        * CKAN_LANG is the language code eg en, fr
        * CKAN_LANG_IS_DEFAULT is set to True or False
        * CKAN_CURRENT_URL is set to the current application url
    '''
    environ = environ or request.environ
    locale_list = get_locales_from_config()
    default_locale = config.get(u'ckan.locale_default', u'en')

    # We only update once for a request so we can keep
    # the language and original url which helps with 404 pages etc
    if u'CKAN_LANG' not in environ:
        path_parts = environ[u'PATH_INFO'].split(u'/')
        if len(path_parts) > 1 and path_parts[1] in locale_list:
            environ[u'CKAN_LANG'] = path_parts[1]
            environ[u'CKAN_LANG_IS_DEFAULT'] = False
            # rewrite url
            if len(path_parts) > 2:
                environ[u'PATH_INFO'] = u'/'.join([u''] + path_parts[2:])
            else:
                environ[u'PATH_INFO'] = u'/'
        else:
            environ[u'CKAN_LANG'] = default_locale
            environ[u'CKAN_LANG_IS_DEFAULT'] = True

        set_ckan_current_url(environ)


def set_ckan_current_url(environ):
    # Current application url
    path_info = environ[u'PATH_INFO']
    # sort out weird encodings
    path_info = \
        u'/'.join(quote(pce, u'') for pce in path_info.split(u'/'))

    qs = environ.get(u'QUERY_STRING')
    if qs:
        # sort out weird encodings
        qs = quote(qs, u'')
        environ[u'CKAN_CURRENT_URL'] = u'%s?%s' % (path_info, qs)
    else:
        environ[u'CKAN_CURRENT_URL'] = path_info
