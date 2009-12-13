"""Pylons environment configuration"""
import os

from sqlalchemy import engine_from_config
from pylons import config

import ckan.lib.app_globals as app_globals
import ckan.lib.helpers
from ckan.config.routing import make_map

from genshi.filters.i18n import Translator
from pylons.i18n.translation import ugettext

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """
    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='ckan',
                    template_engine='genshi', paths=paths)

    config['routes.map'] = make_map()
    config['pylons.g'] = app_globals.Globals()
    config['pylons.h'] = ckan.lib.helpers

    # Customize templating options via this variable
    tmpl_options = config['buffet.template_options']
    # Translator (i18n)
    translator = Translator(ugettext)
    def template_loaded(template):
        template.filters.insert(0, translator)
    tmpl_options["genshi.loader_callback"] = template_loaded

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    config['pylons.g'].sa_engine = engine_from_config(config, 'sqlalchemy.')

