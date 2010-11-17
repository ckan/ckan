"""Pylons middleware initialization"""
import logging 

from beaker.middleware import CacheMiddleware, SessionMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons import config
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware
from repoze.who.config import WhoConfig
from repoze.who.middleware import PluggableAuthenticationMiddleware

from ckan.config.environment import load_environment

def make_app(global_conf, full_stack=True, static_files=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether this application provides a full WSGI stack (by default,
        meaning it handles its own exceptions and errors). Disable
        full_stack when this application is "managed" by another WSGI
        middleware.

    ``static_files``
        Whether this application serves its own static files; disable
        when another web server is responsible for serving them.

    ``app_conf``
        The application's local configuration. Normally specified in
        the [app:<name>] section of the Paste ini file (where <name>
        defaults to main).

    """
    # Configure the Pylons environment
    load_environment(global_conf, app_conf)

    # The Pylons WSGI app
    app = PylonsApp()

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    app = SessionMiddleware(app, config)
    app = CacheMiddleware(app, config)
    
    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
    #app = QueueLogMiddleware(app)
    
    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])
    
    # Initialize repoze.who
    who_parser = WhoConfig(global_conf['here'])
    who_parser.parse(open(app_conf['who.config_file']))
    app = PluggableAuthenticationMiddleware(app,
                    who_parser.identifiers,
                    who_parser.authenticators,
                    who_parser.challengers,
                    who_parser.mdproviders,
                    who_parser.request_classifier,
                    who_parser.challenge_decider,
                    logging.getLogger('repoze.who'),
                    logging.WARN, # ignored
                    who_parser.remote_user_key,
               )
    
    # Establish the Registry for this application
    app = RegistryManager(app)

    if asbool(static_files):
        # Serve static files
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        static_parsers = [static_app, app]

        # Configurable extra static file paths
        extra_public_paths = config.get('extra_public_paths')
        if extra_public_paths:
            static_parsers = [StaticURLParser(public_path) \
                              for public_path in \
                              extra_public_paths.split(',')] + static_parsers
            
        app = Cascade(static_parsers)
    
    return app
