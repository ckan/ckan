# encoding: utf-8

import os
import time
import itertools
import urlparse

from flask import Flask
from flask import request
from flask.ctx import _AppCtxGlobals
from flask.sessions import SessionInterface
from werkzeug.exceptions import HTTPException
from werkzeug.routing import Rule

from flask_babel import Babel
from flask_debugtoolbar import DebugToolbarExtension

from beaker.middleware import SessionMiddleware
from repoze.who.config import WhoConfig
from repoze.who.middleware import PluggableAuthenticationMiddleware
from fanstatic import Fanstatic

import ckan.lib.app_globals as app_globals
from ckan.lib import jinja_extensions
from ckan.lib import helpers
from ckan.common import c, config
from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IBlueprint
from ckan.views import (identify_user,
                        set_cors_headers_for_response,
                        check_session_cookie)


import logging
log = logging.getLogger(__name__)


def make_flask_stack(conf, **app_conf):
    """
    This passes the flask app through most of the same middleware that Pylons
    uses.
    """

    debug = app_conf.get('debug', True)

    root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    app = flask_app = CKANFlask(__name__)
    app.debug = debug
    app.template_folder = os.path.join(root, 'templates')
    app.app_ctx_globals_class = CKAN_AppCtxGlobals
    app.url_rule_class = CKAN_Rule

    # Update Flask config with the CKAN values. We use the common config
    # object as values might have been modified on `load_environment`
    if config:
        app.config.update(config)
    else:
        app.config.update(conf)
        app.config.update(app_conf)

    # Do all the Flask-specific stuff before adding other middlewares

    # Automatically set SERVER_NAME from the value of ckan.site_url. This is
    # needed so Flask is able to generate fully qualified URLs with
    # _external=True. One major thing to note is that when SERVER_NAME is set
    # up the incoming request `Host` header (`HTTP_HOST` in the WSGI environ)
    # must match its value, otherwise the Flask router will return a 404 even
    # if the route has been defined.
    if not app.config.get('SERVER_NAME'):
        site_url = (os.environ.get('CKAN_SITE_URL') or
                    os.environ.get('CKAN__SITE_URL') or
                    app_conf.get('ckan.site_url'))
        if not site_url:
            raise RuntimeError(
                'ckan.site_url is not configured and it must have a value.'
                ' Please amend your .ini file.')
        parts = urlparse.urlparse(site_url)

        app.config['SERVER_NAME'] = parts.netloc

    # secret key needed for flask-debug-toolbar
    app.config['SECRET_KEY'] = '<replace with a secret key>'
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    DebugToolbarExtension(app)

    # Use Beaker as the Flask session interface
    class BeakerSessionInterface(SessionInterface):
        def open_session(self, app, request):
            if 'beaker.session' in request.environ:
                return request.environ['beaker.session']

        def save_session(self, app, session, response):
            session.save()

    cache_dir = app_conf.get('cache_dir') or app_conf.get('cache.dir')
    session_opts = {
        'session.data_dir': '{data_dir}/sessions'.format(
            data_dir=cache_dir),
        'session.key': app_conf.get('beaker.session.key'),
        'session.cookie_expires':
        app_conf.get('beaker.session.cookie_expires'),
        'session.secret': app_conf.get('beaker.session.secret')
    }
    app.wsgi_app = SessionMiddleware(app.wsgi_app, session_opts)
    app.session_interface = BeakerSessionInterface()

    # Add jinja2 extensions and filters
    extensions = [
        'jinja2.ext.do', 'jinja2.ext.with_',
        jinja_extensions.SnippetExtension,
        jinja_extensions.CkanExtend,
        jinja_extensions.CkanInternationalizationExtension,
        jinja_extensions.LinkForExtension,
        jinja_extensions.ResourceExtension,
        jinja_extensions.UrlForStaticExtension,
        jinja_extensions.UrlForExtension
    ]
    for extension in extensions:
        app.jinja_env.add_extension(extension)
    app.jinja_env.filters['empty_and_escape'] = \
        jinja_extensions.empty_and_escape
    app.jinja_env.filters['truncate'] = jinja_extensions.truncate

    @app.before_request
    def ckan_before_request():
        c._request_timer = time.time()
        app_globals.app_globals._check_uptodate()
        identify_user()

    @app.after_request
    def ckan_after_request(response):
        response = check_session_cookie(response)
        response = set_cors_headers_for_response(response)

        # log time between before and after view
        if request.environ.get('CKAN_CURRENT_URL'):
            r_time = time.time() - c._request_timer
            url = request.environ['CKAN_CURRENT_URL'].split('?')[0]
            log.info('{url} render time {r_time:.3f} seconds'.format(
                url=url, r_time=r_time))
        return response

    # Template context processors
    @app.context_processor
    def helper_functions():
        helpers.load_plugin_helpers()
        return dict(h=helpers.helper_functions)

    @app.context_processor
    def c_object():
        return dict(c=c)

    # Babel
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(root, 'i18n')
    app.config['BABEL_DOMAIN'] = 'ckan'

    babel = Babel(app)

    @babel.localeselector
    def get_locale():
        '''
        Return the value of the `CKAN_LANG` key of the WSGI environ,
        set by the I18nMiddleware based on the URL.
        If no value is defined, it defaults to `ckan.locale_default` or `en`.
        '''
        from flask import request
        return request.environ.get(
            'CKAN_LANG',
            config.get('ckan.locale_default', 'en'))

    # A couple of test routes while we migrate to Flask
    @app.route('/hello', methods=['GET'])
    def hello_world():
        return 'Hello World, this is served by Flask'

    @app.route('/hello', methods=['POST'])
    def hello_world_post():
        return 'Hello World, this was posted to Flask'

    # TODO: maybe we can automate this?
    from ckan.views.api import api
    app.register_blueprint(api)

    # Set up each iRoute extension as a Flask Blueprint
    for plugin in PluginImplementations(IBlueprint):
        if hasattr(plugin, 'get_blueprint'):
            app.register_extension_blueprint(plugin.get_blueprint())

    # Update the main CKAN config object with the Flask specific keys
    # that were set here or autogenerated
    flask_config_keys = set(app.config.keys()) - set(config.keys())
    for key in flask_config_keys:
        config[key] = app.config[key]

    # Start other middleware

    # Fanstatic
    if debug:
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

    # Add a reference to the actual Flask app so it's easier to access
    app._wsgi_app = flask_app

    return app


