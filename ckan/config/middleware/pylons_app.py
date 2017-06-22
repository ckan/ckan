# encoding: utf-8

import os
import re

from pylons.wsgiapp import PylonsApp

from beaker.middleware import CacheMiddleware, SessionMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from routes.middleware import RoutesMiddleware
from repoze.who.config import WhoConfig
from repoze.who.middleware import PluggableAuthenticationMiddleware
from fanstatic import Fanstatic

from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IMiddleware
import ckan.lib.uploader as uploader
from ckan.config.middleware import common_middleware
from ckan.common import config

import logging
log = logging.getLogger(__name__)


def make_pylons_stack(conf, full_stack=True, static_files=True,
                      **app_conf):
    """Create a Pylons WSGI application and return it

    ``conf``
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
    # The Pylons WSGI app
    app = pylons_app = CKANPylonsApp()

    for plugin in PluginImplementations(IMiddleware):
        app = plugin.make_middleware(app, config)

    app = common_middleware.RootPathMiddleware(app, config)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    # we want to be able to retrieve the routes middleware to be able to update
    # the mapper.  We store it in the pylons config to allow this.
    config['routes.middleware'] = app
    app = SessionMiddleware(app, config)
    app = CacheMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
    # app = QueueLogMiddleware(app)
    if asbool(config.get('ckan.use_pylons_response_cleanup_middleware',
                         True)):
        app = execute_on_completion(app, config,
                                    cleanup_pylons_response_string)

    # Fanstatic
    if asbool(config.get('debug', False)):
        fanstatic_config = {
            'versioning': True,
            'recompute_hashes': True,
            'minified': False,
            'bottom': True,
            'bundle': False,
        }
    else:
        fanstatic_config = {
            'versioning': True,
            'recompute_hashes': False,
            'minified': True,
            'bottom': True,
            'bundle': True,
        }
    root_path = config.get('ckan.root_path', None)
    if root_path:
        root_path = re.sub('/{{LANG}}', '', root_path)
        fanstatic_config['base_url'] = root_path
    app = Fanstatic(app, **fanstatic_config)

    for plugin in PluginImplementations(IMiddleware):
        try:
            app = plugin.make_error_log_middleware(app, config)
        except AttributeError:
            log.critical('Middleware class {0} is missing the method'
                         'make_error_log_middleware.'
                         .format(plugin.__class__.__name__))

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, conf, **config['pylons.errorware'])

        # Display error documents for 400, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app, [400, 403, 404])
        else:
            app = StatusCodeRedirect(app, [400, 403, 404, 500])

    # Initialize repoze.who
    who_parser = WhoConfig(conf['here'])
    who_parser.parse(open(app_conf['who.config_file']))

    app = PluggableAuthenticationMiddleware(
        app,
        who_parser.identifiers,
        who_parser.authenticators,
        who_parser.challengers,
        who_parser.mdproviders,
        who_parser.request_classifier,
        who_parser.challenge_decider,
        logging.getLogger('repoze.who'),
        logging.WARN,  # ignored
        who_parser.remote_user_key
    )

    # Establish the Registry for this application
    app = RegistryManager(app)

    app = common_middleware.I18nMiddleware(app, config)

    if asbool(static_files):
        # Serve static files
        static_max_age = None if not asbool(
            config.get('ckan.cache_enabled')) \
            else int(config.get('ckan.static_max_age', 3600))

        static_app = StaticURLParser(
            config['pylons.paths']['static_files'],
            cache_max_age=static_max_age)
        static_parsers = [static_app, app]

        storage_directory = uploader.get_storage_path()
        if storage_directory:
            path = os.path.join(storage_directory, 'storage')
            try:
                os.makedirs(path)
            except OSError, e:
                # errno 17 is file already exists
                if e.errno != 17:
                    raise

            storage_app = StaticURLParser(path, cache_max_age=static_max_age)
            static_parsers.insert(0, storage_app)

        # Configurable extra static file paths
        extra_static_parsers = []
        for public_path in config.get(
                'extra_public_paths', '').split(','):
            if public_path.strip():
                extra_static_parsers.append(
                    StaticURLParser(public_path.strip(),
                                    cache_max_age=static_max_age)
                )
        app = Cascade(extra_static_parsers + static_parsers)

    # Page cache
    if asbool(config.get('ckan.page_cache_enabled')):
        app = common_middleware.PageCacheMiddleware(app, config)

    # Tracking
    if asbool(config.get('ckan.tracking_enabled', 'false')):
        app = common_middleware.TrackingMiddleware(app, config)

    # Add a reference to the actual Pylons app so it's easier to access
    app._wsgi_app = pylons_app

    return app


class CKANPylonsApp(PylonsApp):

    app_name = 'pylons_app'

    def can_handle_request(self, environ):
        '''
        Decides whether it can handle a request with the Pylons app by
        matching the request environ against the route mapper

        Returns (True, 'pylons_app', origin) if this is the case.

        origin can be either 'core' or 'extension' depending on where
        the route was defined.

        NOTE: There is currently a catch all route for GET requests to
        point arbitrary urls to templates with the same name:

            map.connect('/*url', controller='template', action='view')

        This means that this function will match all GET requests. This
        does not cause issues as the Pylons core routes are the last to
        take precedence so the current behaviour is kept, but it's worth
        keeping in mind.
        '''

        pylons_mapper = config['routes.map']
        match_route = pylons_mapper.routematch(environ=environ)
        if match_route:
            match, route = match_route
            origin = 'core'
            if hasattr(route, '_ckan_core') and not route._ckan_core:
                origin = 'extension'
            log.debug('Pylons route match: {0} Origin: {1}'.format(
                match, origin))
            return (True, self.app_name, origin)
        else:
            return (False, self.app_name)


def generate_close_and_callback(iterable, callback, environ):
    """
    return a generator that passes through items from iterable
    then calls callback(environ).
    """
    try:
        for item in iterable:
            yield item
    except GeneratorExit:
        if hasattr(iterable, 'close'):
            iterable.close()
        raise
    finally:
        callback(environ)


def execute_on_completion(application, config, callback):
    """
    Call callback(environ) once complete response is sent
    """
    def inner(environ, start_response):
        try:
            result = application(environ, start_response)
        except:
            callback(environ)
            raise
        return generate_close_and_callback(result, callback, environ)
    return inner


def cleanup_pylons_response_string(environ):
    try:
        msg = 'response cleared by pylons response cleanup middleware'
        environ['pylons.controller']._py_object.response._body = msg
    except (KeyError, AttributeError):
        pass
