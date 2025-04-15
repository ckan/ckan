# encoding: utf-8
from __future__ import annotations

import time
from http import HTTPStatus
from typing import Any, Optional
from zlib import adler32

from urllib.parse import quote
from flask.wrappers import Response

import ckan.model as model
import ckan.lib.api_token as api_token
from ckan.common import (g, request, config, current_user,
                         logout_user, session, CacheType)
from ckan.lib.i18n import get_locales_from_config
import ckan.plugins as p

import logging

log = logging.getLogger(__name__)

# For more details about caching, please read the spec located at
# https://datatracker.ietf.org/doc/html/rfc9111


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
                f'{config.get("apitoken_header_name")}, Content-Type'

    return response


# ETag's are very useful since it allows conditional freshness checks
# without bandwidth costs by the browser/cdn.
# Since html pages from ckan are always generated on the fly it
# can't use last modified and content length our Nginx does it
# This is a simple etag which changes on each request
# If you wish to have etags always use etag plugin
def set_etag_for_response(response: Response) -> Response:
    """Set ETag and return 304 if content is unchanged."""

    # skip streaming content
    if not response.is_streamed:
        enable_etags = config.get(u'ckan.cache_etags', True)
        allowed_status_codes = {HTTPStatus.OK,  # 200
                                HTTPStatus.MOVED_PERMANENTLY,  # 301
                                HTTPStatus.FOUND,  # 302
                                HTTPStatus.UNAUTHORIZED,  # 401
                                HTTPStatus.FORBIDDEN,  # 403
                                HTTPStatus.NOT_FOUND  # 404
                                }

        if response.status_code in allowed_status_codes and enable_etags:
            if 'etag' not in response.headers:
                # s3 etag uses md5 if you want that, load etag plugin, this is weak etag
                check = (adler32(request.environ['PATH_INFO'].encode('utf-8'))
                         & 0xFFFFFFFF)
                mtime = time.time()
                size = response.content_length
                response.set_etag(f"{mtime}-{size}-{check}")

        # Use built-in function for make_conditional
        response.make_conditional(request.environ)

    return response


def set_cache_control_headers_for_response(response: Response) -> Response:
    """ This uses the presents of ckan g's: 'cache_enabled',
    '__no_private_cache__', '__limit_cache_by_cookie__' as well
    as config variables to control cache response headers"""
    cacheType = getattr(g, 'cacheType', None)

    if cacheType == CacheType.OVERRIDDEN:
        # Don't alter notified overridden response
        return response

    # __no_cache__ should not be present when caching is allowed
    # environ is deprecated will be removed in 2026/7

    environ_allow_cache = u'__no_cache__' not in request.environ

    allow_cache = environ_allow_cache or not getattr(g, 'no_cache', False)
    # no_private_cache should not be present when private caching is allowed
    allow_private_cache = not getattr(g, 'no_private_cache', False)

    # Use sparingly as this kills full browser caching (including dev tools)
    is_sensitive = getattr(g, 'is_sensitive', False)
    # If cookie is changing, don't allow it to be cached/stored
    is_set_cookie_header = u'Set-Cookie' in response.headers
    if is_sensitive or is_set_cookie_header or session.modified:
        # https://developer.chrome.com/docs/web-platform/bfcache-ccns
        # no_store Chrome assumes the page should never be reused, even in memory.
        response.cache_control.no_store = True
        # enforce no caching defaults
        allow_cache = False
        allow_private_cache = False

    if u'Pragma' in response.headers:
        # Pragma has been replaced with Cache-Control
        del response.headers["Pragma"]

    if allow_cache:
        response.cache_control.public = True
        cache_expire = config.get(u'ckan.cache_expires', 0)
        response.cache_control.max_age = cache_expire
        shared_cache_expire = config.get(u'ckan.shared_cache_expires', 0)
        response.cache_control.s_maxage = shared_cache_expire
        response.cache_control.must_revalidate = True
        response.cache_control.private = None  # Reset
    elif allow_private_cache:
        response.cache_control.public = False  # Reset
        response.cache_control.private = True
        private_cache_expire = config.get(u'ckan.private_cache_expires')
        response.cache_control.max_age = private_cache_expire
        response.cache_control.must_revalidate = True
    else:

        # no_cache is like private, max-age=0
        # no_cache Does not block bfcache — revalidation applies to HTTP cache only
        response.cache_control.no_cache = True
        response.cache_control.max_age = 0  # This is fall back for older browsers
        response.cache_control.public = False  # Reset
        response.cache_control.private = None  # Reset

    # __limit_cache_by_api_header_name__ should vary by api auth header name
    api_header_name = u'__limit_cache_by_api_header_name__' in request.environ
    if api_header_name:
        # So api users get their own payloads
        # Q: If a user is using their own key for public resources and
        #    its public/public dataset/resources and it's a side effect
        #    free `get` should we not vary on api key allowing a shared
        #    cache hit?
        response.vary.add(request.environ.get('__limit_cache_by_api_header_name__'))

    limit_cache_by_cookie = u'__limit_cache_by_cookie__' in request.environ
    # __limit_cache_by_cookie__ should vary by cookie
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
    apitoken_header_name = config.get("apitoken_header_name")
    apitoken_value: str = request.headers.get(apitoken_header_name, u'')

    if not apitoken_value:
        return None

    # ensure response cache-control `Vary` includes api auth header
    # (like cookie on template pages)
    request.environ['__limit_cache_by_api_header_name__'] = apitoken_header_name

    apitoken_value = str(apitoken_value)
    log.debug('Received API Token: %s[...]', apitoken_value[:10])

    user = api_token.get_user_from_token(apitoken_value)

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
