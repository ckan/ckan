# encoding: utf-8

"""WSGI app initialization"""
from __future__ import annotations

import logging
from typing import Optional, Union

from flask.ctx import RequestContext
from flask.sessions import SecureCookieSessionInterface
from flask_session import RedisSessionInterface

from ckan.config.environment import load_environment
from ckan.config.middleware.flask_app import make_flask_stack
from ckan.common import CKANConfig
from ckan.types import CKANApp, Config, Request
from ckan.lib.redis import connect_to_redis


log = logging.getLogger(__name__)

# This is a test Flask request context to be used internally.
# Do not use it!
_internal_test_request_context: Optional[RequestContext] = None


def make_app(conf: Union[Config, CKANConfig]) -> CKANApp:
    '''
    Initialise the Flask app and wrap it in dispatcher middleware.
    '''

    load_environment(conf)

    flask_app = make_flask_stack(conf)

    # Set this internal test request context with the configured environment so
    # it can be used when calling url_for from tests
    global _internal_test_request_context
    _internal_test_request_context = flask_app._wsgi_app.test_request_context()

    return flask_app


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
            app.config["SESSION_REDIS"],
            app.config["SESSION_KEY_PREFIX"],
            app.config["SESSION_USE_SIGNER"],
            app.config["SESSION_PERMANENT"]
        )
