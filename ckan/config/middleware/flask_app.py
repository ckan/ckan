# encoding: utf-8

import os
import sys
import re
import time
import inspect
import itertools
import pkgutil

from flask import Blueprint, send_from_directory
from flask.ctx import _AppCtxGlobals
from flask.sessions import SessionInterface
from flask_multistatic import MultiStaticFlask

import six
from werkzeug.exceptions import default_exceptions, HTTPException
from werkzeug.routing import Rule

from flask_babel import Babel

from beaker.middleware import SessionMiddleware
from ckan.common import asbool
from fanstatic import Fanstatic
from repoze.who.config import WhoConfig
from repoze.who.middleware import PluggableAuthenticationMiddleware

import ckan.model as model
from ckan.lib import base
from ckan.lib import helpers
from ckan.lib import jinja_extensions
from ckan.lib import uploader
from ckan.lib import i18n
from ckan.common import config, g, request, ungettext
from ckan.config.middleware.common_middleware import (TrackingMiddleware,
                                                      HostHeaderMiddleware,
                                                      RootPathMiddleware)
import ckan.lib.app_globals as app_globals
import ckan.lib.plugins as lib_plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.webassets_tools import get_webassets_path

from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IBlueprint, IMiddleware, ITranslation
from ckan.views import (identify_user,
                        set_cors_headers_for_response,
                        check_session_cookie,
                        set_controller_and_action,
                        set_cache_control_headers_for_response,
                        handle_i18n,
                        set_ckan_current_url,
                        )

import logging
from logging.handlers import SMTPHandler
log = logging.getLogger(__name__)


class I18nMiddleware(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):

        handle_i18n(environ)
        return self.app(environ, start_response)


class CKANBabel(Babel):
    def __init__(self, *pargs, **kwargs):
        super(CKANBabel, self).__init__(*pargs, **kwargs)
        self._i18n_path_idx = 0

    @property
    def domain(self):
        default = super(CKANBabel, self).domain
        multiple = self.app.config.get('BABEL_MULTIPLE_DOMAINS')
        if not multiple:
            return default
        domains = multiple.split(';')
        try:
            return domains[self._i18n_path_idx]
        except IndexError:
            return default

    @property
    def translation_directories(self):
        self._i18n_path_idx = 0
        for path in super(CKANBabel, self).translation_directories:
            yield path
            self._i18n_path_idx += 1


class BeakerSessionInterface(SessionInterface):
    def open_session(self, app, request):
        if 'beaker.session' in request.environ:
            return request.environ['beaker.session']

    def save_session(self, app, session, response):
        session.save()

    def is_null_session(self, obj):

        is_null = super(BeakerSessionInterface, self).is_null_session(obj)

        if not is_null:
            # Beaker always adds these keys on each request, so if these are
            # the only keys present we assume it's an empty session

            is_null = (
                sorted(obj.keys()) in [
                    # Beaker 0.11 (py3)
                    [u"_accessed_time", u"_creation_time", u"_domain",
                        u"_path"],
                    # Beaker 0.10 (py2)
                    [u"_accessed_time", u"_creation_time"]
                ]
            )

        return is_null


