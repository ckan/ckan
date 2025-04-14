# encoding: utf-8
from __future__ import annotations

from http import HTTPStatus
from typing import Any, Optional
import hashlib
import re

from urllib.parse import quote
from flask.wrappers import Response

import ckan.model as model
import ckan.lib.api_token as api_token
from ckan.common import g, request, config, current_user, logout_user
from ckan.lib.i18n import get_locales_from_config
import ckan.plugins as p

import logging

log = logging.getLogger(__name__)

# For more details about caching, please read the spec located at
# https://datatracker.ietf.org/doc/html/rfc7234


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
def set_etag_and_fast_304_response_if_unchanged(response: Response) -> Response:
    """Set ETag and return 304 if content is unchanged."""

    # skip stremaing content
    if not response.is_streamed:
        enable_etags = config.get(u'ckan.cache_etags', True)
        enable_etags_not_modified = config.get(u'ckan.cache_etags_notModified', True)
        allowed_status_codes = {HTTPStatus.OK,  # 200
                                HTTPStatus.MOVED_PERMANENTLY,  # 301
                                HTTPStatus.FOUND,  # 302
                                HTTPStatus.UNAUTHORIZED,  # 401
                                HTTPStatus.FORBIDDEN,  # 403
                                HTTPStatus.NOT_FOUND  # 404
                                }

        if response.status_code in allowed_status_codes and enable_etags:
            if 'etag' not in response.headers:
                # s3 etag uses md5, so using it here also

                content_type = response.mimetype or ''
                allowed_types = {'text/plain', 'text/css',
                                 'text/html', 'application/json'}
                etag_super_strong = u'__etag_super_strong__' in request.environ

                try:
                    # anon/public get ignored csrf
                    if (etag_super_strong
                            or content_type not in allowed_types
                            or current_user.is_authenticated or g.user):
                        data_to_hash = response.get_data()
                    else:
                        # Regex for both _csrf_token content and csp nonce and don't
                        # care if there is new lines spacing etc attributes which are
                        # dynamic on pages
                        # May need to add more when we come across them.

                        field_name = re.escape(config.get("WTF_CSRF_FIELD_NAME", "_csrf_token"))  # noqa: E501
                        # csrf meta only, if to include value,
                        #   update (?:content) to (?:content|value)
                        pattern = fr'(?i)((?:_csrf_token|{field_name})[^>]*?\b(?:content)=|\bnonce=)["\'][^"\']+(["\'])'  # noqa: E501

                        # Replace values with etag_removed
                        response_data = re.sub(pattern,
                                               lambda m: m.group(1) + '="etag_removed"',
                                               response.get_data(as_text=True))
                        data_to_hash = response_data.encode()

                    etag = hashlib.md5(data_to_hash).hexdigest()
                    response.set_etag(etag)
                except (AttributeError, IndexError, TypeError,
                        UnicodeEncodeError, ValueError, re.error) as e:
                    logging.info("Failed to compute and set ETag: %s", e)
            else:
                etag = response.headers.get('etag')

            etag_not_conditional = u'__etag_not_conditional__' not in request.environ
            # Allow legacy behaviour if config is set
            if enable_etags_not_modified and etag_not_conditional:
                # Use built-in function now that we have an eTag
                response.make_conditional(request.environ)

    return response


def set_cache_control_headers_for_response(response: Response) -> Response:
    """ This uses the presents of request environ's: '__no_cache__',
    '__no_private_cache__', '__limit_cache_by_cookie__' as well
    as config variables to control cache response headers"""

    is_webasset = u'__webasset__' in request.environ
    if is_webasset:
        # Don't alter web assets as flask_app has handled cache control for us
        return response

    # __no_cache__ should not be present when caching is allowed
    allow_cache = u'__no_cache__' not in request.environ
    # __no_private_cache__ should not be present when private caching is allowed
    allow_private_cache = u'__no_private_cache__' not in request.environ

    # Use sparingly as this kills full browser caching (including dev tools)
    is_sensitive = u'__is_sensitive__' in request.environ
    # If cookie is changing, don't allow it to be cached/stored
    is_set_cookie_header = u'Set-Cookie' in response.headers
    if is_sensitive or is_set_cookie_header:
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
        if private_cache_expire != 9999999:  # ckan config int blocks None
            response.cache_control.max_age = private_cache_expire
            # best to ensure freshness if you give a max_age
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
