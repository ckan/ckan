"""Pylons environment configuration"""
import os
import logging
import warnings
from urlparse import urlparse

import pylons
from paste.deploy.converters import asbool
import sqlalchemy
from pylons import config
from genshi.template import TemplateLoader
from genshi.filters.i18n import Translator

import ckan.config.routing as routing
import ckan.model as model
import ckan.plugins as p
import ckan.lib.helpers as h
import ckan.lib.search as search
import ckan.lib.app_globals as app_globals


# Suppress benign warning 'Unbuilt egg for setuptools'
warnings.simplefilter('ignore', UserWarning)

class _Helpers(object):
    ''' Helper object giving access to template helpers stopping
    missing functions from causing template exceptions. Useful if
    templates have helper functions provided by extensions that have
    not been enabled. '''
    def __init__(self, helpers, restrict=True):
        functions = {}
        allowed = helpers.__allowed_functions__
        # list of functions due to be depreciated
        self.depreciated = []

        for helper in dir(helpers):
            if helper not in allowed:
                self.depreciated.append(helper)
                if restrict:
                    continue
            functions[helper] = getattr(helpers, helper)
        self.functions = functions

        # extend helper functions with ones supplied by plugins
        extra_helpers = []
        for plugin in p.PluginImplementations(p.ITemplateHelpers):
            helpers = plugin.get_helpers()
            for helper in helpers:
                if helper in extra_helpers:
                    raise Exception('overwritting extra helper %s' % helper)
                extra_helpers.append(helper)
                functions[helper] = helpers[helper]
        # logging
        self.log = logging.getLogger('ckan.helpers')

    @classmethod
    def null_function(cls, *args, **kw):
        ''' This function is returned if no helper is found. The idea is
        to try to allow templates to be rendered even if helpers are
        missing.  Returning the empty string seems to work well.'''
        return ''

    def __getattr__(self, name):
        ''' return the function/object requested '''
        if name in self.functions:
            if name in self.depreciated:
                msg = 'Template helper function `%s` is depriciated' % name
                self.log.warn(msg)
            return self.functions[name]
        else:
            if name in self.depreciated:
                msg = 'Template helper function `%s` is not available ' \
                      'as it has been depriciated.\nYou can enable it ' \
                      'by setting ckan.restrict_template_vars = true ' \
                      'in your .ini file.' % name
                self.log.critical(msg)
            else:
                msg = 'Helper function `%s` could not be found\n ' \
                      '(are you missing an extension?)' % name
                self.log.critical(msg)
            return self.null_function


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
    p.load_all(config)

    for plugin in p.PluginImplementations(p.IConfigurer):
        # must do update in place as this does not work:
        # config = plugin.update_config(config)
        plugin.update_config(config)

    # This is set up before globals are initialized
    site_id = os.environ.get('CKAN_SITE_ID')
    if site_id:
        config['ckan.site_id'] = site_id

    site_url = config.get('ckan.site_url', '')
    ckan_host = config['ckan.host'] = urlparse(site_url).netloc
    if config.get('ckan.site_id') is None:
        if ':' in ckan_host:
            ckan_host, port = ckan_host.split(':')
        assert ckan_host, 'You need to configure ckan.site_url or ' \
                          'ckan.site_id for SOLR search-index rebuild to work.'
        config['ckan.site_id'] = ckan_host

    # Init SOLR settings and check if the schema is compatible
    #from ckan.lib.search import SolrSettings, check_solr_schema_version
    search.SolrSettings.init(config.get('solr_url'),
                             config.get('solr_user'),
                             config.get('solr_password'))
    search.check_solr_schema_version()

    config['routes.map'] = routing.make_map()
    config['pylons.app_globals'] = app_globals.Globals()

    # add helper functions
    restrict_helpers = asbool(config.get('ckan.restrict_template_vars', 'false'))
    helpers = _Helpers(h, restrict_helpers)
    config['pylons.h'] = helpers

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
    config['pylons.app_globals'].genshi_loader = TemplateLoader(
        template_paths, auto_reload=True, callback=template_loaded)

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    # Setup the SQLAlchemy database engine
    # Suppress a couple of sqlalchemy warnings
    warnings.filterwarnings('ignore', '^Unicode type received non-unicode bind param value', sqlalchemy.exc.SAWarning)
    warnings.filterwarnings('ignore', "^Did not recognize type 'BIGINT' of column 'size'", sqlalchemy.exc.SAWarning)
    warnings.filterwarnings('ignore', "^Did not recognize type 'tsvector' of column 'search_vector'", sqlalchemy.exc.SAWarning)

    ckan_db = os.environ.get('CKAN_DB') 

    if ckan_db:
        config['sqlalchemy.url'] = ckan_db
    engine = sqlalchemy.engine_from_config(config, 'sqlalchemy.')

    if not model.meta.engine:
        model.init_model(engine)

    for plugin in p.PluginImplementations(p.IConfigurable):
        plugin.configure(config)

