# encoding: utf-8

"""WSGI app initialization"""

import logging
from typing import Union

from ckan.config.environment import load_environment
from ckan.config.middleware.flask_app import make_flask_stack
from ckan.common import CKANConfig
from ckan.types import CKANApp, Config

log = logging.getLogger(__name__)


def make_app(conf: Union[Config, CKANConfig]) -> CKANApp:
    '''
    Initialise the Flask app and wrap it in dispatcher middleware.
    '''

    load_environment(conf)

    flask_app = make_flask_stack(conf)

    return flask_app
