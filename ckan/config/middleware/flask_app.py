# encoding: utf-8

import os
import time
import itertools

from flask import Flask
from flask import abort
from flask import request
from flask import _request_ctx_stack
from flask.ctx import _AppCtxGlobals
from flask.sessions import SessionInterface
from werkzeug.exceptions import HTTPException

from wsgi_party import WSGIParty, HighAndDry
from flask.ext.babel import Babel
from flask_debugtoolbar import DebugToolbarExtension
from pylons import config

from beaker.middleware import SessionMiddleware
from repoze.who.config import WhoConfig
from repoze.who.middleware import PluggableAuthenticationMiddleware

import ckan.lib.app_globals as app_globals
from ckan.lib import jinja_extensions
from ckan.lib import helpers
from ckan.common import c
from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IBlueprint
from ckan.views import (identify_user,
                        set_cors_headers_for_response,
                        check_session_cookie)

from ckan.config.middleware import common_middleware

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
    app = CKANFlask(__name__)
    app.debug = debug
    app.template_folder = os.path.join(root, 'templates')
    app.app_ctx_globals_class = CKAN_AppCtxGlobals

    # Do all the Flask-specific stuff before adding other middlewares

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
        'session.cookie_expires': app_conf.get(
            'beaker.session.cookie_expires'),
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
        identify_user()

    @app.after_request
    def ckan_after_request(response):
        response = check_session_cookie(response)
        response = set_cors_headers_for_response(response)

        # log time between before and after view
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
            app.register_blueprint(plugin.get_blueprint(),
                                   prioritise_rules=True)

    # Start other middleware

    app = common_middleware.I18nMiddleware(app, config)

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

    return app


class CKAN_AppCtxGlobals(_AppCtxGlobals):

    '''Custom Flask AppCtxGlobal class (flask.g).'''

    def __getattr__(self, name):
        '''
        If flask.g doesn't have attribute `name`, try the app_globals object.
        '''
        return getattr(app_globals.app_globals, name)


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
        self.partyline_connected = False
        self.invitation_context = None
        # A label for the app handling this request (this app).
        self.app_name = None

    def join_party(self, request=request):
        # Bootstrap, turn the view function into a 404 after registering.
        if self.partyline_connected:
            # This route does not exist at the HTTP level.
            abort(404)
        self.invitation_context = _request_ctx_stack.top
        self.partyline = request.environ.get(WSGIParty.partyline_key)
        self.app_name = request.environ.get('partyline_handling_app')
        self.partyline.connect('can_handle_request', self.can_handle_request)
        self.partyline_connected = True
        return 'ok'

    def can_handle_request(self, environ):
        '''
        Decides whether it can handle a request with the Flask app by
        matching the request environ against the route mapper

        Returns (True, 'flask_app') if this is the case.
        '''

        # TODO: identify matching urls as core or extension. This will depend
        # on how we setup routing in Flask

        urls = self.url_map.bind_to_environ(environ)
        try:
            endpoint, args = urls.match()
            log.debug('Flask route match, endpoint: {0}, args: {1}'.format(
                endpoint, args))
            return (True, self.app_name)
        except HTTPException:
            raise HighAndDry()

    def register_blueprint(self, blueprint, prioritise_rules=False, **options):
        '''
        If prioritise_rules is True, add complexity to each url rule in the
        blueprint, to ensure they will override similar existing rules.
        '''

        # Register the blueprint with the app.
        super(CKANFlask, self).register_blueprint(blueprint, **options)
        if prioritise_rules:
            # Get the new blueprint rules
            bp_rules = [v for k, v in self.url_map._rules_by_endpoint.items()
                        if k.startswith(blueprint.name)]
            bp_rules = list(itertools.chain.from_iterable(bp_rules))

            # This compare key will ensure the rule will be near the top.
            top_compare_key = False, -100, [(-2, 0)]
            for r in bp_rules:
                r.match_compare_key = lambda: top_compare_key
