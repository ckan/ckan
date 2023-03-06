# encoding: utf-8
from __future__ import annotations

import os
import sys
import time
import inspect
import itertools
import pkgutil
import logging

from logging.handlers import SMTPHandler
from typing import Any, Iterable, Optional, Union, cast

from flask import Blueprint, send_from_directory, current_app
from flask.ctx import _AppCtxGlobals
from flask.sessions import SessionInterface
from flask_multistatic import MultiStaticFlask

from werkzeug.exceptions import (
    default_exceptions,
    HTTPException,
    Unauthorized,
    Forbidden
)
from werkzeug.routing import Rule
from werkzeug.local import LocalProxy

from flask_babel import Babel

from beaker.middleware import SessionMiddleware
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from ckan.common import CKANConfig, asbool, session, current_user

import ckan.model as model
from ckan.lib import base
from ckan.lib import helpers as h
from ckan.lib import jinja_extensions
from ckan.lib import uploader
from ckan.lib import i18n
from ckan.common import config, g, request, ungettext
from ckan.config.middleware.common_middleware import (TrackingMiddleware,
                                                      HostHeaderMiddleware,
                                                      RootPathMiddleware)
import ckan.lib.app_globals as app_globals
import ckan.lib.plugins as lib_plugins
from ckan.lib.webassets_tools import get_webassets_path

from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IBlueprint, IMiddleware, ITranslation
from ckan.views import (identify_user,
                        set_cors_headers_for_response,
                        set_controller_and_action,
                        set_cache_control_headers_for_response,
                        handle_i18n,
                        set_ckan_current_url,
                        _get_user_for_apitoken,
                        )
from ckan.types import CKANApp, Config, Response

log = logging.getLogger(__name__)

csrf = CSRFProtect()

csrf_warn_extensions = (
        "Extensions are excluded from CSRF protection! "
        "We allow extensions to run without CSRF protection "
        "but it will be forced future releases. "
        "Read the documentation for more information on how to add "
        "CSRF protection to your extension."
    )


class I18nMiddleware(object):
    def __init__(self, app: CKANApp):
        self.app = app

    def __call__(self, environ: Any, start_response: Any):

        handle_i18n(environ)
        return self.app(environ, start_response)


class CKANBabel(Babel):
    app: CKANApp

    def __init__(self, *pargs: Any, **kwargs: Any):
        super(CKANBabel, self).__init__(*pargs, **kwargs)
        self._i18n_path_idx = 0

    @property
    def domain(self) -> str:
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
    def translation_directories(self) -> Iterable[str]:
        self._i18n_path_idx = 0
        for path in super(CKANBabel, self).translation_directories:
            yield path
            self._i18n_path_idx += 1


def _ungettext_alias():
    u'''
    Provide `ungettext` as an alias of `ngettext` for backwards
    compatibility
    '''
    return dict(ungettext=ungettext)


class BeakerSessionInterface(SessionInterface):
    def open_session(self, app: Any, request: Any):
        if 'beaker.session' in request.environ:
            return request.environ['beaker.session']

    def save_session(self, app: Any, session: Any, response: Any):
        session.save()


