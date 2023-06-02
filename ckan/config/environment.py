# encoding: utf-8
'''CKAN environment configuration'''
from __future__ import annotations

import os
import logging
import warnings
import pytz

from typing import Union, cast

import sqlalchemy
import sqlalchemy.exc

import ckan.model as model
import ckan.plugins as p
import ckan.lib.plugins as lib_plugins
import ckan.lib.helpers as helpers
import ckan.lib.app_globals as app_globals
from ckan.lib.redis import is_redis_available
import ckan.lib.search as search
import ckan.logic as logic
import ckan.authz as authz
from ckan.lib.webassets_tools import webassets_init
from ckan.lib.i18n import build_js_translations

from ckan.common import CKANConfig, config, config_declaration
from ckan.exceptions import CkanConfigurationException
from ckan.types import Config

log = logging.getLogger(__name__)

# Suppress benign warning 'Unbuilt egg for setuptools'
warnings.simplefilter('ignore', UserWarning)


def load_environment(conf: Union[Config, CKANConfig]):
    """
    Configure the Pylons environment via the ``pylons.config`` object. This
    code should only need to be run once.
    """
    os.environ['CKAN_CONFIG'] = cast(str, conf['__file__'])

    valid_base_public_folder_names = ['public', 'public-bs3']
    static_files = conf.get('ckan.base_public_folder', 'public')
    conf['ckan.base_public_folder'] = static_files

    if static_files not in valid_base_public_folder_names:
        raise CkanConfigurationException(
            'You provided an invalid value for ckan.base_public_folder. '
            'Possible values are: "public" and "public-bs3".'
        )

    log.info('Loading static files from %s' % static_files)

    # Initialize main CKAN config object
    config.update(conf)

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

    # Build JavaScript translations. Must be done after plugins have
    # been loaded.
    build_js_translations()


# A mapping of config settings that can be overridden by env vars.
# Note: Do not remove the following lines, they are used in the docs
# Start CONFIG_FROM_ENV_VARS
CONFIG_FROM_ENV_VARS: dict[str, str] = {
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


def update_config() -> None:
    ''' This code needs to be run when the config is changed to take those
    changes into account. It is called whenever a plugin is loaded as the
    plugin might have changed the config values (for instance it might
    change ckan.site_url) '''

    for option in CONFIG_FROM_ENV_VARS:
        from_env = os.environ.get(CONFIG_FROM_ENV_VARS[option], None)
        if from_env:
            config[option] = from_env

    config_declaration.setup()
    config_declaration.make_safe(config)
    config_declaration.normalize(config)

    webassets_init()

    # these are collections of all template/public paths registered by
    # extensions. Each call to `tk.add_template_directory` or
    # `tk.add_public_directory` updates these collections. We have to reset
    # them in order to remove templates/public files that came from plugins
    # that were once enabled but are disabled right now.
    config["plugin_template_paths"] = []
    config["plugin_public_paths"] = []

    for plugin in reversed(list(p.PluginImplementations(p.IConfigurer))):
        # must do update in place as this does not work:
        # config = plugin.update_config(config)
        plugin.update_config(config)

    _, errors = config_declaration.validate(config)
    if errors:
        if config.get("config.mode") == "strict":
            msg = "\n".join(
                "{}: {}".format(key, "; ".join(issues))
                for key, issues in errors.items()
            )
            msg = "Invalid configuration values provided:\n" + msg
            raise CkanConfigurationException(msg)
        else:
            for key, issues in errors.items():
                log.warning(
                    "Invalid value for %s (%s): %s",
                    key,
                    config.get(key),
                    "; ".join(issues)
                )

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    site_url = config.get('ckan.site_url')
    if not site_url:
        raise RuntimeError(
            'ckan.site_url is not configured and it must have a value.'
            ' Please amend your .ini file.')
    if not site_url.lower().startswith('http'):
        raise RuntimeError(
            'ckan.site_url should be a full URL, including the schema '
            '(http or https)')
    # Remove backslash from site_url if present
    config['ckan.site_url'] = site_url.rstrip('/')

    display_timezone = config.get('ckan.display_timezone')
    if (display_timezone and
            display_timezone != 'server' and
            display_timezone not in pytz.all_timezones):
        raise CkanConfigurationException(
            "ckan.display_timezone is not 'server' or a valid timezone"
        )

    # Init SOLR settings and check if the schema is compatible
    # from ckan.lib.search import SolrSettings, check_solr_schema_version

    # lib.search is imported here as we need the config enabled and parsed
    search.SolrSettings.init(config.get('solr_url'),
                             config.get('solr_user'),
                             config.get('solr_password'))
    search.check_solr_schema_version()

    lib_plugins.reset_package_plugins()
    lib_plugins.register_package_plugins()
    lib_plugins.reset_group_plugins()
    lib_plugins.register_group_plugins()

    # initialise the globals
    app_globals.app_globals._init()

    helpers.load_plugin_helpers()

    # Templates and CSS loading from configuration
    valid_base_templates_folder_names = ['templates', 'templates-bs3']
    templates = config.get('ckan.base_templates_folder')
    config['ckan.base_templates_folder'] = templates

    if templates not in valid_base_templates_folder_names:
        raise CkanConfigurationException(
            'You provided an invalid value for ckan.base_templates_folder. '
            'Possible values are: "templates" and "templates-bs3".'
        )

    jinja2_templates_path = os.path.join(root, templates)
    log.info('Loading templates from %s' % jinja2_templates_path)
    template_paths = [jinja2_templates_path]

    extra_template_paths = config.get('extra_template_paths')
    if 'plugin_template_paths' in config:
        template_paths = config['plugin_template_paths'] + template_paths
    if extra_template_paths:
        # must be first for them to override defaults
        template_paths = extra_template_paths.split(',') + template_paths
    config['computed_template_paths'] = template_paths

    # Enable pessimistic disconnect handling (added in SQLAlchemy 1.2)
    # to eliminate database errors due to stale pooled connections
    config.setdefault('sqlalchemy.pool_pre_ping', True)
    # Initialize SQLAlchemy
    engine = sqlalchemy.engine_from_config(config)
    model.init_model(engine)

    for plugin in p.PluginImplementations(p.IConfigurable):
        plugin.configure(config)

    # clear other caches
    logic.clear_actions_cache()
    logic.clear_validators_cache()
    authz.clear_auth_functions_cache()

    # Here we create the site user if they are not already in the database
    try:
        logic.get_action('get_site_user')({'ignore_auth': True}, {})
    except (sqlalchemy.exc.ProgrammingError, sqlalchemy.exc.OperationalError):
        # The database is not yet initialised. It happens in `ckan db init`
        pass
    except sqlalchemy.exc.IntegrityError:
        # Race condition, user already exists.
        pass

    # Close current session and open database connections to ensure a clean
    # clean environment even if an error occurs later on
    model.Session.remove()
    model.Session.bind.dispose()
