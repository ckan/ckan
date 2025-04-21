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
# as well as RFC 7234 + RFC 5861 + RFC 9111


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


allowed_status_codes = frozenset({HTTPStatus.OK,  # 200
                                  HTTPStatus.MOVED_PERMANENTLY,  # 301
                                  HTTPStatus.FOUND,  # 302
                                  HTTPStatus.UNAUTHORIZED,  # 401
                                  HTTPStatus.FORBIDDEN,  # 403
                                  HTTPStatus.NOT_FOUND  # 404
                                  })


# ETag's are very useful since it allows conditional freshness checks
# without bandwidth costs by the browser/cdn.
# Since html pages from ckan are always generated on the fly it
# can't use last modified and content length our Nginx does it
# This is a simple etag which changes on each request
# If you wish to have etags always use etag plugin
def set_etag_for_response(response: Response) -> Response:
    """Set ETag and return 304 if content is unchanged."""

    # skip streaming content
    if response.is_streamed:
        return response

    enable_etags = config.get(u'ckan.etags.enabled', True)
    if enable_etags and response.status_code in allowed_status_codes:
        if 'etag' not in response.headers:
            etag_replace = getattr(g, 'etag_replace', None)
            if etag_replace:
                response.set_etag(etag_replace)
            else:
                # s3 etag uses md5 if you want that, load `etag` plugin, this is fast
                # hash etag which h.set_etag_modified_time(str) can be used to set
                # correct modified time as well as extended by plugins via
                # `h.etag_append(str)` for their uniqueness constraints
                mtime = getattr(g, 'etag_modified_time', time.time())
                size = response.content_length
                etag_append = getattr(g, 'etag_append', "")
                check = (adler32(request.environ['PATH_INFO'].encode('utf-8'))
                         & 0xFFFFFFFF)
                response.set_etag(f"{mtime}-{size}-{check}{etag_append}")

    # Use built-in function for make_conditional
    response.make_conditional(request.environ)

    return response


def set_cache_control_headers_for_response(response: Response) -> Response:
    cache_type: Optional[CacheType] = getattr(g, 'cache_type', None)
    # log.debug("set_cache_control_headers_for_response %r", cacheType)
    cache_type = set_cache_control_headers_from_request(cache_type, response)

    if cache_type == CacheType.OVERRIDDEN:
        # Don't alter notified overridden response
        return response

    # the must-understand directive is recommended to be used in conjunction
    # with no-store in the case that said directive is unsupported by a
    # legacu cache and thus ignored.
    response.cache_control.must_understand = True

    if u'Pragma' in response.headers:
        # Pragma has been replaced with Cache-Control
        del response.headers["Pragma"]

    no_transform = config.get(u'ckan.cache.no_transform')
    if no_transform:
        response.cache_control.no_transform = True

    set_vary_cache_settings(response)

    # environ is deprecated and will be removed in 2026/7
    environ_no_cache = u'__no_cache__' in request.environ
    if environ_no_cache:
        log.warning("environ '__no_cache__' is deprecated, "
                    "use 'h.set_cache_level' function instead")
        if cache_type is None or cache_type == CacheType.PUBLIC:
            # Only make private, don't override other levels
            cache_type = CacheType.PRIVATE

    # log.debug("session accessed: %r modified: %r, keys: %r",
    #           session.accessed, session.modified, session.keys())
    if (session.accessed and len(session.keys()) > 0
       and cache_type != CacheType.SENSITIVE):
        # If we have session data, it can't be public
        # Note: due to CSRF protection being 'session' based. All html pages will
        # now be classified non-public due to needing to vary on at least cookie.
        # as session stores '_csrf_token', '_fresh', '_permanent'
        cache_type = CacheType.PRIVATE

    # If cookie's is changing, don't allow it to be cached/stored
    is_set_cookie_header = u'Set-Cookie' in response.headers
    if is_set_cookie_header or session.modified:
        # Note, flask_session occurs after ckan cache controls. So must use
        # session.modified flag for swap outs
        # If you use redis session, then the cookie only changes on
        # first access/login/logout.
        cache_type = CacheType.SENSITIVE

    log.error("chacheType = %r", cache_type)

    if cache_type == CacheType.PUBLIC:
        response.cache_control.public = True
        response.cache_control.private = None  # Reset
        response.cache_control.max_age = config.get(u'ckan.cache.expires')
        response.cache_control.s_maxage = config.get(u'ckan.cache.shared.expires')
        set_cache_control_while_stale(response)

    elif cache_type == CacheType.PRIVATE:
        response.cache_control.public = False  # Reset
        response.cache_control.private = True
        private_cache_expire = config.get(u'ckan.cache.private.expires')
        response.cache_control.max_age = private_cache_expire
        set_cache_control_while_stale(response)

    elif cache_type in (CacheType.NO_CACHE, CacheType.SENSITIVE):
        # no_cache is like private, max-age=0
        # no_cache Does not block bfcache — revalidation applies to HTTP cache only
        response.cache_control.no_cache = True
        response.cache_control.max_age = 0  # This is fall back for older browsers
        response.cache_control.public = False  # Reset
        response.cache_control.private = None  # Reset

    if cache_type == CacheType.SENSITIVE:
        # https://developer.chrome.com/docs/web-platform/bfcache-ccns
        # no_store Chrome assumes the page should never be reused, even in memory.
        response.cache_control.no_store = True

    return response


def set_vary_cache_settings(rs: Response):
    # limit_cache_for_api should vary by api auth header name
    limit_cache_by_api = getattr(g, 'limit_cache_for_api', False)
    if limit_cache_by_api:
        rs.vary.add(config.get("apitoken_header_name"))

    limit_cache_by_cookie = u'__limit_cache_by_cookie__' in request.environ
    if limit_cache_by_cookie:
        log.warning("environ: '__limit_cache_by_cookie__' is deprecated, "
                    "use 'g.limit_cache_for_page = True' instead")

    limit_cache_for_page = getattr(g, 'limit_cache_for_page', False)
    if limit_cache_for_page or limit_cache_by_cookie:
        rs.vary.add("Cookie")
        rs.vary.add("HX-Request")


def set_cache_control_while_stale(rs: Response) -> None:
    """This functions updates cache_control with config settings.
    If both stale configs are set to 0, then must-validate will be enabled"""
    stale_while_revalidates = config.get(u'ckan.cache.stale_while_revalidates')
    stale_if_error = config.get(u'ckan.cache.stale_if_error')
    if stale_while_revalidates == 0 and stale_if_error == 0:
        # must_revalidate overrides staleness values.
        rs.cache_control.must_revalidate = True
    else:
        rs.cache_control.stale_while_revalidate = stale_while_revalidates
        rs.cache_control.stale_if_error = stale_if_error
        rs.cache_control.must_revalidate = False


def set_cache_control_headers_from_request(cache_type: Optional[CacheType],
                                           rs: Response) -> Optional[CacheType]:
    """This function returns updated cacheType if request headers wants us
    to disable cache, also sets no-transform if also found."""
    # https://http.dev/cache-control
    # This is very useful for developer tools testing
    if 'Cache-Control' in request.headers:
        request_cache_control = request.headers.get('Cache-Control', '')
        directives = {d.strip() for d in request_cache_control.lower().split(',')}

        if 'no-cache' in directives:
            cache_type = CacheType.NO_CACHE
        elif 'no-store' in directives:
            cache_type = CacheType.SENSITIVE

        if 'no-transform' in directives:
            rs.cache_control.no_transform = True
    return cache_type


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

    # If it is set, then Response Vary. This is a catch-all for extensions
    g.limit_cache_for_api = True

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