def make_flask_stack(conf: Union[Config, CKANConfig]) -> CKANApp:
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
        'extra_public_paths'
    ).split(',') + config.get('plugin_public_paths', []) + [
        os.path.join(root, public_folder)
    ] + storage_folder

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

    root_path = config.get('ckan.root_path')
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
                    for k, v in config.items()
                    if k.startswith(namespace)}
    if (not session_opts.get('session.data_dir') and
            session_opts.get('session.type', 'file') == 'file'):
        cache_dir = conf.get('cache_dir') or conf.get('cache.dir')
        session_opts['session.data_dir'] = '{data_dir}/sessions'.format(
            data_dir=cache_dir)

    app.wsgi_app = RootPathMiddleware(app.wsgi_app)
    app.wsgi_app = SessionMiddleware(app.wsgi_app, session_opts)
    app.session_interface = BeakerSessionInterface()

    # Add Jinja2 extensions and filters
    app.jinja_env.filters['empty_and_escape'] = \
        jinja_extensions.empty_and_escape

    # Common handlers for all requests
    #
    # flask types do not mention that it's possible to return a response from
    # the `before_request` callback
    app.before_request(ckan_before_request)
    app.after_request(ckan_after_request)

    # Template context processors
    app.context_processor(helper_functions)
    app.context_processor(c_object)

    app.context_processor(_ungettext_alias)

    # Babel
    _ckan_i18n_dir = i18n.get_ckan_i18n_dir()

    pairs = [
        cast("tuple[str, str]", (_ckan_i18n_dir, u'ckan'))
    ] + [
        (p.i18n_directory(), p.i18n_domain())
        for p in reversed(list(PluginImplementations(ITranslation)))
    ]

    i18n_dirs, i18n_domains = zip(*pairs)

    app.config[u'BABEL_TRANSLATION_DIRECTORIES'] = ';'.join(i18n_dirs)
    app.config[u'BABEL_DOMAIN'] = 'ckan'
    app.config[u'BABEL_MULTIPLE_DOMAINS'] = ';'.join(i18n_domains)
    app.config[u'BABEL_DEFAULT_TIMEZONE'] = str(h.get_display_timezone())

    babel = CKANBabel(app)

    babel.localeselector(get_locale)

    # WebAssets
    _setup_webassets(app)

    # Auto-register all blueprints defined in the `views` folder
    _register_core_blueprints(app)
    _register_error_handler(app)

    # CSRF
    wtf_key = "WTF_CSRF_SECRET_KEY"
    if not app.config.get(wtf_key):
        config[wtf_key] = app.config[wtf_key] = app.config["SECRET_KEY"]
    app.config["WTF_CSRF_FIELD_NAME"] = config.get('WTF_CSRF_FIELD_NAME')
    csrf.init_app(app)

    # Set up each IBlueprint extension as a Flask Blueprint
    _register_plugins_blueprints(app)

    if config.get("ckan.csrf_protection.ignore_extensions"):
        log.warn(csrf_warn_extensions)
        _exempt_plugins_blueprints_from_csrf(csrf)

    lib_plugins.register_package_blueprints(app)
    lib_plugins.register_group_blueprints(app)

    # Start other middleware
    for plugin in PluginImplementations(IMiddleware):
        app = plugin.make_middleware(app, config)

    for plugin in PluginImplementations(IMiddleware):
        try:
            app = plugin.make_error_log_middleware(app, config)
        except AttributeError:
            log.critical('Middleware class {0} is missing the method'
                         'make_error_log_middleware.'
                         .format(plugin.__class__.__name__))

    # Initialize flask-login
    login_manager = LoginManager()
    login_manager.init_app(flask_app)
    # make anonymous_user an instance of CKAN custom class
    login_manager.anonymous_user = model.AnonymousUser
    # The name of the view to redirect to when the user needs to log in.
    login_manager.login_view = config.get("ckan.auth.login_view")

    @login_manager.user_loader
    def load_user(user_id: str) -> Optional["model.User"]:  # type: ignore
        """
        This callback function is called whenever we need to reload from
        the database the logged in user in the session (ie the cookie).

        Site maintainers can choose to completely ignore cookie based
        authentication for API calls, but that will break existing JS widgets
        that rely on API calls so it should be used with caution.
        """
        endpoint = request.endpoint or ""
        is_api = endpoint.split(".")[0] == "api"
        if (
            not config.get("ckan.auth.enable_cookie_auth_in_api")
                and is_api):
            return

        return model.User.get(user_id)

    @login_manager.request_loader
    def load_user_from_request(request):  # type: ignore
        """
        This callback function is called whenever a user could not be
        authenticated via the session cookie, so we fall back to the API token.
        """
        g.login_via_auth_header = True

        user = _get_user_for_apitoken()

        return user

    # Update the main CKAN config object with the Flask specific keys
    # that were set here or autogenerated
    flask_config_keys = set(flask_app.config.keys()) - set(config.keys())
    for key in flask_config_keys:
        config[key] = flask_app.config[key]

    # Prevent the host from request to be added to the new header location.
    app = HostHeaderMiddleware(app)

    app = I18nMiddleware(app)

    if config.get('ckan.tracking_enabled'):
        app = TrackingMiddleware(app, config)

    # Add a reference to the actual Flask app so it's easier to access
    # type_ignore_reason: custom attribute
    app._wsgi_app = flask_app  # type: ignore

    return app


