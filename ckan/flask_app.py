# encoding: utf-8

"""Flask application factory for CKAN

This module provides the Flask application factory that replaces the Pylons
WSGI application. It maintains backward compatibility with existing CKAN
plugins and extensions while leveraging Flask's modern features.
"""

import os
import logging
from flask import Flask, g, request, session
from werkzeug.exceptions import HTTPException
import sqlalchemy

import ckan.model as model
import ckan.plugins as p
import ckan.lib.helpers as helpers
import ckan.logic as logic
import ckan.authz as authz
import ckan.lib.app_globals as app_globals
from ckan.common import config
from ckan.lib.redis import is_redis_available
import ckan.lib.jinja_extensions as jinja_extensions
from ckan.common import _, ungettext

log = logging.getLogger(__name__)


def create_app(config_path=None):
    """Create and configure the Flask application

    Args:
        config_path: Path to the CKAN configuration file (INI format)

    Returns:
        Configured Flask application instance
    """
    app = Flask('ckan',
                static_folder='public',
                template_folder='templates')

    # Load configuration
    if config_path:
        load_config(config_path, app)

    # Configure Flask app from CKAN config
    configure_app(app)

    # Register blueprints
    register_blueprints(app)

    # Setup extensions
    setup_extensions(app)

    # Register error handlers
    register_error_handlers(app)

    # Setup template context processors
    setup_template_context(app)

    # Setup before/after request handlers
    setup_request_handlers(app)

    return app


def load_config(config_path, app):
    """Load CKAN configuration from INI file

    Args:
        config_path: Path to configuration file
        app: Flask application instance
    """
    from paste.deploy import appconfig
    import ckan.config.environment as environment

    # Load config using Paste Deploy for compatibility
    conf = appconfig('config:' + config_path)

    # Update global config object
    config.clear()
    config.update(conf)

    # Set environment variable for config path
    os.environ['CKAN_CONFIG'] = config_path

    # Load environment (plugins, database, etc.)
    environment.load_environment(conf.global_conf, conf.local_conf)


def configure_app(app):
    """Configure Flask application with CKAN settings

    Args:
        app: Flask application instance
    """
    # Flask configuration from CKAN config
    app.config['SECRET_KEY'] = config.get('beaker.session.secret')
    app.config['MAX_CONTENT_LENGTH'] = int(config.get('ckan.max_resource_size', 10)) * 1024 * 1024
    app.config['DEBUG'] = asbool(config.get('debug', False))

    # Session configuration
    app.config['SESSION_COOKIE_NAME'] = 'ckan'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = config.get('ckan.site_url', '').startswith('https')

    # Template configuration
    app.jinja_env.autoescape = True
    app.jinja_env.auto_reload = app.config['DEBUG']

    # Add CKAN template paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_paths = [os.path.join(root, 'ckan', 'templates')]

    extra_template_paths = config.get('extra_template_paths', '')
    if extra_template_paths:
        template_paths = extra_template_paths.split(',') + template_paths

    # Use CKAN's Jinja extensions
    app.jinja_env.add_extension('jinja2.ext.do')
    app.jinja_env.add_extension('jinja2.ext.with_')
    app.jinja_env.add_extension(jinja_extensions.SnippetExtension)
    app.jinja_env.add_extension(jinja_extensions.CkanExtend)
    app.jinja_env.add_extension(jinja_extensions.CkanInternationalizationExtension)
    app.jinja_env.add_extension(jinja_extensions.LinkForExtension)
    app.jinja_env.add_extension(jinja_extensions.ResourceExtension)
    app.jinja_env.add_extension(jinja_extensions.UrlForStaticExtension)
    app.jinja_env.add_extension(jinja_extensions.UrlForExtension)

    # Install i18n
    app.jinja_env.install_gettext_callables(_, ungettext, newstyle=True)

    # Add custom filters
    app.jinja_env.filters['empty_and_escape'] = jinja_extensions.empty_and_escape
    app.jinja_env.filters['truncate'] = jinja_extensions.truncate

    # Add template helpers
    app.jinja_env.globals.update(helpers.helper_functions)


