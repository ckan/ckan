# encoding: utf-8

"""WSGI app initialization"""

import webob

from werkzeug.test import create_environ, run_wsgi_app

from ckan.config.environment import load_environment
from ckan.config.middleware.flask_app import make_flask_stack
from ckan.config.middleware.pylons_app import make_pylons_stack

import logging
log = logging.getLogger(__name__)

# This monkey-patches the webob request object because of the way it messes
# with the WSGI environ.

# Start of webob.requests.BaseRequest monkey patch
original_charset__set = webob.request.BaseRequest._charset__set


def custom_charset__set(self, charset):
    original_charset__set(self, charset)
    if self.environ.get('CONTENT_TYPE', '').startswith(';'):
        self.environ['CONTENT_TYPE'] = ''


webob.request.BaseRequest._charset__set = custom_charset__set

webob.request.BaseRequest.charset = property(
    webob.request.BaseRequest._charset__get,
    custom_charset__set,
    webob.request.BaseRequest._charset__del,
    webob.request.BaseRequest._charset__get.__doc__)

# End of webob.requests.BaseRequest monkey patch


def make_app(conf, full_stack=True, static_files=True, **app_conf):
    '''
    Initialise both the pylons and flask apps, and wrap them in dispatcher
    middleware.
    '''

    load_environment(conf, app_conf)

    pylons_app = make_pylons_stack(conf, full_stack, static_files,
                                   **app_conf)
    flask_app = make_flask_stack(conf, **app_conf)

    app = AskAppDispatcherMiddleware({'pylons_app': pylons_app,
                                      'flask_app': flask_app})

    return app


class AskAppDispatcherMiddleware(object):

    '''
    Dispatches incoming requests to either the Flask or Pylons apps depending
    on the WSGI environ.

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

    def __init__(self, apps=None):
        # Dict of apps managed by this middleware {<app_name>: <app_obj>, ...}
        self.apps = apps or {}

    def ask_around(self, environ):
        '''Checks with all apps whether they can handle the incoming request
        '''
        answers = [
            app._wsgi_app.can_handle_request(environ)
            for name, app in self.apps.iteritems()
        ]
        # Sort answers by app name
        answers = sorted(answers, key=lambda x: x[1])
        log.debug('Route support answers for {0} {1}: {2}'.format(
            environ.get('REQUEST_METHOD'), environ.get('PATH_INFO'),
            answers))

        return answers

    def __call__(self, environ, start_response):
        '''Determine which app to call by asking each app if it can handle the
        url and method defined on the eviron'''

        app_name = 'pylons_app'  # currently defaulting to pylons app
        answers = self.ask_around(environ)
        available_handlers = []
        for answer in answers:
            if len(answer) == 2:
                can_handle, asked_app = answer
                origin = 'core'
            else:
                can_handle, asked_app, origin = answer
            if can_handle:
                available_handlers.append('{0}_{1}'.format(asked_app, origin))

        # Enforce order of precedence:
        # Flask Extension > Pylons Extension > Flask Core > Pylons Core
        if available_handlers:
            if 'flask_app_extension' in available_handlers:
                app_name = 'flask_app'
            elif 'pylons_app_extension' in available_handlers:
                app_name = 'pylons_app'
            elif 'flask_app_core' in available_handlers:
                app_name = 'flask_app'

        log.debug('Serving request via {0} app'.format(app_name))
        environ['ckan.app'] = app_name
        if app_name == 'flask_app':
            return self.apps[app_name](environ, start_response)
        else:
            # Although this request will be served by Pylons we still
            # need an application context in order for the Flask URL
            # builder to work and to be able to access the Flask config
            flask_app = self.apps['flask_app']._wsgi_app

            with flask_app.app_context():
                return self.apps[app_name](environ, start_response)