def get_locale() -> str:
    u'''
    Return the value of the `CKAN_LANG` key of the WSGI environ,
    set by the I18nMiddleware based on the URL.
    If no value is defined, it defaults to `ckan.locale_default` or `en`.
    '''
    return request.environ.get(
        u'CKAN_LANG',
        config.get(u'ckan.locale_default'))


def set_remote_user_as_current_user_for_tests():
    '''This function exists to maintain backward compatibility
    for the `TESTS` of the `CKAN` extensions

    If `REMOTE_USER` is in the request environ we will try to get
    the user_obj from the DB, if there is an user_obj, we will set the
    `session['_user_id']` with that user_obj.id

    This way, `Flask-Login` will load the user from
    `session['_user_id']` and will set the `current_user`
    proxy for us behind the scene.
    '''
    if "REMOTE_USER" in request.environ:
        username = request.environ["REMOTE_USER"]
        if isinstance(username, bytes):
            username = username.decode()

        userobj = model.User.get(username)
        if userobj:
            session["_user_id"] = userobj.id


def ckan_before_request() -> Optional[Response]:
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

    # This is needed for the TESTS of the CKAN extensions only!
    # we should remove it as soon as the maintainers of the
    # CKAN extensions change their tests according to the new changes.
    if config.get("testing"):
        set_remote_user_as_current_user_for_tests()

    # Identify the user from the flask-login cookie or the API header
    # Sets g.user and g.userobj for extensions
    response = identify_user()

    # Disable CSRF protection if user was logged in via the Authorization
    # header
    if g.get("login_via_auth_header"):
        # Get the actual view function, as it might not match the endpoint,
        # eg "organization.edit" -> "group.edit", or custom dataset types
        endpoint = request.endpoint or ""
        view = current_app.view_functions.get(endpoint)
        dest = f"{view.__module__}.{view.__name__}"     # type: ignore
        csrf.exempt(dest)

    # Set the csrf_field_name so we can use it in our templates
    g.csrf_field_name = config.get("WTF_CSRF_FIELD_NAME")

    # Provide g.controller and g.action for backward compatibility
    # with extensions
    set_controller_and_action()

    set_ckan_current_url(request.environ)

    return response


def ckan_after_request(response: Response) -> Response:
    u'''Common handler executed after all Flask requests'''

    # Dispose of the SQLALchemy session
    model.Session.remove()

    # Set CORS headers if necessary
    response = set_cors_headers_for_response(response)

    # Set Cache Control headers
    response = set_cache_control_headers_for_response(response)

    r_time = time.time() - g.__timer
    url = request.environ['PATH_INFO']
    status_code = response.status_code

    log.info(' %s %s render time %.3f seconds' % (status_code, url, r_time))

    return response


def helper_functions() -> dict[str, h.HelperAttributeDict]:
    u'''Make helper functions (`h`) available to Flask templates'''
    if not h.helper_functions:
        h.load_plugin_helpers()
    return dict(h=h.helper_functions)


def c_object() -> dict[str, LocalProxy]:
    u'''
    Expose `c` as an alias of `g` in templates for backwards compatibility
    '''
    return dict(c=g)


class CKAN_Rule(Rule):  # noqa

    u'''Custom Flask url_rule_class.

    We use it to be able to flag routes defined in extensions as such
    '''

    def __init__(self, *args: Any, **kwargs: Any):
        self.ckan_core = True
        super(CKAN_Rule, self).__init__(*args, **kwargs)


class CKAN_AppCtxGlobals(_AppCtxGlobals):  # noqa

    '''Custom Flask AppCtxGlobal class (flask.g).'''

    def __getattr__(self, name: str):
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

    app_name: str = 'flask_app'
    static_folder: list[str]
    session_interface: SessionInterface

    def can_handle_request(
            self,
            environ: Any) -> Union[tuple[bool, str], tuple[bool, str, str]]:
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
            if not getattr(rule, 'ckan_core', True):
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

    def register_extension_blueprint(self, blueprint: Blueprint,
                                     **kwargs: dict[str, Any]):
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
            v for k, v in self.url_map._rules_by_endpoint.items()
            if k.startswith(u'{0}.'.format(blueprint.name))
        )

        # This compare key will ensure the rule will be near the top.
        top_compare_key = False, -100, [(-2, 0)]
        for r in bp_rules:
            setattr(r, "ckan_core", False)
            setattr(r, "match_compare_key", lambda: top_compare_key)


