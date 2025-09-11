# encoding: utf-8

"""WSGI app initialization"""
from __future__ import annotations

import logging
from typing import Optional, Union

from flask.ctx import AppContext

from ckan.config.environment import load_environment
from ckan.config.middleware.flask_app import make_flask_stack
from ckan.common import CKANConfig
from ckan.types import CKANApp, Config


log = logging.getLogger(__name__)

# This is a test Flask request context to be used internally.
# Do not use it!
_internal_app_context: Optional[AppContext] = None


def make_app(conf: Union[Config, CKANConfig]) -> CKANApp:
    '''
    Initialise the Flask app and wrap it in dispatcher middleware.
    '''

    load_environment(conf)

    flask_app = make_flask_stack()

    # Set this internal test request context with the configured environment so
    # it can be used when calling url_for from tests
    global _internal_app_context
    _internal_app_context = flask_app._wsgi_app.app_context()

    return flask_app
