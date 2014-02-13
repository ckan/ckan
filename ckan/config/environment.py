# -*- coding: utf-8 -*-
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
import ckan.lib.app_globals as app_globals
import ckan.lib.render as render
import ckan.lib.search as search
import ckan.logic as logic
import ckan.new_authz as new_authz
import ckan.lib.jinja_extensions as jinja_extensions

from ckan.common import _, ungettext

log = logging.getLogger(__name__)


# Suppress benign warning 'Unbuilt egg for setuptools'
warnings.simplefilter('ignore', UserWarning)


class _Helpers(object):
    ''' Helper object giving access to template helpers stopping
    missing functions from causing template exceptions. Useful if
    templates have helper functions provided by extensions that have
    not been enabled. '''
    def __init__(self, helpers):
        self.helpers = helpers
        self._setup()

    def _setup(self):
        helpers = self.helpers
        functions = {}
        allowed = helpers.__allowed_functions__[:]
        # list of functions due to be deprecated
        self.deprecated = []

        for helper in dir(helpers):
            if helper not in allowed:
                self.deprecated.append(helper)
                continue
            functions[helper] = getattr(helpers, helper)
            if helper in allowed:
                allowed.remove(helper)
        self.functions = functions

        if allowed:
            raise Exception('Template helper function(s) `%s` not defined'
                            % ', '.join(allowed))

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
            if name in self.deprecated:
                msg = 'Template helper function `%s` is deprecated' % name
                self.log.warn(msg)
            return self.functions[name]
        else:
            if name in self.deprecated:
                msg = ('Template helper function `{0}` is not available '
                       'because it has been deprecated.'.format(name))
                self.log.critical(msg)
            else:
                msg = 'Helper function `%s` could not be found\n ' \
                      '(are you missing an extension?)' % name
                self.log.critical(msg)
            return self.null_function


def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config``
    object.  This code should only need to be run once.
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
            mycontroller = pkg_resources \
                .EntryPoint \
                .parse('x=%s' % controller).load(False)
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
                 templates=[])

    # Initialize config with the basic options
    config.init_app(global_conf, app_conf, package='ckan', paths=paths)

    #################################################################
    #                                                               #
    #                   HORRIBLE GENSHI HACK                        #
    #                                                               #
    #################################################################
    #                                                               #
    # Genshi does strange things to get stuff out of the template   #
    # variables.  This stops it from handling properties in the     #
    # correct way as it returns the property rather than the actual #
    # value of the property.                                        #
    #                                                               #
    # By overriding lookup_attr() in the LookupBase class we are    #
    # able to get the required behaviour.  Using @property allows   #
    # us to move functionality out of templates whilst maintaining  #
    # backwards compatability.                                      #
    #                                                               #
    #################################################################

    '''
    This code is based on Genshi code

    Copyright © 2006-2012 Edgewall Software
    All rights reserved.

    Redistribution and use in source and binary forms, with or
    without modification, are permitted provided that the following
    conditions are met:

        Redistributions of source code must retain the above copyright
        notice, this list of conditions and the following disclaimer.

        Redistributions in binary form must reproduce the above
        copyright notice, this list of conditions and the following
        disclaimer in the documentation and/or other materials provided
        with the distribution.

        The name of the author may not be used to endorse or promote
        products derived from this software without specific prior
        written permission.

    THIS SOFTWARE IS PROVIDED BY THE AUTHOR "AS IS" AND ANY EXPRESS OR
    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
    ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY
    DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
    DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
    GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
    INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
    IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
    OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
    IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    '''
    from genshi.template.eval import LookupBase

    @classmethod
    def genshi_lookup_attr(cls, obj, key):
        __traceback_hide__ = True
        try:
            val = getattr(obj, key)
        except AttributeError:
            if hasattr(obj.__class__, key):
                raise
            else:
                try:
                    val = obj[key]
                except (KeyError, TypeError):
                    val = cls.undefined(key, owner=obj)
        if isinstance(val, property):
            val = val.fget()
        return val

    setattr(LookupBase, 'lookup_attr', genshi_lookup_attr)
    del genshi_lookup_attr
    del LookupBase

    #################################################################
    #                                                               #
    #                       END OF GENSHI HACK                      #
    #                                                               #
    #################################################################

    # Setup the SQLAlchemy database engine
    # Suppress a couple of sqlalchemy warnings
    msgs = ['^Unicode type received non-unicode bind param value',
            "^Did not recognize type 'BIGINT' of column 'size'",
            "^Did not recognize type 'tsvector' of column 'search_vector'"
            ]
    for msg in msgs:
        warnings.filterwarnings('ignore', msg, sqlalchemy.exc.SAWarning)

    # load all CKAN plugins
    p.load_all(config)