def make_flask_stack(conf):
    """ This has to pass the flask app through all the same middleware that
    Pylons used """

    root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    debug = asbool(conf.get('debug', conf.get('DEBUG', False)))
    testing = asbool(conf.get('testing', conf.get('TESTING', False)))
    app = flask_app = CKANFlask(__name__, static_url_path='')

    # Register storage for accessing group images, site logo, etc.
    storage_folder = []
    storage = uploader.get_storage_path()
    if storage:
        storage_folder = [os.path.join(storage, 'storage')]

    # Static files folders (core and extensions)
    public_folder = config.get(u'ckan.base_public_folder')
    app.static_folder = config.get(
        'extra_public_paths', ''
    ).split(',') + [os.path.join(root, public_folder)] + storage_folder

    app.jinja_options = jinja_extensions.get_jinja_env_options()
    app.jinja_env.policies['ext.i18n.trimmed'] = True

    app.debug = debug
    app.testing = testing
    app.template_folder = os.path.join(root, 'templates')
    app.app_ctx_globals_class = CKAN_AppCtxGlobals
    app.url_rule_class = CKAN_Rule

    # Update Flask config with the CKAN values. We use the common config
    # object as values might have been modified on `load_environment`
    if config:
        app.config.update(config)
    else:
        app.config.update(conf)

    # Do all the Flask-specific stuff before adding other middlewares

    # Secret key needed for flask-debug-toolbar and sessions
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = config.get('beaker.session.secret')
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError(u'You must provide a value for the secret key'
                           ' with the SECRET_KEY config option')

    root_path = config.get('ckan.root_path', None)
    if debug:
        from flask_debugtoolbar import DebugToolbarExtension
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        debug_ext = DebugToolbarExtension()

        # register path that includes `ckan.site_root` before
        # initializing debug app. In such a way, our route receives
        # higher precedence.

        # TODO: After removal of Pylons code, switch to
        # `APPLICATION_ROOT` config value for flask application. Right
        # now it's a bad option because we are handling both pylons
        # and flask urls inside helpers and splitting this logic will
        # bring us tons of headache.
        if root_path:
            app.add_url_rule(
                root_path.replace('{{LANG}}', '').rstrip('/') +
                '/_debug_toolbar/static/<path:filename>',
                '_debug_toolbar.static', debug_ext.send_static_file
            )
        debug_ext.init_app(app)

        from werkzeug.debug import DebuggedApplication
        app.wsgi_app = DebuggedApplication(app.wsgi_app, True)

    namespace = 'beaker.session.'
    session_opts = {k.replace('beaker.', ''): v
                    for k, v in six.iteritems(config)
                    if k.startswith(namespace)}
    if (not session_opts.get('session.data_dir') and
            session_opts.get('session.type', 'file') == 'file'):
        cache_dir = conf.get('cache_dir') or conf.get('cache.dir')
        session_opts['session.data_dir'] = '{data_dir}/sessions'.format(
            data_dir=cache_dir)

    app.wsgi_app = RootPathMiddleware(app.wsgi_app, session_opts)
    app.wsgi_app = SessionMiddleware(app.wsgi_app, session_opts)
    app.session_interface = BeakerSessionInterface()

    # Add Jinja2 extensions and filters
    app.jinja_env.filters['empty_and_escape'] = \
        jinja_extensions.empty_and_escape

    # Common handlers for all requests
    app.before_request(ckan_before_request)
    app.after_request(ckan_after_request)

    # Template context processors
    app.context_processor(helper_functions)
    app.context_processor(c_object)
    app.context_processor(request_object)

    @app.context_processor
    def ungettext_alias():
        u'''
        Provide `ungettext` as an alias of `ngettext` for backwards
        compatibility
        '''
        return dict(ungettext=ungettext)

    # Babel
    _ckan_i18n_dir = i18n.get_ckan_i18n_dir()

    pairs = [
        (_ckan_i18n_dir, u'ckan')
    ] + [
        (p.i18n_directory(), p.i18n_domain())
        for p in reversed(list(PluginImplementations(ITranslation)))
    ]

    i18n_dirs, i18n_domains = zip(*pairs)

    app.config[u'BABEL_TRANSLATION_DIRECTORIES'] = ';'.join(i18n_dirs)
    app.config[u'BABEL_DOMAIN'] = 'ckan'
    app.config[u'BABEL_MULTIPLE_DOMAINS'] = ';'.join(i18n_domains)
    app.config[u'BABEL_DEFAULT_TIMEZONE'] = str(helpers.get_display_timezone())

    babel = CKANBabel(app)

    babel.localeselector(get_locale)

    # WebAssets
    _setup_webassets(app)

    # Auto-register all blueprints defined in the `views` folder
    _register_core_blueprints(app)
    _register_error_handler(app)

    # Set up each IBlueprint extension as a Flask Blueprint
    for plugin in PluginImplementations(IBlueprint):
        if hasattr(plugin, 'get_blueprint'):
            plugin_blueprints = plugin.get_blueprint()
            if not isinstance(plugin_blueprints, list):
                plugin_blueprints = [plugin_blueprints]
            for blueprint in plugin_blueprints:
                app.register_extension_blueprint(blueprint)

    lib_plugins.register_package_blueprints(app)
    lib_plugins.register_group_blueprints(app)

    # Set flask routes in named_routes
    # TODO: refactor whatever helper is using this to not do it
    if 'routes.named_routes' not in config:
        config['routes.named_routes'] = {}
    for rule in app.url_map.iter_rules():
        if '.' not in rule.endpoint:
            continue
        controller, action = rule.endpoint.split('.')
        needed = list(rule.arguments - set(rule.defaults or {}))
        route = {
            rule.endpoint: {
                'action': action,
                'controller': controller,
                'highlight_actions': action,
                'needed': needed
            }
        }
        config['routes.named_routes'].update(route)

    # Start other middleware
    for plugin in PluginImplementations(IMiddleware):
        app = plugin.make_middleware(app, config)

    # Fanstatic
    fanstatic_enable_rollup = asbool(
        conf.get('fanstatic_enable_rollup', False))
    if debug:
        fanstatic_config = {
            'versioning': True,
            'recompute_hashes': True,
            'minified': False,
            'bottom': True,
            'bundle': False,
            'rollup': fanstatic_enable_rollup,
        }
    else:
        fanstatic_config = {
            'versioning': True,
            'recompute_hashes': False,
            'minified': True,
            'bottom': True,
            'bundle': True,
            'rollup': fanstatic_enable_rollup,
        }

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

    # Initialize repoze.who
    who_parser = WhoConfig(conf['here'])
    who_parser.parse(open(conf['who.config_file']))

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

    # Update the main CKAN config object with the Flask specific keys
    # that were set here or autogenerated
    flask_config_keys = set(flask_app.config.keys()) - set(config.keys())
    for key in flask_config_keys:
        config[key] = flask_app.config[key]

    # Prevent the host from request to be added to the new header location.
    app = HostHeaderMiddleware(app)
    if six.PY3:
        app = I18nMiddleware(app)

        if asbool(config.get('ckan.tracking_enabled', 'false')):
            app = TrackingMiddleware(app, config)

    # Add a reference to the actual Flask app so it's easier to access
    app._wsgi_app = flask_app

    return app


