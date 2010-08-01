"""Pylons environment configuration"""
import os
from urlparse import urlparse

import pylons
from sqlalchemy import engine_from_config
from pylons import config
from pylons.i18n.translation import ugettext
from genshi.template import TemplateLoader
from genshi.filters.i18n import Translator

import ckan.lib.app_globals as app_globals
import ckan.lib.helpers
from ckan.config.routing import make_map
from ckan import model

import plugins


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
    config.init_app(global_conf, app_conf, package='ckan', paths=paths)
    
    # This is set up before globals are initialized
    site_url = config.get('ckan.site_url', 'http://www.ckan.net')
    ckan_host = config['ckan.host'] = urlparse(site_url).netloc
    if ':' in ckan_host:
        ckan_host, port = ckan_host.split(':')
    if config.get('ckan.site_id') is None:
        config['ckan.site_id'] = '_'.join(config['ckan.host'].split('.')[::-1])
    
    config['routes.map'] = make_map()
    config['pylons.app_globals'] = app_globals.Globals()
    config['pylons.h'] = ckan.lib.helpers
    
    # load all CKAN plugins
    plugins.load_all(config)
    
    ## redo template setup to use genshi.search_path (so remove std template setup)
    template_paths = [paths['templates'][0]]
    extra_template_paths = app_conf.get('extra_template_paths', '')
    if extra_template_paths:
        # must be first for them to override defaults
        template_paths = extra_template_paths.split(',') + template_paths

    # Translator (i18n)
    translator = Translator(pylons.translator)
    def template_loaded(template):
        translator.setup(template)

    # Create the Genshi TemplateLoader
    # config['pylons.app_globals'].genshi_loader = TemplateLoader(
    #    paths['templates'], auto_reload=True)
    # tmpl_options["genshi.loader_callback"] = template_loaded
    config['pylons.app_globals'].genshi_loader = TemplateLoader(
        template_paths, auto_reload=True, callback=template_loaded)

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)    

    # Setup the SQLAlchemy database engine
    engine = engine_from_config(config, 'sqlalchemy.')
    model.init_model(engine)
        
    if bool(config.get('ckan.build_search_index_synchronously', True)):
        import ckan.lib.search as search
        search.setup_synchronous_indexing()
    else:
        import ckan.lib.async_notifier as notf

