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
from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IMiddleware

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

    for plugin in PluginImplementations(IMiddleware):
        app = plugin.make_middleware(app, config)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    app = SessionMiddleware(app, config)
    app = I18nMiddleware(app, config)
    app = CacheMiddleware(app, config)
    
    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
    #app = QueueLogMiddleware(app)
    
    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app, [400, 404])
        else:
            app = StatusCodeRedirect(app, [400, 404, 500])
    
    # Initialize repoze.who
    who_parser = WhoConfig(global_conf['here'])
    who_parser.parse(open(app_conf['who.config_file']))

    if asbool(config.get('openid_enabled', 'true')):
        from repoze.who.plugins.openid.identification import OpenIdIdentificationPlugin
        # Monkey patches for repoze.who.openid
        # Fixes #1659 - enable log-out when CKAN mounted at non-root URL 
        from ckan.lib import repoze_patch
        OpenIdIdentificationPlugin.identify = repoze_patch.identify
        OpenIdIdentificationPlugin.redirect_to_logged_in = repoze_patch.redirect_to_logged_in
        OpenIdIdentificationPlugin._redirect_to_loginform = repoze_patch._redirect_to_loginform
        OpenIdIdentificationPlugin.challenge = repoze_patch.challenge

        who_parser.identifiers = [i for i in who_parser.identifiers if \
                not isinstance(i, OpenIdIdentificationPlugin)]
        who_parser.challengers = [i for i in who_parser.challengers if \
                not isinstance(i, OpenIdIdentificationPlugin)]
    
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
        static_max_age = None if not asbool(config.get('ckan.cache_enabled')) \
            else int(config.get('ckan.static_max_age', 3600))

        static_app = StaticURLParser(config['pylons.paths']['static_files'],
                cache_max_age=static_max_age)
        static_parsers = [static_app, app]

        # Configurable extra static file paths
        extra_static_parsers = []
        for public_path in config.get('extra_public_paths', '').split(','):
            if public_path.strip():
                extra_static_parsers.append(
                    StaticURLParser(public_path.strip(),
                        cache_max_age=static_max_age)
                )
        app = Cascade(extra_static_parsers+static_parsers)

    return app

class I18nMiddleware(object):
    """I18n Middleware selects the language based on the url
    eg /fr/home is French"""
    def __init__(self, app, config):
        self.app = app
        self.default_locale = config['ckan.locale_default']
        self.local_list = config['ckan.locale_order'].split()
        # we want to know the root of the site in case it is in a
        # subdirectory so that we can correctly rewrite the urls.

    def __call__(self, environ, start_response):
        # strip the language selector from the requested url
        # and set environ variables for the language selected
        # CKAN_LANG is the language code eg en, fr
        # CKAN_LANG_IS_DEFAULT is set to True or False
        path_parts = environ['PATH_INFO'].split('/')
        if len(path_parts) > 1 and path_parts[1] in self.local_list:
            environ['CKAN_LANG'] = path_parts[1]
            environ['CKAN_LANG_IS_DEFAULT'] = False
            # rewrite url
            if len(path_parts) > 2:
                environ['PATH_INFO'] = '/'.join([''] + path_parts[2:])
            else:
                environ['PATH_INFO'] = '/'
        else:
            # See if we have a language the browser requests. If this is
            # not the site default language then redirect to that
            # language eg for french -> /fr/....
            browser_langs = environ.get('HTTP_ACCEPT_LANGUAGE', 'en')
            languages = browser_langs.split(';')[0].split(',')
            for language in languages:
                if language in self.local_list:
                    if language != self.default_locale:
                        # if this is not the default locale of the site
                        # then we will redirect to the url using that
                        # language here.
                        root = environ['SCRIPT_NAME']
                        url = environ['PATH_INFO']
                        url = url[len(root):]
                        url = '/%s%s%s' % (root, language,  url)
                        start_response('200 OK', [('Content-Type', 'text/html'),('Refresh', '0; url=%s' % url)])
                        return []
                    break
            # use default language from config
            environ['CKAN_LANG'] = self.default_locale
            environ['CKAN_LANG_IS_DEFAULT'] = True
        return self.app(environ, start_response)