class CKAN_Rule(Rule):

    '''Custom Flask url_rule_class.'''

    def __init__(self, *args, **kwargs):
        self.ckan_core = True
        super(CKAN_Rule, self).__init__(*args, **kwargs)


class CKAN_AppCtxGlobals(_AppCtxGlobals):

    '''Custom Flask AppCtxGlobal class (flask.g).'''

    def __getattr__(self, name):
        '''
        If flask.g doesn't have attribute `name`, try the app_globals object.
        '''
        return getattr(app_globals.app_globals, name)


class CKANFlask(Flask):

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
            return (True, self.app_name, origin)
        except HTTPException:
            return (False, self.app_name)

    def register_extension_blueprint(self, blueprint, **kwargs):
        '''
        This method should be used to register blueprints that come from
        extensions, so there's an opportunity to add extension-specific
        options.

        If prioritise_rules is True, add complexity to each url rule in the
        blueprint, to ensure they will override similar existing rules.

        Sets the rule property `ckan_core` to False, to indicate that the rule
        applies to an extension route.
        '''
        self.register_blueprint(blueprint, **kwargs)

        # Get the new blueprint rules
        bp_rules = [v for k, v in self.url_map._rules_by_endpoint.items()
                    if k.startswith(blueprint.name)]
        bp_rules = list(itertools.chain.from_iterable(bp_rules))

        # This compare key will ensure the rule will be near the top.
        top_compare_key = False, -100, [(-2, 0)]
        for r in bp_rules:
            r.ckan_core = False
            r.match_compare_key = lambda: top_compare_key