def get_locale():
    u'''
    Return the value of the `CKAN_LANG` key of the WSGI environ,
    set by the I18nMiddleware based on the URL.
    If no value is defined, it defaults to `ckan.locale_default` or `en`.
    '''
    return request.environ.get(
        u'CKAN_LANG',
        config.get(u'ckan.locale_default', u'en'))


def ckan_before_request():
    u'''
    Common handler executed before all Flask requests

    If a response is returned by any of the functions called (
    currently ``identify_user()` only) any further processing of the
    request will be stopped and that response will be returned.

    '''
    response = None

    g.__timer = time.time()

    # Update app_globals
    app_globals.app_globals._check_uptodate()

    # Identify the user from the repoze cookie or the API header
    # Sets g.user and g.userobj
    response = identify_user()

    # Provide g.controller and g.action for backward compatibility
    # with extensions
    set_controller_and_action()

    set_ckan_current_url(request.environ)

    return response


def ckan_after_request(response):
    u'''Common handler executed after all Flask requests'''

    # Dispose of the SQLALchemy session
    model.Session.remove()

    # Check session cookie
    response = check_session_cookie(response)

    # Set CORS headers if necessary
    response = set_cors_headers_for_response(response)

    # Set Cache Control headers
    response = set_cache_control_headers_for_response(response)

    r_time = time.time() - g.__timer
    url = request.environ['PATH_INFO']
    status_code = response.status_code

    log.info(' %s %s render time %.3f seconds' % (status_code, url, r_time))

    return response


def helper_functions():
    u'''Make helper functions (`h`) available to Flask templates'''
    if not helpers.helper_functions:
        helpers.load_plugin_helpers()
    return dict(h=helpers.helper_functions)


def c_object():
    u'''
    Expose `c` as an alias of `g` in templates for backwards compatibility
    '''
    return dict(c=g)


def request_object():
    u"""Use CKANRequest object implicitly in templates"""
    return dict(request=request)


class CKAN_Rule(Rule):

    u'''Custom Flask url_rule_class.

    We use it to be able to flag routes defined in extensions as such
    '''

    def __init__(self, *args, **kwargs):
        self.ckan_core = True
        super(CKAN_Rule, self).__init__(*args, **kwargs)


class CKAN_AppCtxGlobals(_AppCtxGlobals):

    '''Custom Flask AppCtxGlobal class (flask.g).'''

    def __getattr__(self, name):
        '''
        If flask.g doesn't have attribute `name`, fall back to CKAN's
        app_globals object.
        If the key is also not found in there, an AttributeError will be raised
        '''
        return getattr(app_globals.app_globals, name)


