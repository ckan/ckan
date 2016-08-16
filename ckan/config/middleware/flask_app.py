# encoding: utf-8

import os
import importlib
import inspect

from flask import Flask, Blueprint
from flask.ctx import _AppCtxGlobals

from werkzeug.exceptions import HTTPException

from ckan.common import config, g
import ckan.lib.app_globals as app_globals

import logging
log = logging.getLogger(__name__)


def make_flask_stack(conf, **app_conf):
    """ This has to pass the flask app through all the same middleware that
    Pylons used """

    app = flask_app = CKANFlask(__name__)
    app.app_ctx_globals_class = CKAN_AppCtxGlobals

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

    # Add a reference to the actual Flask app so it's easier to access
    app._wsgi_app = flask_app

    return app


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
            return (False, self.app_name)


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
