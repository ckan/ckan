# encoding: utf-8

'''CKAN environment configuration'''
import json
import os
import logging
import warnings
from urlparse import urlparse
import pytz

import sqlalchemy
from pylons import config as pylons_config
import formencode

import ckan.config.routing as routing
import ckan.model as model
import ckan.plugins as p
import ckan.lib.helpers as helpers
import ckan.lib.app_globals as app_globals
from ckan.lib.redis import is_redis_available
import ckan.lib.render as render
import ckan.lib.search as search
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.jinja_extensions as jinja_extensions
from ckan.lib.i18n import build_js_translations

from ckan.common import _, ungettext, config
from ckan.exceptions import CkanConfigurationException

log = logging.getLogger(__name__)


# Suppress benign warning 'Unbuilt egg for setuptools'
warnings.simplefilter('ignore', UserWarning)


def load_environment(global_conf, app_conf):
    """
    Configure the Pylons environment via the ``pylons.config`` object. This
    code should only need to be run once.
    """
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
            ep = pkg_resources.EntryPoint.parse('x={0}'.format(controller))

            if hasattr(ep, 'resolve'):
                # setuptools >= 10.2
                mycontroller = ep.resolve()
            else:
                # setuptools >= 11.3
                mycontroller = ep.load(False)

            self.controller_classes[controller] = mycontroller
            return mycontroller
        return find_controller_generic(self, controller)
    PylonsApp.find_controller = find_controller

    os.environ['CKAN_CONFIG'] = global_conf['__file__']

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    valid_base_public_folder_names = ['public', 'public-bs2']
    static_files = app_conf.get('ckan.base_public_folder', 'public')
    app_conf['ckan.base_public_folder'] = static_files

    if static_files not in valid_base_public_folder_names:
        raise CkanConfigurationException(
            'You provided an invalid value for ckan.base_public_folder. '
            'Possible values are: "public" and "public-bs2".'
        )

    log.info('Loading static files from %s' % static_files)
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, static_files),
                 templates=[])

    # Initialize main CKAN config object
    config.update(global_conf)
    config.update(app_conf)

    # Initialize Pylons own config object
    pylons_config.init_app(global_conf, app_conf, package='ckan', paths=paths)

    # Update the main CKAN config object with the Pylons specific stuff, as it
    # quite hard to keep them separated. This should be removed once Pylons
    # support is dropped
    config.update(pylons_config)

    # Setup the SQLAlchemy database engine
    # Suppress a couple of sqlalchemy warnings
    msgs = ['^Unicode type received non-unicode bind param value',
            "^Did not recognize type 'BIGINT' of column 'size'",
            "^Did not recognize type 'tsvector' of column 'search_vector'"
            ]
    for msg in msgs:
        warnings.filterwarnings('ignore', msg, sqlalchemy.exc.SAWarning)

    # load all CKAN plugins
    p.load_all()

    # Check Redis availability
    if not is_redis_available():
        log.critical('Could not connect to Redis.')

    app_globals.reset()

    # issue #3260: remove idle transaction
    # Session that was used for getting all config params nor committed,
    # neither removed and we have idle connection as result
    model.Session.commit()

    # Build JavaScript translations. Must be done after plugins have
    # been loaded.
    build_js_translations()


# A mapping of config settings that can be overridden by env vars.
# Note: Do not remove the following lines, they are used in the docs
# Start CONFIG_FROM_ENV_VARS
CONFIG_FROM_ENV_VARS = {
    'sqlalchemy.url': 'CKAN_SQLALCHEMY_URL',
    'ckan.datastore.write_url': 'CKAN_DATASTORE_WRITE_URL',
    'ckan.datastore.read_url': 'CKAN_DATASTORE_READ_URL',
    'ckan.redis.url': 'CKAN_REDIS_URL',
    'solr_url': 'CKAN_SOLR_URL',
    'solr_user': 'CKAN_SOLR_USER',
    'solr_password': 'CKAN_SOLR_PASSWORD',
    'ckan.site_id': 'CKAN_SITE_ID',
    'ckan.site_url': 'CKAN_SITE_URL',
    'ckan.storage_path': 'CKAN_STORAGE_PATH',
    'ckan.datapusher.url': 'CKAN_DATAPUSHER_URL',
    'smtp.server': 'CKAN_SMTP_SERVER',
    'smtp.starttls': 'CKAN_SMTP_STARTTLS',
    'smtp.user': 'CKAN_SMTP_USER',
    'smtp.password': 'CKAN_SMTP_PASSWORD',
    'smtp.mail_from': 'CKAN_SMTP_MAIL_FROM',
    'ckan.max_resource_size': 'CKAN_MAX_UPLOAD_SIZE_MB'
}
# End CONFIG_FROM_ENV_VARS


