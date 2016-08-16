# encoding: utf-8

import os
import importlib
import inspect
import itertools

from flask import Flask, Blueprint
from flask.ctx import _AppCtxGlobals

from werkzeug.exceptions import HTTPException
from werkzeug.routing import Rule

from ckan.common import config, g
import ckan.lib.app_globals as app_globals
from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import IBlueprint


import logging
log = logging.getLogger(__name__)


def make_flask_stack(conf, **app_conf):
    """ This has to pass the flask app through all the same middleware that
    Pylons used """

    app = flask_app = CKANFlask(__name__)
    app.app_ctx_globals_class = CKAN_AppCtxGlobals
    app.url_rule_class = CKAN_Rule

    # Update Flask config with the CKAN values. We use the common config
    # object as values might have been modified on `load_environment`
    if config:
        app.config.update(config)
    else:
        app.config.update(conf)
        app.config.update(app_conf)

    # Template context processors
    @app.context_processor
    def c_object():
        u'''
        Expose `c` as an alias of `g` in templates for backwards compatibility
        '''
        return dict(c=g)

    @app.route('/hello', methods=['GET'])
    def hello_world():
        return 'Hello World, this is served by Flask'

    @app.route('/hello', methods=['POST'])
    def hello_world_post():
        return 'Hello World, this was posted to Flask'

    # Auto-register all blueprints defined in the `views` folder
    _register_core_blueprints(app)

    # Set up each IBlueprint extension as a Flask Blueprint
    for plugin in PluginImplementations(IBlueprint):
        if hasattr(plugin, 'get_blueprint'):
            app.register_extension_blueprint(plugin.get_blueprint())

    # Add a reference to the actual Flask app so it's easier to access
    app._wsgi_app = flask_app

    return app


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


def _register_core_blueprints(app):
    u'''Register all blueprints defined in the `views` folder
    '''
    views_path = os.path.join(os.path.dirname(__file__),
                              u'..', u'..', u'views')
    module_names = [f.rstrip(u'.py')
                    for f in os.listdir(views_path)
                    if f.endswith(u'.py') and not f.startswith(u'_')]
    blueprints = []
    for name in module_names:
        module = importlib.import_module(u'ckan.views.{0}'.format(name))
        blueprints.extend([m for m in inspect.getmembers(module)
                           if isinstance(m[1], Blueprint)])
    if blueprints:
        for blueprint in blueprints:
            app.register_blueprint(blueprint[1])
            log.debug(u'Registered core blueprint: {0}'.format(blueprint[0]))