def update_config():
    ''' This code needs to be run when the config is changed to take those
    changes into account. '''

    for plugin in p.PluginImplementations(p.IConfigurer):
        # must do update in place as this does not work:
        # config = plugin.update_config(config)
        plugin.update_config(config)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    # ensure that a favicon has been set
    favicon = config.get('ckan.favicon', '/images/icons/ckan.ico')
    config['ckan.favicon'] = favicon

    # Init SOLR settings and check if the schema is compatible
    #from ckan.lib.search import SolrSettings, check_solr_schema_version

    # lib.search is imported here as we need the config enabled and parsed
    search.SolrSettings.init(config.get('solr_url'),
                             config.get('solr_user'),
                             config.get('solr_password'))
    search.check_solr_schema_version()

    routes_map = routing.make_map()
    config['routes.map'] = routes_map
    # The RoutesMiddleware needs its mapper updating if it exists
    if 'routes.middleware' in config:
        config['routes.middleware'].mapper = routes_map
    config['routes.named_routes'] = routing.named_routes
    config['pylons.app_globals'] = app_globals.app_globals
    # initialise the globals
    config['pylons.app_globals']._init()

    # add helper functions
    helpers = _Helpers(h)
    config['pylons.h'] = helpers

    ## redo template setup to use genshi.search_path
    ## (so remove std template setup)
    legacy_templates_path = os.path.join(root, 'templates_legacy')
    jinja2_templates_path = os.path.join(root, 'templates')
    if asbool(config.get('ckan.legacy_templates', 'no')):
        # We want the new template path for extra snippets like the
        # dataviewer and also for some testing stuff
        template_paths = [legacy_templates_path, jinja2_templates_path]
    else:
        template_paths = [jinja2_templates_path, legacy_templates_path]

    extra_template_paths = config.get('extra_template_paths', '')
    if extra_template_paths:
        # must be first for them to override defaults
        template_paths = extra_template_paths.split(',') + template_paths
    config['pylons.app_globals'].template_paths = template_paths

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

    # Create Jinja2 environment
    env = jinja_extensions.Environment(
        loader=jinja_extensions.CkanFileSystemLoader(template_paths),
        autoescape=True,
        extensions=['jinja2.ext.do', 'jinja2.ext.with_',
                    jinja_extensions.SnippetExtension,
                    jinja_extensions.CkanExtend,
                    jinja_extensions.CkanInternationalizationExtension,
                    jinja_extensions.LinkForExtension,
                    jinja_extensions.ResourceExtension,
                    jinja_extensions.UrlForStaticExtension,
                    jinja_extensions.UrlForExtension]
    )
    env.install_gettext_callables(_, ungettext, newstyle=True)
    # custom filters
    env.filters['empty_and_escape'] = jinja_extensions.empty_and_escape
    env.filters['truncate'] = jinja_extensions.truncate
    config['pylons.app_globals'].jinja_env = env

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    ckan_db = os.environ.get('CKAN_DB')
    if ckan_db:
        config['sqlalchemy.url'] = ckan_db

    # for postgresql we want to enforce utf-8
    sqlalchemy_url = config.get('sqlalchemy.url', '')
    if sqlalchemy_url.startswith('postgresql://'):
        extras = {'client_encoding': 'utf8'}
    else:
        extras = {}

    engine = sqlalchemy.engine_from_config(config, 'sqlalchemy.', **extras)

    if not model.meta.engine:
        model.init_model(engine)

    for plugin in p.PluginImplementations(p.IConfigurable):
        plugin.configure(config)

    # reset the template cache - we do this here so that when we load the
    # environment it is clean
    render.reset_template_info_cache()

    # clear other caches
    logic.clear_actions_cache()
    new_authz.clear_auth_functions_cache()

    # Here we create the site user if they are not already in the database
    try:
        logic.get_action('get_site_user')({'ignore_auth': True}, None)
    except (sqlalchemy.exc.ProgrammingError, sqlalchemy.exc.OperationalError):
        # (ProgrammingError for Postgres, OperationalError for SQLite)
        # The database is not initialised.  This is a bit dirty.  This occurs
        # when running tests.
        pass
    except sqlalchemy.exc.InternalError:
        # The database is not initialised.  Travis hits this
        pass
    # if an extension or our code does not finish
    # transaction properly db cli commands can fail
    model.Session.remove()
