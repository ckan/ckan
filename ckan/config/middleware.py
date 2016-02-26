"""Pylons middleware initialization"""
import urllib
import urllib2
import logging
import json
import hashlib
import os

import sqlalchemy as sa
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
from fanstatic import Fanstatic

from wsgi_party import WSGIParty, HighAndDry
from flask import Flask
from flask import abort as flask_abort
from flask import request as flask_request
from flask import _request_ctx_stack
from werkzeug.exceptions import HTTPException
from werkzeug.test import create_environ, run_wsgi_app

from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IMiddleware
from ckan.lib.i18n import get_locales_from_config
import ckan.lib.uploader as uploader

from ckan.config.environment import load_environment
import ckan.lib.app_globals as app_globals

log = logging.getLogger(__name__)


def make_app(conf, full_stack=True, static_files=True, **app_conf):

    # :::TODO::: like the flask app, make the pylons app respond to invites at
    # /__invite__/, and handle can_handle_request requests.

    pylons_app = make_pylons_stack(conf, full_stack, static_files, **app_conf)
    flask_app = make_flask_stack(conf)

    app = AskAppDispatcherMiddleware({'pylons_app': pylons_app, 'flask_app': flask_app})

    return app


def make_pylons_stack(conf, full_stack=True, static_files=True, **app_conf):
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
    # Configure the Pylons environment
    load_environment(conf, app_conf)

    # The Pylons WSGI app
    app = PylonsApp()
    # set pylons globals
    app_globals.reset()

    for plugin in PluginImplementations(IMiddleware):
        app = plugin.make_middleware(app, config)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    # we want to be able to retrieve the routes middleware to be able to update
    # the mapper.  We store it in the pylons config to allow this.
    config['routes.middleware'] = app
    app = SessionMiddleware(app, config)
    app = CacheMiddleware(app, config)

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)
    # app = QueueLogMiddleware(app)
    if asbool(config.get('ckan.use_pylons_response_cleanup_middleware', True)):
        app = execute_on_completion(app, config, cleanup_pylons_response_string)

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
    app = Fanstatic(app, **fanstatic_config)

    for plugin in PluginImplementations(IMiddleware):
        try:
            app = plugin.make_error_log_middleware(app, config)
        except AttributeError:
            log.critical('Middleware class {0} is missing the method'
                         'make_error_log_middleware.'.format(plugin.__class__.__name__))

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app, [400, 404])
        else:
            app = StatusCodeRedirect(app, [400, 404, 500])

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

    app = I18nMiddleware(app, config)

    if asbool(static_files):
        # Serve static files
        static_max_age = None if not asbool(config.get('ckan.cache_enabled')) \
            else int(config.get('ckan.static_max_age', 3600))

        static_app = StaticURLParser(config['pylons.paths']['static_files'],
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
        for public_path in config.get('extra_public_paths', '').split(','):
            if public_path.strip():
                extra_static_parsers.append(
                    StaticURLParser(public_path.strip(),
                                    cache_max_age=static_max_age)
                )
        app = Cascade(extra_static_parsers + static_parsers)

    # Page cache
    if asbool(config.get('ckan.page_cache_enabled')):
        app = PageCacheMiddleware(app, config)

    # Tracking
    if asbool(config.get('ckan.tracking_enabled', 'false')):
        app = TrackingMiddleware(app, config)

    return app


def make_flask_stack(conf):
    """ This has to pass the flask app through all the same middleware that
    Pylons used """

    app = CKANFlask(__name__)

    @app.route('/hello', methods=['GET'])
    def hello_world():
        return 'Hello World, this is served by Flask'

    return app


class CKANFlask(Flask):

    '''Extend the Flask class with a special view to join the 'partyline'
    established by AskAppDispatcherMiddleware.

    Also provide a 'can_handle_request' method.
    '''

    def __init__(self, import_name, *args, **kwargs):
        super(CKANFlask, self).__init__(import_name, *args, **kwargs)
        self.add_url_rule('/__invite__/', endpoint='partyline',
                          view_func=self.join_party)
        self.partyline = None
        self.connected = False
        self.invitation_context = None
        self.app_name = None  # A label for the app handling this request
                              # (this app).

    def join_party(self, request=flask_request):
        # Bootstrap, turn the view function into a 404 after registering.
        if self.connected:
            # This route does not exist at the HTTP level.
            flask_abort(404)
        self.invitation_context = _request_ctx_stack.top
        self.partyline = request.environ.get(WSGIParty.partyline_key)
        self.app_name = request.environ.get('partyline_handling_app')
        self.partyline.connect('can_handle_request', self.can_handle_request)
        self.connected = True
        return 'ok'

    def can_handle_request(self, environ):
        '''
        Decides whether it can handle a request with the Flask app by
        matching the request environ against the route mapper

        Returns (True, 'flask_app') if this is the case.
        '''

        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()

            log.debug('Flask route match, endpoint: {0}, args: {1}'.format(
                endpoint, args))
            return (True, self.app_name)
        except HTTPException:
            raise HighAndDry()


class AskAppDispatcherMiddleware(WSGIParty):

    '''
    Establish a 'partyline' to each provided app. Select which app to call
    by asking each if they can handle the requested path at PATH_INFO.

    Used to help transition from Pylons to Flask, and should be removed once
    Pylons has been deprecated and all app requests are handled by Flask.

    Each app should handle a call to 'can_handle_request(environ)', responding
    with a tuple:
        (<bool>, <app>, [<origin>])
    where:
       `bool` is True if the app can handle the payload url,
       `app` is the wsgi app returning the answer
       `origin` is an optional string to determine where in the app the url
        will be handled, e.g. 'core' or 'extension'.

    Order of precedence if more than one app can handle a url:
        Flask Extension > Pylons Extension > Flask Core > Pylons Core
    '''

    def __init__(self, apps=None, invites=(), ignore_missing_services=False):
        # Dict of apps managed by this middleware {<app_name>: <app_obj>, ...}
        self.apps = apps or {}

        # A dict of service name => handler mappings.
        self.handlers = {}

        # If True, suppress :class:`NoSuchServiceName` errors. Default: False.
        self.ignore_missing_services = ignore_missing_services

        self.send_invitations(apps)

    def send_invitations(self, apps):
        '''Call each app at the invite route to establish a partyline. Called
        on init.'''
        PATH = '/__invite__/'
        for app_name, app in apps.items():
            environ = create_environ(path=PATH)
            environ[self.partyline_key] = self.operator_class(self)
            # A reference to the handling app. Used to id the app when
            # responding to a handling request.
            environ['partyline_handling_app'] = app_name
            run_wsgi_app(app, environ)

    def __call__(self, environ, start_response):
        '''Determine which app to call by asking each app if it can handle the
        url and method defined on the eviron'''
        # :::TODO::: Enforce order of precedence for dispatching to apps here.

        app_name = 'pylons_app'  # currently defaulting to pylons app
        answers = self.ask_around('can_handle_request', environ)
        for answer in answers:
            can_handle, asked_app = answer
            if can_handle:
                app_name = asked_app
                break

        log.debug('Route support answers for {0} {1}: {2}'.format(
            environ.get('REQUEST_METHOD'), environ.get('PATH_INFO'),
            answers))
        log.debug('Serving request via {0} app'.format(app_name))
        return self.apps[app_name](environ, start_response)


class I18nMiddleware(object):
    """I18n Middleware selects the language based on the url
    eg /fr/home is French"""
    def __init__(self, app, config):
        self.app = app
        self.default_locale = config.get('ckan.locale_default', 'en')
        self.local_list = get_locales_from_config()

    def __call__(self, environ, start_response):
        # strip the language selector from the requested url
        # and set environ variables for the language selected
        # CKAN_LANG is the language code eg en, fr
        # CKAN_LANG_IS_DEFAULT is set to True or False
        # CKAN_CURRENT_URL is set to the current application url

        # We only update once for a request so we can keep
        # the language and original url which helps with 404 pages etc
        if 'CKAN_LANG' not in environ:
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
                environ['CKAN_LANG'] = self.default_locale
                environ['CKAN_LANG_IS_DEFAULT'] = True

            # Current application url
            path_info = environ['PATH_INFO']
            # sort out weird encodings
            path_info = '/'.join(urllib.quote(pce, '') for pce in path_info.split('/'))

            qs = environ.get('QUERY_STRING')

            if qs:
                # sort out weird encodings
                qs = urllib.quote(qs, '')
                environ['CKAN_CURRENT_URL'] = '%s?%s' % (path_info, qs)
            else:
                environ['CKAN_CURRENT_URL'] = path_info

        return self.app(environ, start_response)


class PageCacheMiddleware(object):
    ''' A simple page cache that can store and serve pages. It uses
    Redis as storage. It caches pages that have a http status code of
    200, use the GET method. Only non-logged in users receive cached
    pages.
    Cachable pages are indicated by a environ CKAN_PAGE_CACHABLE
    variable.'''

    def __init__(self, app, config):
        self.app = app
        import redis    # only import if used
        self.redis = redis  # we need to reference this within the class
        self.redis_exception = redis.exceptions.ConnectionError
        self.redis_connection = None

    def __call__(self, environ, start_response):

        def _start_response(status, response_headers, exc_info=None):
            # This wrapper allows us to get the status and headers.
            environ['CKAN_PAGE_STATUS'] = status
            environ['CKAN_PAGE_HEADERS'] = response_headers
            return start_response(status, response_headers, exc_info)

        # Only use cache for GET requests
        # REMOTE_USER is used by some tests.
        if environ['REQUEST_METHOD'] != 'GET' or environ.get('REMOTE_USER'):
            return self.app(environ, start_response)

        # If there is a ckan cookie (or auth_tkt) we avoid the cache.
        # We want to allow other cookies like google analytics ones :(
        cookie_string = environ.get('HTTP_COOKIE')
        if cookie_string:
            for cookie in cookie_string.split(';'):
                if cookie.startswith('ckan') or cookie.startswith('auth_tkt'):
                    return self.app(environ, start_response)

        # Make our cache key
        key = 'page:%s?%s' % (environ['PATH_INFO'], environ['QUERY_STRING'])

        # Try to connect if we don't have a connection. Doing this here
        # allows the redis server to be unavailable at times.
        if self.redis_connection is None:
            try:
                self.redis_connection = self.redis.StrictRedis()
                self.redis_connection.flushdb()
            except self.redis_exception:
                # Connection may have failed at flush so clear it.
                self.redis_connection = None
                return self.app(environ, start_response)

        # If cached return cached result
        try:
            result = self.redis_connection.lrange(key, 0, 2)
        except self.redis_exception:
            # Connection failed so clear it and return the page as normal.
            self.redis_connection = None
            return self.app(environ, start_response)

        if result:
            headers = json.loads(result[1])
            # Convert headers from list to tuples.
            headers = [(str(key), str(value)) for key, value in headers]
            start_response(str(result[0]), headers)
            # Returning a huge string slows down the server. Therefore we
            # cut it up into more usable chunks.
            page = result[2]
            out = []
            total = len(page)
            position = 0
            size = 4096
            while position < total:
                out.append(page[position:position + size])
                position += size
            return out

        # Generate the response from our application.
        page = self.app(environ, _start_response)

        # Only cache http status 200 pages
        if not environ['CKAN_PAGE_STATUS'].startswith('200'):
            return page

        cachable = False
        if environ.get('CKAN_PAGE_CACHABLE'):
            cachable = True

        # Cache things if cachable.
        if cachable:
            # Make sure we consume any file handles etc.
            page_string = ''.join(list(page))
            # Use a pipe to add page in a transaction.
            pipe = self.redis_connection.pipeline()
            pipe.rpush(key, environ['CKAN_PAGE_STATUS'])
            pipe.rpush(key, json.dumps(environ['CKAN_PAGE_HEADERS']))
            pipe.rpush(key, page_string)
            pipe.execute()
        return page


class TrackingMiddleware(object):

    def __init__(self, app, config):
        self.app = app
        self.engine = sa.create_engine(config.get('sqlalchemy.url'))

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        method = environ.get('REQUEST_METHOD')
        if path == '/_tracking' and method == 'POST':
            # do the tracking
            # get the post data
            payload = environ['wsgi.input'].read()
            parts = payload.split('&')
            data = {}
            for part in parts:
                k, v = part.split('=')
                data[k] = urllib2.unquote(v).decode("utf8")
            start_response('200 OK', [('Content-Type', 'text/html')])
            # we want a unique anonomized key for each user so that we do
            # not count multiple clicks from the same user.
            key = ''.join([
                environ['HTTP_USER_AGENT'],
                environ['REMOTE_ADDR'],
                environ.get('HTTP_ACCEPT_LANGUAGE', ''),
                environ.get('HTTP_ACCEPT_ENCODING', ''),
            ])
            key = hashlib.md5(key).hexdigest()
            # store key/data here
            sql = '''INSERT INTO tracking_raw
                     (user_key, url, tracking_type)
                     VALUES (%s, %s, %s)'''
            self.engine.execute(sql, key, data.get('url'), data.get('type'))
            return []
        return self.app(environ, start_response)


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
