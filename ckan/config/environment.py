"""Pylons environment configuration"""
import os

from sqlalchemy import engine_from_config
from pylons import config
from genshi.template import TemplateLoader

import ckan.lib.app_globals as app_globals
import ckan.lib.helpers
from ckan.config.routing import make_map
from ckan import model

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
    config['pylons.app_globals'] = app_globals.Globals()
    config['pylons.h'] = ckan.lib.helpers

    ## redo template setup to use genshi.search_path (so remove std template setup)
    template_paths = [paths['templates'][0]]
    extra_template_paths = app_conf.get('extra_template_paths', '')
    if extra_template_paths:
        # must be first for them to override defaults
        template_paths = extra_template_paths.split(',') + template_paths

    # Translator (i18n)
    translator = Translator(ugettext)
    def template_loaded(template):
        template.filters.insert(0, translator)

    # Create the Genshi TemplateLoader
    # config['pylons.app_globals'].genshi_loader = TemplateLoader(
    #    paths['templates'], auto_reload=True)
    # tmpl_options["genshi.loader_callback"] = template_loaded
    config['pylons.app_globals'].genshi_loader = TemplateLoader(
        template_paths, auto_reload=True, callback=template_loaded)
    # HACK! For some reason callback=template_loaded in previous line does
    # *not* work (this required 1h to track down!!)
    # This does work ...
    tmpl_options = config['buffet.template_options']
    tmpl_options["genshi.loader_callback"] = template_loaded

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    # Setup the SQLAlchemy database engine
    engine = engine_from_config(config, 'sqlalchemy.')
    model.init_model(engine)

