"""Utility classes for creating workable pylons controllers for unit
testing.

These classes are used solely by Pylons for unit testing controller
functionality.

"""
import gettext

import pylons
from pylons.configuration import request_defaults, response_defaults
from pylons.controllers.util import Request, Response
from pylons.util import ContextObj, PylonsContext

class ControllerWrap(object):
    def __init__(self, controller):
        self.controller = controller

    def __call__(self, environ, start_response):
        app = self.controller()
        app.start_response = None
        return app(environ, start_response)

class SetupCacheGlobal(object):
    def __init__(self, app, environ, setup_g=True, setup_cache=False,
                 setup_session=False):
        if setup_g:
            g = type('G object', (object,), {})
            g.message = 'Hello'
            g.counter = 0
            g.pylons_config = type('App conf', (object,), {})
            g.pylons_config.app_conf = dict(cache_enabled='True')
            self.g = g
        self.app = app
        self.environ = environ
        self.setup_cache = setup_cache
        self.setup_session = setup_session
        self.setup_g = setup_g

    def __call__(self, environ, start_response):
        registry = environ['paste.registry']
        py_obj = PylonsContext()
        environ_config = environ.setdefault('pylons.environ_config', {})
        if self.setup_cache:
            py_obj.cache = environ['beaker.cache']
            registry.register(pylons.cache, environ['beaker.cache'])
            environ_config['cache'] = 'beaker.cache'
        if self.setup_session:
            py_obj.session = environ['beaker.session']
            registry.register(pylons.session, environ['beaker.session'])
            environ_config['session'] = 'beaker.session'
        if self.setup_g:
            py_obj.g = self.g
            registry.register(pylons.g, self.g)
        translator = gettext.NullTranslations()
        py_obj.translator = translator
        registry.register(pylons.translator, translator)

        # Update the environ
        req = Request(environ, charset=request_defaults['charset'],
                      unicode_errors=request_defaults['errors'],
                      decode_param_names=request_defaults['decode_param_names'])        
        req.language = request_defaults['language']
        
        response = Response(
            content_type=response_defaults['content_type'],
            charset=response_defaults['charset'])
        response.headers.update(response_defaults['headers'])
        
        environ.update(self.environ)
        py_obj.config = pylons.config._current_obj()
        py_obj.request = req
        py_obj.response = response
        py_obj.c = ContextObj()
        environ['pylons.pylons'] = py_obj
        registry.register(pylons.request, req)
        registry.register(pylons.response, response)
        return self.app(environ, start_response)