class CKANFlask(MultiStaticFlask):

    '''Extend the Flask class with a special method called on incoming
     requests by AskAppDispatcherMiddleware.
    '''

    app_name = 'flask_app'

    def can_handle_request(self, environ):
        '''
        Decides whether it can handle a request with the Flask app by
        matching the request environ against the route mapper

        Returns (True, 'flask_app', origin) if this is the case.

        `origin` can be either 'core' or 'extension' depending on where
        the route was defined.
        '''
        urls = self.url_map.bind_to_environ(environ)

        try:
            rule, args = urls.match(return_rule=True)
            origin = 'core'
            if hasattr(rule, 'ckan_core') and not rule.ckan_core:
                origin = 'extension'
            log.debug('Flask route match, endpoint: {0}, args: {1}, '
                      'origin: {2}'.format(rule.endpoint, args, origin))

            # Disable built-in flask's ability to prepend site root to
            # generated url, as we are going to use locale and existing
            # logic is not flexible enough for this purpose
            environ['SCRIPT_NAME'] = ''

            return (True, self.app_name, origin)
        except HTTPException:
            return (False, self.app_name)

    def register_extension_blueprint(self, blueprint, **kwargs):
        '''
        This method should be used to register blueprints that come from
        extensions, so there's an opportunity to add extension-specific
        options.

        Sets the rule property `ckan_core` to False, to indicate that the rule
        applies to an extension route.
        '''
        self.register_blueprint(blueprint, **kwargs)

        # Get the new blueprint rules
        bp_rules = itertools.chain.from_iterable(
            v for k, v in six.iteritems(self.url_map._rules_by_endpoint)
            if k.startswith(u'{0}.'.format(blueprint.name))
        )

        # This compare key will ensure the rule will be near the top.
        top_compare_key = False, -100, [(-2, 0)]
        for r in bp_rules:
            r.ckan_core = False
            r.match_compare_key = lambda: top_compare_key


def _register_core_blueprints(app):
    u'''Register all blueprints defined in the `views` folder
    '''
    def is_blueprint(mm):
        return isinstance(mm, Blueprint) and getattr(mm, 'auto_register', True)

    path = os.path.join(os.path.dirname(__file__), '..', '..', 'views')

    for loader, name, _ in pkgutil.iter_modules([path], 'ckan.views.'):
        module = loader.find_module(name).load_module(name)
        for blueprint in inspect.getmembers(module, is_blueprint):
            app.register_blueprint(blueprint[1])
            log.debug(u'Registered core blueprint: {0!r}'.format(blueprint[0]))


def _register_error_handler(app):
    u'''Register error handler'''

    def error_handler(e):
        debug = asbool(config.get('debug', config.get('DEBUG', False)))
        if isinstance(e, HTTPException):
            log.debug(e, exc_info=sys.exc_info) if debug else log.info(e)
            extra_vars = {
                u'code': e.code,
                u'content': e.description,
                u'name': e.name
            }

            return base.render(
                u'error_document_template.html', extra_vars), e.code
        log.error(e, exc_info=sys.exc_info)
        extra_vars = {u'code': [500], u'content': u'Internal server error'}
        return base.render(u'error_document_template.html', extra_vars), 500

    for code in default_exceptions:
        app.register_error_handler(code, error_handler)
    if not app.debug and not app.testing:
        app.register_error_handler(Exception, error_handler)
        if config.get('email_to'):
            _setup_error_mail_handler(app)


def _setup_error_mail_handler(app):

    class ContextualFilter(logging.Filter):
        def filter(self, log_record):
            log_record.url = request.path
            log_record.method = request.method
            log_record.ip = request.environ.get("REMOTE_ADDR")
            log_record.headers = request.headers
            return True

    smtp_server = config.get('smtp.server', 'localhost')
    mailhost = tuple(smtp_server.split(':')) \
        if ':' in smtp_server else smtp_server
    credentials = None
    if config.get('smtp.user'):
        credentials = (config.get('smtp.user'), config.get('smtp.password'))
    secure = () if asbool(config.get('smtp.starttls')) else None
    mail_handler = SMTPHandler(
        mailhost=mailhost,
        fromaddr=config.get('error_email_from'),
        toaddrs=[config.get('email_to')],
        subject='Application Error',
        credentials=credentials,
        secure=secure
    )

    mail_handler.setLevel(logging.ERROR)
    mail_handler.setFormatter(logging.Formatter('''
Time:               %(asctime)s
URL:                %(url)s
Method:             %(method)s
IP:                 %(ip)s
Headers:            %(headers)s

'''))

    context_provider = ContextualFilter()
    app.logger.addFilter(context_provider)
    app.logger.addHandler(mail_handler)


def _setup_webassets(app):
    app.use_x_sendfile = toolkit.asbool(
        config.get('ckan.webassets.use_x_sendfile')
    )

    webassets_folder = get_webassets_path()

    @app.route('/webassets/<path:path>', endpoint='webassets.index')
    def webassets(path):
        return send_from_directory(webassets_folder, path)
