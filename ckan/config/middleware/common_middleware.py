# encoding: utf-8

"""Additional middleware used by the Flask app stack."""
from typing import Any, Optional

from urllib.parse import urlparse

from flask import Response
from flask.sessions import SecureCookieSessionInterface
from flask_session.redis import RedisSessionInterface

from ckan.common import CacheType, config, session
from ckan.types import CKANApp, Request
from ckan.lib import helpers as h
from ckan.lib.redis import connect_to_redis
from ckan.views import set_cache_control_while_stale


class RootPathMiddleware(object):
    '''
    Prevents the SCRIPT_NAME server variable conflicting with the ckan.root_url
    config. The routes package uses the SCRIPT_NAME variable and appends to the
    path and ckan addes the root url causing a duplication of the root path.
    This is a middleware to ensure that even redirects use this logic.
    '''
    def __init__(self, app: CKANApp):
        self.app = app

    def __call__(self, environ: Any, start_response: Any):
        # Prevents the variable interfering with the root_path logic
        if 'SCRIPT_NAME' in environ:
            environ['SCRIPT_NAME'] = ''

        return self.app(environ, start_response)


class HostHeaderMiddleware(object):
    '''
        Prevent the `Host` header from the incoming request to be used
        in the `Location` header of a redirect.
    '''
    def __init__(self, app: CKANApp):
        self.app = app

    def __call__(self, environ: Any, start_response: Any) -> Any:
        path_info = environ[u'PATH_INFO']
        if path_info in ['/login_generic', '/user/login',
                         '/user/logout', '/user/logged_in',
                         '/user/logged_out']:
            site_url = config.get('ckan.site_url')
            parts = urlparse(site_url)
            environ['HTTP_HOST'] = str(parts.netloc)
        return self.app(environ, start_response)


class CKANSecureCookieSessionInterface(SecureCookieSessionInterface):
    """Flask cookie-based sessions with expiration support.

    Parent class supports only cookies stored till the end of the browser's
    session. Current class extends its functionality and adds support of
    permanent sessions.

    """

    def __init__(self, app: CKANApp):
        pass

    def open_session(self, app: CKANApp, request: Request):
        session = super().open_session(app, request)
        if session:
            # Cookie-based sessions expire with the browser's session. The line
            # below changes this behavior, extending session's lifetime by
            # `PERMANENT_SESSION_LIFETIME` seconds. `SESSION_PERMANENT` option
            # is used as indicator of permanent sessions by flask-session
            # package, so we also should rely on it, for predictability.
            session.setdefault("_permanent", app.config["SESSION_PERMANENT"])

        return session


class CKANRedisSessionInterface(RedisSessionInterface):
    """Flask-Session redis-based sessions with CKAN's Redis connection.

    Parent class connects to Redis instance running on localhost:6379. This
    class initializes session with the connection to the Redis instance
    configured by `ckan.redis.url` option.

    """

    def __init__(self, app: CKANApp):
        app.config.setdefault("SESSION_REDIS", connect_to_redis())
        return super().__init__(
            app,
            app.config["SESSION_REDIS"],
            app.config["SESSION_KEY_PREFIX"],
            app.config["SESSION_USE_SIGNER"],
            app.config["SESSION_PERMANENT"]
        )


def static_or_webasset_pre_configuration(max_age: Optional[int]):
    h.set_cache_level(CacheType.OVERRIDDEN)
    if max_age is not None:
        cache_expire = max_age
    else:
        cache_expire = config.get(u'ckan.cache.expires', 0)
    if cache_expire == 0:
        # If set, ``Cache-Control`` will be ``public``, otherwise
        #         it will be ``no-cache``
        cache_expire = None
        shared_cache_expire = 0
    else:
        shared_cache_expire = config.get(u'ckan.cache.shared.expires')
    return cache_expire, shared_cache_expire


def static_or_webasset_post_configuration(response: Response, shared_cache_expire: int):
    if shared_cache_expire != 0:
        response.cache_control.s_maxage = shared_cache_expire
    set_cache_control_while_stale(response)
    if not session.modified:
        # Session must be set to not accessed to stop introduction of vary by Cookie
        session.accessed = False
