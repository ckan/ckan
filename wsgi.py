# -*- coding: utf-8 -*-

import os
from ckan.config.middleware import make_app
from ckan.cli import CKANConfigLoader
from logging.config import fileConfig as loggingFileConfig
config_filepath = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), u'ckan.ini')
abspath = os.path.join(os.path.dirname(os.path.abspath(__file__)))
loggingFileConfig(config_filepath)
config = CKANConfigLoader(config_filepath).get_config()
application = make_app(config)
