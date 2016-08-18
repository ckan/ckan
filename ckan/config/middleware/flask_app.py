# encoding: utf-8

from flask import Flask
from werkzeug.exceptions import HTTPException

from flask_debugtoolbar import DebugToolbarExtension

from paste.deploy.converters import asbool

from ckan.common import config


import logging
log = logging.getLogger(__name__)


def make_flask_stack(conf, **app_conf):
    """ This has to pass the flask app through all the same middleware that
    Pylons used """

    debug = asbool(app_conf.get('debug', app_conf.get('DEBUG', False)))

    app = flask_app = CKANFlask(__name__)
    app.debug = debug

    # Update Flask config with the CKAN values. We use the common config
    # object as values might have been modified on `load_environment`
    if config:
        app.config.update(config)
    else:
        app.config.update(conf)
        app.config.update(app_conf)

    # Do all the Flask-specific stuff before adding other middlewares

    # Secret key needed for flask-debug-toolbar and sessions
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = config.get('beaker.session.secret')
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError(u'You must provide a value for the secret key'
                           ' with the SECRET_KEY config option')

    if debug:
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        DebugToolbarExtension(app)

    @app.route('/hello', methods=['GET'])
    def hello_world():
        return 'Hello World, this is served by Flask'

    @app.route('/hello', methods=['POST'])
    def hello_world_post():
        return 'Hello World, this was posted to Flask'

    # Add a reference to the actual Flask app so it's easier to access
    app._wsgi_app = flask_app

    return app


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
