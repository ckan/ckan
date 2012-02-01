"""Pylons environment configuration"""
import os
from urlparse import urlparse
import logging
import warnings

from paste.deploy.converters import asbool

# Suppress benign warning 'Unbuilt egg for setuptools'
warnings.simplefilter('ignore', UserWarning) 
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
from ckan import plugins



def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object
    """
    
    ######  Pylons monkey-patch
    # this must be run at a time when the env is semi-setup, thus inlined here. 
    # Required by the deliverance plugin and iATI
    from pylons.wsgiapp import PylonsApp
    import pkg_resources
    find_controller_generic = PylonsApp.find_controller
    # This is from pylons 1.0 source, will monkey-patch into 0.9.7
    def find_controller(self, controller):
        if controller in self.controller_classes:
            return self.controller_classes[controller]
        # Check to see if its a dotted name
        if '.' in controller or ':' in controller:
            mycontroller = pkg_resources.EntryPoint.parse('x=%s' % controller).load(False)
            self.controller_classes[controller] = mycontroller
            return mycontroller
        return find_controller_generic(self, controller)
    PylonsApp.find_controller = find_controller
    ###### END evil monkey-patch 

    os.environ['CKAN_CONFIG'] = global_conf['__file__']

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    
    config.init_app(global_conf, app_conf, package='ckan', paths=paths)
    
    # load all CKAN plugins
    plugins.load_all(config)

    from ckan.plugins import PluginImplementations
    from ckan.plugins.interfaces import IConfigurer
    
    for plugin in PluginImplementations(IConfigurer):
        # must do update in place as this does not work:
        # config = plugin.update_config(config)
        plugin.update_config(config)
    
    # This is set up before globals are initialized
    site_url = config.get('ckan.site_url', '')
    ckan_host = config['ckan.host'] = urlparse(site_url).netloc
    if config.get('ckan.site_id') is None:
        if ':' in ckan_host:
            ckan_host, port = ckan_host.split(':')
        assert ckan_host, 'You need to configure ckan.site_url or ' \
                          'ckan.site_id for SOLR search-index rebuild to work.'
        config['ckan.site_id'] = ckan_host

    # Init SOLR settings and check if the schema is compatible
    from ckan.lib.search import SolrSettings, check_solr_schema_version
    SolrSettings.init(config.get('solr_url'),
                      config.get('solr_user'),
                      config.get('solr_password'))
    check_solr_schema_version()

    config['routes.map'] = make_map()
    config['pylons.app_globals'] = app_globals.Globals()
    config['pylons.h'] = ckan.lib.helpers
        
    ## redo template setup to use genshi.search_path (so remove std template setup)
    template_paths = [paths['templates'][0]]
    extra_template_paths = config.get('extra_template_paths', '')
    if extra_template_paths:
        # must be first for them to override defaults
        template_paths = extra_template_paths.split(',') + template_paths

    # Translator (i18n)
    translator = Translator(pylons.translator)
    def template_loaded(template):
        translator.setup(template)

    # Markdown ignores the logger config, so to get rid of excessive
    # markdown debug messages in the log, set it to the level of the
    # root logger.
    logging.getLogger("MARKDOWN").setLevel(logging.getLogger().level)

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

    if not model.meta.engine:
        model.init_model(engine)
    
    from ckan.plugins import PluginImplementations
    from ckan.plugins.interfaces import IConfigurable
    
    for plugin in PluginImplementations(IConfigurable):
        plugin.configure(config)
    