def _register_plugins_blueprints(app: CKANApp):
    """ Resgister all blueprints defined in plugins by IBlueprint
    """
    for plugin in PluginImplementations(IBlueprint):
        plugin_blueprints = plugin.get_blueprint()
        if isinstance(plugin_blueprints, list):
            for blueprint in plugin_blueprints:
                app.register_extension_blueprint(blueprint)
        else:
            app.register_extension_blueprint(plugin_blueprints)


def _exempt_plugins_blueprints_from_csrf(csrf: CSRFProtect):
    """Exempt plugins blueprints from CSRF protection.

    This feature will be deprecated in future versions.
    """
    for plugin in PluginImplementations(IBlueprint):
        plugin_blueprints = plugin.get_blueprint()
        if isinstance(plugin_blueprints, list):
            for blueprint in plugin_blueprints:
                csrf.exempt(blueprint)
        else:
            csrf.exempt(plugin_blueprints)


def _register_core_blueprints(app: CKANApp):
    u'''Register all blueprints defined in the `views` folder
    '''
    def is_blueprint(mm: Any):
        return isinstance(mm, Blueprint) and getattr(mm, 'auto_register', True)

    path = os.path.join(os.path.dirname(__file__), '..', '..', 'views')

    for loader, name, __ in pkgutil.iter_modules([path], 'ckan.views.'):
        # type_ignore_reason: incorrect external type declarations
        module = loader.find_module(name).load_module(name)  # type: ignore
        for blueprint in inspect.getmembers(module, is_blueprint):
            app.register_blueprint(blueprint[1])
            log.debug(u'Registered core blueprint: {0!r}'.format(blueprint[0]))


def _register_error_handler(app: CKANApp):
    u'''Register error handler'''

    def error_handler(e: Exception) -> Union[
        tuple[str, Optional[int]], Optional[Response]
    ]:
        debug = config.get('debug')
        if isinstance(e, HTTPException):
            if debug:
                log.debug(e, exc_info=sys.exc_info)  # type: ignore
            else:
                log.info(e)

            show_login_redirect_link = current_user.is_anonymous and type(
                e
            ) in (Unauthorized, Forbidden)
            extra_vars = {
                u'code': e.code,
                u'content': e.description,
                u'name': e.name,
                u'show_login_redirect_link': show_login_redirect_link
            }
            return base.render(
                u'error_document_template.html', extra_vars), e.code

        log.error(e, exc_info=sys.exc_info)  # type: ignore
        extra_vars = {u'code': [500], u'content': u'Internal server error'}
        return base.render(u'error_document_template.html', extra_vars), 500

    for code in default_exceptions:
        app.register_error_handler(code, error_handler)
    if not app.debug and not app.testing:
        app.register_error_handler(Exception, error_handler)
        if config.get('email_to'):
            _setup_error_mail_handler(app)


def _setup_error_mail_handler(app: CKANApp):

    class ContextualFilter(logging.Filter):
        def filter(self, log_record: Any) -> bool:
            log_record.url = request.path
            log_record.method = request.method
            log_record.ip = request.environ.get("REMOTE_ADDR")
            log_record.headers = request.headers
            return True

    smtp_server = config.get('smtp.server')
    mailhost = cast("tuple[str, int]", tuple(smtp_server.split(':'))) \
        if ':' in smtp_server else smtp_server
    credentials = None
    if config.get('smtp.user'):
        credentials = (
            config.get('smtp.user'),
            config.get('smtp.password')
        )
    secure = () if config.get('smtp.starttls') else None
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


def _setup_webassets(app: CKANApp):
    app.use_x_sendfile = config.get('ckan.webassets.use_x_sendfile')

    webassets_folder = get_webassets_path()

    def webassets(path: str):
        return send_from_directory(webassets_folder, path)

    app.add_url_rule('/webassets/<path:path>', 'webassets.index', webassets)
