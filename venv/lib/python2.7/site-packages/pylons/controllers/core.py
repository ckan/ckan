"""The core WSGIController"""
import inspect
import logging
import types
import warnings

from paste.httpexceptions import HTTPException as LegacyHTTPException
from webob.exc import HTTPException, HTTPNotFound

import pylons
import pylons.legacy

__all__ = ['WSGIController']

log = logging.getLogger(__name__)


class WSGIController(object):
    """WSGI Controller that follows WSGI spec for calling and return
    values
    
    The Pylons WSGI Controller handles incoming web requests that are 
    dispatched from the PylonsBaseWSGIApp. These requests result in a
    new instance of the WSGIController being created, which is then
    called with the dict options from the Routes match. The standard
    WSGI response is then returned with start_response called as per
    the WSGI spec.
    
    Special WSGIController methods you may define:
    
    ``__before__``
        This method is called before your action is, and should be used
        for setting up variables/objects, restricting access to other
        actions, or other tasks which should be executed before the
        action is called.

    ``__after__``
        This method is called after the action is, unless an unexpected
        exception was raised. Subclasses of
        :class:`~webob.exc.HTTPException` (such as those raised by
        ``redirect_to`` and ``abort``) are expected; e.g. ``__after__``
        will be called on redirects.
        
    Each action to be called is inspected with :meth:`_inspect_call` so
    that it is only passed the arguments in the Routes match dict that
    it asks for. The arguments passed into the action can be customized
    by overriding the :meth:`_get_method_args` function which is
    expected to return a dict.
    
    In the event that an action is not found to handle the request, the
    Controller will raise an "Action Not Found" error if in debug mode,
    otherwise a ``404 Not Found`` error will be returned.
    
    """
    _pylons_log_debug = False

    def _perform_call(self, func, args):
        """Hide the traceback for everything above this method"""
        __traceback_hide__ = 'before_and_this'
        return func(**args)
    
    def _inspect_call(self, func):
        """Calls a function with arguments from
        :meth:`_get_method_args`
        
        Given a function, inspect_call will inspect the function args
        and call it with no further keyword args than it asked for.
        
        If the function has been decorated, it is assumed that the
        decorator preserved the function signature.
        
        """
        # Check to see if the class has a cache of argspecs yet
        try:
            cached_argspecs = self.__class__._cached_argspecs
        except AttributeError:
            self.__class__._cached_argspecs = cached_argspecs = {}
        
        try:
            argspec = cached_argspecs[func.im_func]
        except KeyError:
            argspec = cached_argspecs[func.im_func] = inspect.getargspec(func)
        kargs = self._get_method_args()
                
        log_debug = self._pylons_log_debug
        c = self._py_object.c
        args = None
        
        if argspec[2]:
            if self._py_object.config['pylons.c_attach_args']:
                for k, val in kargs.iteritems():
                    setattr(c, k, val)
            args = kargs
        else:
            args = {}
            argnames = argspec[0][isinstance(func, types.MethodType)
                                  and 1 or 0:]
            for name in argnames:
                if name in kargs:
                    if self._py_object.config['pylons.c_attach_args']:
                        setattr(c, name, kargs[name])
                    args[name] = kargs[name]
        if log_debug:
            log.debug("Calling %r method with keyword args: **%r",
                      func.__name__, args)
        try:
            result = self._perform_call(func, args)
        except HTTPException, httpe:
            if log_debug:
                log.debug("%r method raised HTTPException: %s (code: %s)",
                          func.__name__, httpe.__class__.__name__,
                          httpe.wsgi_response.code, exc_info=True)
            result = httpe
            
            # 304 Not Modified's shouldn't have a content-type set
            if result.wsgi_response.status_int == 304:
                result.wsgi_response.headers.pop('Content-Type', None)
            result._exception = True
        except LegacyHTTPException, httpe:
            if log_debug:
                log.debug("%r method raised legacy HTTPException: %s (code: "
                          "%s)", func.__name__, httpe.__class__.__name__,
                          httpe.code, exc_info=True)
            warnings.warn("Raising a paste.httpexceptions.HTTPException is "
                          "deprecated, use webob.exc.HTTPException instead",
                          DeprecationWarning, 2)
            result = httpe.response(pylons.request.environ)
            result.headers.pop('Content-Type')
            result._exception = True

        return result
    
    def _get_method_args(self):
        """Retrieve the method arguments to use with inspect call
        
        By default, this uses Routes to retrieve the arguments,
        override this method to customize the arguments your controller
        actions are called with.
        
        This method should return a dict.
        
        """
        req = self._py_object.request
        kargs = req.environ['pylons.routes_dict'].copy()
        kargs['environ'] = req.environ
        kargs['start_response'] = self.start_response
        kargs['pylons'] = self._py_object
        return kargs
    
    def _dispatch_call(self):
        """Handles dispatching the request to the function using
        Routes"""
        log_debug = self._pylons_log_debug
        req = self._py_object.request
        try:
            action = req.environ['pylons.routes_dict']['action']
        except KeyError:
            raise Exception("No action matched from Routes, unable to"
                            "determine action dispatch.")
        action_method = action.replace('-', '_')
        if log_debug:
            log.debug("Looking for %r method to handle the request",
                      action_method)
        try:
            func = getattr(self, action_method, None)
        except UnicodeEncodeError:
            func = None
        if action_method != 'start_response' and callable(func):
            # Store function used to handle request
            req.environ['pylons.action_method'] = func
            
            response = self._inspect_call(func)
        else:
            if log_debug:
                log.debug("Couldn't find %r method to handle response", action)
            if pylons.config['debug']:
                raise NotImplementedError('Action %r is not implemented' %
                                          action)
            else:
                response = HTTPNotFound()
        return response
    
    def __call__(self, environ, start_response):
        """The main call handler that is called to return a response"""
        log_debug = self._pylons_log_debug
                
        # Keep a local reference to the req/response objects
        self._py_object = environ['pylons.pylons']

        # Keep private methods private
        try:
            if environ['pylons.routes_dict']['action'][:1] in ('_', '-'):
                if log_debug:
                    log.debug("Action starts with _, private action not "
                              "allowed. Returning a 404 response")
                return HTTPNotFound()(environ, start_response)
        except KeyError:
            # The check later will notice that there's no action
            pass

        start_response_called = []
        def repl_start_response(status, headers, exc_info=None):
            response = self._py_object.response
            start_response_called.append(None)
            
            # Copy the headers from the global response
            if log_debug:
                log.debug("Merging pylons.response headers into "
                          "start_response call, status: %s", status)
            for header in response.headerlist:
                if header[0] == 'Set-Cookie' or header[0].startswith('X-'):
                    headers.append(header)
            return start_response(status, headers, exc_info)
        self.start_response = repl_start_response
        
        if hasattr(self, '__before__'):
            response = self._inspect_call(self.__before__)
            if hasattr(response, '_exception'):
                return response(environ, self.start_response)
        
        response = self._dispatch_call()
        if not start_response_called:
            self.start_response = start_response
            py_response = self._py_object.response
            # If its not a WSGI response, and we have content, it needs to
            # be wrapped in the response object
            if isinstance(response, str):
                if log_debug:
                    log.debug("Controller returned a string "
                              ", writing it to pylons.response")
                py_response.body = py_response.body + response
            elif isinstance(response, unicode):
                if log_debug:
                    log.debug("Controller returned a unicode string "
                              ", writing it to pylons.response")
                py_response.unicode_body = py_response.unicode_body + \
                        response
            elif hasattr(response, 'wsgi_response'):
                # It's either a legacy WSGIResponse object, or an exception
                # that got tossed.
                if log_debug:
                    log.debug("Controller returned a Response object, merging "
                              "it with pylons.response")
                if response is pylons.response:
                    # Only etag_cache() returns pylons.response
                    # (deprecated). Unwrap it to avoid a recursive loop
                    # (see ticket #508)
                    response = response._current_obj()
                    warnings.warn(pylons.legacy.response_warning,
                                  DeprecationWarning, 1)
                for name, value in py_response.headers.items():
                    if name.lower() == 'set-cookie':
                        response.headers.add(name, value)
                    else:
                        response.headers.setdefault(name, value)
                try:
                    registry = environ['paste.registry']
                    registry.replace(pylons.response, response)
                except KeyError:
                    # Ignore the case when someone removes the registry
                    pass
                py_response = response
            elif response is None:
                if log_debug:
                    log.debug("Controller returned None")
            else:
                if log_debug:
                    log.debug("Assuming controller returned an iterable, "
                              "setting it as pylons.response.app_iter")
                py_response.app_iter = response
            response = py_response
        
        if hasattr(self, '__after__'):
            after = self._inspect_call(self.__after__)
            if hasattr(after, '_exception'):
                return after(environ, self.start_response)
        
        if hasattr(response, 'wsgi_response'):
            # Copy the response object into the testing vars if we're testing
            if 'paste.testing_variables' in environ:
                environ['paste.testing_variables']['response'] = response
            if log_debug:
                log.debug("Calling Response object to return WSGI data")
            return response(environ, self.start_response)
        
        if log_debug:
            log.debug("Response assumed to be WSGI content, returning "
                      "un-touched")
        return response