def update_config():
    ''' This code needs to be run when the config is changed to take those
    changes into account. It is called whenever a plugin is loaded as the
    plugin might have changed the config values (for instance it might
    change ckan.site_url) '''

    for plugin in p.PluginImplementations(p.IConfigurer):
        # must do update in place as this does not work:
        # config = plugin.update_config(config)
        plugin.update_config(config)

    # Set whitelisted env vars on config object
    # This is set up before globals are initialized

    ckan_db = os.environ.get('CKAN_DB', None)
    if ckan_db:
        msg = 'Setting CKAN_DB as an env var is deprecated and will be' \
            ' removed in a future release. Use CKAN_SQLALCHEMY_URL instead.'
        log.warn(msg)
        config['sqlalchemy.url'] = ckan_db

    for option in CONFIG_FROM_ENV_VARS:
        from_env = os.environ.get(CONFIG_FROM_ENV_VARS[option], None)
        if from_env:
            config[option] = from_env

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    site_url = config.get('ckan.site_url', '')
    if not site_url:
        raise RuntimeError(
            'ckan.site_url is not configured and it must have a value.'
            ' Please amend your .ini file.')
    if not site_url.lower().startswith('http'):
        raise RuntimeError(
            'ckan.site_url should be a full URL, including the schema '
            '(http or https)')

    display_timezone = config.get('ckan.display_timezone', '')
    if (display_timezone and
            display_timezone != 'server' and
            display_timezone not in pytz.all_timezones):
        raise CkanConfigurationException(
            "ckan.display_timezone is not 'server' or a valid timezone"
        )

    # Remove backslash from site_url if present
    config['ckan.site_url'] = config['ckan.site_url'].rstrip('/')

    ckan_host = config['ckan.host'] = urlparse(site_url).netloc
    if config.get('ckan.site_id') is None:
        if ':' in ckan_host:
            ckan_host, port = ckan_host.split(':')
        assert ckan_host, 'You need to configure ckan.site_url or ' \
                          'ckan.site_id for SOLR search-index rebuild to work.'
        config['ckan.site_id'] = ckan_host

    # ensure that a favicon has been set
    favicon = config.get('ckan.favicon', '/base/images/ckan.ico')
    config['ckan.favicon'] = favicon

    # Init SOLR settings and check if the schema is compatible
    # from ckan.lib.search import SolrSettings, check_solr_schema_version

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
    # routes.named_routes is a CKAN thing
    config['routes.named_routes'] = routing.named_routes
    config['pylons.app_globals'] = app_globals.app_globals

    # initialise the globals
    app_globals.app_globals._init()

    helpers.load_plugin_helpers()
    config['pylons.h'] = helpers.helper_functions

    # Templates and CSS loading from configuration
    valid_base_templates_folder_names = ['templates', 'templates-bs2']
    templates = config.get('ckan.base_templates_folder', 'templates')
    config['ckan.base_templates_folder'] = templates

    if templates not in valid_base_templates_folder_names:
        raise CkanConfigurationException(
            'You provided an invalid value for ckan.base_templates_folder. '
            'Possible values are: "templates" and "templates-bs2".'
        )

    jinja2_templates_path = os.path.join(root, templates)
    log.info('Loading templates from %s' % jinja2_templates_path)
    template_paths = [jinja2_templates_path]

    extra_template_paths = config.get('extra_template_paths', '')
    if extra_template_paths:
        # must be first for them to override defaults
        template_paths = extra_template_paths.split(',') + template_paths
    config['computed_template_paths'] = template_paths

    # Set the default language for validation messages from formencode
    # to what is set as the default locale in the config
    default_lang = config.get('ckan.locale_default', 'en')
    formencode.api.set_stdtranslation(domain="FormEncode",
                                      languages=[default_lang])

    # Markdown ignores the logger config, so to get rid of excessive
    # markdown debug messages in the log, set it to the level of the
    # root logger.
    logging.getLogger("MARKDOWN").setLevel(logging.getLogger().level)

    # Create Jinja2 environment
    env = jinja_extensions.Environment(
        **jinja_extensions.get_jinja_env_options())
    env.install_gettext_callables(_, ungettext, newstyle=True)
    # custom filters
    env.filters['empty_and_escape'] = jinja_extensions.empty_and_escape
    config['pylons.app_globals'].jinja_env = env

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)

    # Initialize SQLAlchemy
    engine = sqlalchemy.engine_from_config(config, client_encoding='utf8')
    model.init_model(engine)

    for plugin in p.PluginImplementations(p.IConfigurable):
        plugin.configure(config)

    # reset the template cache - we do this here so that when we load the
    # environment it is clean
    render.reset_template_info_cache()

    # clear other caches
    logic.clear_actions_cache()
    logic.clear_validators_cache()
    authz.clear_auth_functions_cache()

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

    # Close current session and open database connections to ensure a clean
    # clean environment even if an error occurs later on
    model.Session.remove()
    model.Session.bind.dispose()