def register_blueprints(app):
    """Register Flask blueprints for all CKAN controllers

    Args:
        app: Flask application instance
    """
    # Import blueprints
    from ckan.blueprints.home import home
    from ckan.blueprints.package import package
    from ckan.blueprints.group import group
    from ckan.blueprints.organization import organization
    from ckan.blueprints.user import user
    from ckan.blueprints.api import api
    from ckan.blueprints.admin import admin
    from ckan.blueprints.feed import feed
    from ckan.blueprints.tag import tag

    # Register core blueprints
    app.register_blueprint(home)
    app.register_blueprint(package, url_prefix='/dataset')
    app.register_blueprint(group, url_prefix='/group')
    app.register_blueprint(organization, url_prefix='/organization')
    app.register_blueprint(user, url_prefix='/user')
    app.register_blueprint(api, url_prefix='/api')
    app.register_blueprint(admin, url_prefix='/ckan-admin')
    app.register_blueprint(feed, url_prefix='/feeds')
    app.register_blueprint(tag, url_prefix='/tag')

    # Allow plugins to register their own blueprints
    for plugin in p.PluginImplementations(p.IBlueprint):
        plugin.register_blueprint(app)


def setup_extensions(app):
    """Setup Flask extensions and CKAN components

    Args:
        app: Flask application instance
    """
    # Initialize database
    engine = sqlalchemy.engine_from_config(config, client_encoding='utf8')
    model.init_model(engine)

    # Check Redis
    if not is_redis_available():
        log.warning('Redis is not available. Some features may not work.')

    # Initialize app globals
    app_globals.reset()
    app_globals.app_globals._init()

    # Load helper functions
    helpers.load_plugin_helpers()

    # Call plugin configure methods
    for plugin in p.PluginImplementations(p.IConfigurable):
        plugin.configure(config)


def register_error_handlers(app):
    """Register error handlers for common HTTP errors

    Args:
        app: Flask application instance
    """
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('error_document_template.html',
                             code=404,
                             content='Page not found'), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        log.error('Internal server error: %s', error)
        return render_template('error_document_template.html',
                             code=500,
                             content='Internal server error'), 500

    @app.errorhandler(logic.NotAuthorized)
    def handle_not_authorized(error):
        from flask import render_template
        return render_template('error_document_template.html',
                             code=403,
                             content=str(error)), 403

    @app.errorhandler(logic.NotFound)
    def handle_not_found(error):
        from flask import render_template
        return render_template('error_document_template.html',
                             code=404,
                             content=str(error)), 404

    @app.errorhandler(logic.ValidationError)
    def handle_validation_error(error):
        from flask import render_template, jsonify, request
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': error.error_dict}), 400
        return render_template('error_document_template.html',
                             code=400,
                             content=str(error)), 400


def setup_template_context(app):
    """Setup template context processors

    Args:
        app: Flask application instance
    """
    @app.context_processor
    def inject_common_variables():
        """Inject common template variables (c, g, h, etc.)"""
        return {
            'c': g,  # Compatibility: 'c' was the Pylons context variable
            'h': helpers.helper_functions,
            'request': request,
            'session': session,
            'config': config,
        }


def setup_request_handlers(app):
    """Setup before/after request handlers

    Args:
        app: Flask application instance
    """
    @app.before_request
    def before_request():
        """Called before each request"""
        # Set up g (global context) for this request
        g.user = None
        g.userobj = None

        # Get user from session or API key
        user = session.get('user')
        if user:
            g.user = user
            g.userobj = model.User.get(user)

        # Check for API key in headers
        api_key = request.headers.get('X-CKAN-API-Key') or request.args.get('api_key')
        if api_key:
            user_obj = model.User.get_by_apikey(api_key)
            if user_obj:
                g.user = user_obj.name
                g.userobj = user_obj

        # Set up action context
        g.context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'userobj': g.userobj
        }

    @app.after_request
    def after_request(response):
        """Called after each request"""
        # Commit or rollback database session
        if response.status_code >= 400:
            model.Session.rollback()
        else:
            try:
                model.Session.commit()
            except Exception as e:
                log.error('Failed to commit session: %s', e)
                model.Session.rollback()
                raise

        model.Session.remove()
        return response

    @app.teardown_request
    def teardown_request(exception=None):
        """Called when tearing down request context"""
        if exception:
            log.error('Request exception: %s', exception)
            model.Session.rollback()
        model.Session.remove()


def asbool(value):
    """Convert string value to boolean"""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', 'yes', '1', 'on')
    return bool(value)


# WSGI application factory for compatibility with deployment tools
def make_app(global_config, **app_config):
    """WSGI application factory

    This maintains compatibility with Paste Deploy and existing deployment
    configurations.

    Args:
        global_config: Global configuration dict
        **app_config: Application-specific configuration

    Returns:
        WSGI application instance
    """
    config_path = global_config.get('__file__')
    app = create_app(config_path)
    return app
