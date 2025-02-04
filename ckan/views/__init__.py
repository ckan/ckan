# encoding: utf-8
from __future__ import annotations

from typing import Any, Optional

import six

from urllib.parse import quote
from flask.wrappers import Response

import ckan.model as model
import ckan.lib.api_token as api_token
from ckan.common import g, request, config, current_user, logout_user
from ckan.lib.i18n import get_locales_from_config
import ckan.plugins as p

import logging
log = logging.getLogger(__name__)


def set_cors_headers_for_response(response: Response) -> Response:
    u'''
    Set up Access Control Allow headers if either origin_allow_all is True, or
    the request Origin is in the origin_whitelist.
    '''
    if request.headers.get(u'Origin'):
        cors_origin_allowed = None
        allow_all = config.get(u'ckan.cors.origin_allow_all')
        whitelisted = request.headers.get(u'Origin') in config.get(
            u'ckan.cors.origin_whitelist')
        if allow_all:
            cors_origin_allowed = '*'
        elif whitelisted:
            # set var to the origin to allow it.
            cors_origin_allowed: Optional[str] = request.headers.get(u'Origin')

        if cors_origin_allowed is not None:
            response.headers['Access-Control-Allow-Origin'] = \
                cors_origin_allowed
            response.headers['Access-Control-Allow-Methods'] = \
                'POST, PUT, GET, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = \
                'X-CKAN-API-KEY, Authorization, Content-Type'

    return response


def set_cache_control_headers_for_response(response: Response) -> Response:

    # __no_cache__ should not be present when caching is allowed
    allow_cache = u'__no_cache__' not in request.environ
    limit_cache_by_cookie = u'__limit_cache_by_cookie__' in request.environ

    if u'Pragma' in response.headers:
        del response.headers["Pragma"]

    if allow_cache:
        response.cache_control.public = True
        try:
            cache_expire = config.get(u'ckan.cache_expires')
            response.cache_control.max_age = cache_expire
            response.cache_control.must_revalidate = True
        except ValueError:
            pass
    else:
        response.cache_control.private = True

    # Invalidate cached pages upon login/logout
    if limit_cache_by_cookie:
        response.vary.add("Cookie")

    return response


def identify_user() -> Optional[Response]:
    u'''This function exists only to maintain backward compatibility
    to extensions that still need g.user/g.userobj.

    Note: flask_login now identifies users for us behind the scene.
    '''
    # see if it was proxied first
    g.remote_addr = request.environ.get(u'HTTP_X_FORWARDED_FOR', u'')
    if not g.remote_addr:
        g.remote_addr = request.environ.get(u'REMOTE_ADDR',
                                            u'Unknown IP Address')

    # Authentication plugins get a chance to run here break as soon as a user
    # is identified or a response is returned
    authenticators = p.PluginImplementations(p.IAuthenticator)
    if authenticators:
        for item in authenticators:
            response = item.identify()
            if response:
                return response
            try:
                if current_user.is_authenticated or g.user:
                    break
            except AttributeError:
                continue
    # sets the g.user/g.userobj for extensions
    g.user = current_user.name
    g.userobj = '' if current_user.is_anonymous else current_user

    # logout, if a user that was still logged in is deleted.
    if current_user.is_authenticated:
        if not current_user.is_active:
            logout_user()

    # If we have a user but not the userobj let's get the userobj. This means
    # that IAuthenticator extensions do not need to access the user model
    # directly.
    if g.user:
        if not getattr(g, u'userobj', None):
            g.userobj = model.User.by_name(g.user)

    # general settings
    if g.user:
        if g.userobj:
            userobj = model.User.by_name(g.user)
            userobj.set_user_last_active()  # type: ignore
        g.author = g.user
    else:
        g.author = g.remote_addr
    g.author = str(g.author)


def _get_user_for_apitoken() -> Optional[model.User]:  # type: ignore
    apitoken_header_name = config.get("apikey_header_name")

    apitoken: str = request.headers.get(apitoken_header_name, u'')
    if not apitoken:
        apitoken = request.environ.get(apitoken_header_name, u'')
    if not apitoken:
        # For misunderstanding old documentation (now fixed).
        apitoken = request.environ.get(u'HTTP_AUTHORIZATION', u'')
    if not apitoken:
        apitoken = request.environ.get(u'Authorization', u'')
        # Forget HTTP Auth credentials (they have spaces).
        if u' ' in apitoken:
            apitoken = u''
    if not apitoken:
        return None
    apitoken = six.ensure_text(apitoken, errors=u"ignore")
    log.debug(u'Received API Token: %s' % apitoken)

    user = api_token.get_user_from_token(apitoken)

    return user


def set_controller_and_action() -> None:
    g.blueprint, g.view = p.toolkit.get_endpoint()


def handle_i18n(environ: Optional[dict[str, Any]] = None) -> None:
    u'''
    Strips the locale code from the requested url
    (eg '/sk/about' -> '/about') and sets environ variables for the
    language selected:

        * CKAN_LANG is the language code eg en, fr
        * CKAN_LANG_IS_DEFAULT is set to True or False
        * CKAN_CURRENT_URL is set to the current application url
    '''
    environ = environ or request.environ
    assert environ
    locale_list = get_locales_from_config()
    default_locale = config.get(u'ckan.locale_default')

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


def set_ckan_current_url(environ: Any) -> None:
    # Current application url
    path_info = environ[u'PATH_INFO']
    # sort out weird encodings
    path_info = \
        u'/'.join(quote(pce, u'') for pce in path_info.split(u'/'))

    qs = environ.get(u'QUERY_STRING')
    if qs:
        environ[u'CKAN_CURRENT_URL'] = u'%s?%s' % (path_info, qs)
    else:
        environ[u'CKAN_CURRENT_URL'] = path_info
