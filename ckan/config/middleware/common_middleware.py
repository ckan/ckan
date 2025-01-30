# encoding: utf-8

"""Additional middleware used by the Flask app stack."""
from typing import Any

from urllib.parse import urlparse

from flask.sessions import SecureCookieSessionInterface
from flask_session.redis import RedisSessionInterface

from ckan.common import config
from ckan.types import CKANApp, Request
from ckan.lib.redis import connect_to_redis


class RootPathMiddleware(object):
    """Set SERVER_NAME and SCRIPT_NAME.

    Ideally, these variables must be set by web server, but adding it here is
    more reliable and works even when server configuration is not synchronized
    with CKAN configuration.
    """
    def __init__(self, app: CKANApp):
        self.app = app

    def __call__(self, environ: Any, start_response: Any):
        # SERVER_NAME is used for building external URLs.
        environ["SERVER_NAME"] = config["SERVER_NAME"]

        # SCRIPT_NAME defines the prefix of the URL path. It's set to
        # `ckan.root_path` without locale part. The locale is added manually
        # inside `url_for` helper, which opens a possibility for building
        # cross-locale links(mainly used by language selector).
        environ["SCRIPT_NAME"] = config["APPLICATION_ROOT"]

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
