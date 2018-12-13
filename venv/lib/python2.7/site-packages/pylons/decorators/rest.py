"""REST decorators"""
import logging

from decorator import decorator

from pylons.controllers.util import abort
from pylons.decorators.util import get_pylons

__all__ = ['dispatch_on', 'restrict']

log = logging.getLogger(__name__)

def restrict(*methods):
    """Restricts access to the function depending on HTTP method

    Example:

    .. code-block:: python

        from pylons.decorators import rest

        class SomeController(BaseController):

            @rest.restrict('GET')
            def comment(self, id):
    
    """
    def check_methods(func, *args, **kwargs):
        """Wrapper for restrict"""
        if get_pylons(args).request.method not in methods:
            log.debug("Method not allowed by restrict")
            abort(405, headers=[('Allow', ','.join(methods))])
        return func(*args, **kwargs)
    return decorator(check_methods)

def dispatch_on(**method_map):
    """Dispatches to alternate controller methods based on HTTP method

    Multiple keyword arguments should be passed, with the keyword
    corresponding to the HTTP method to dispatch on (DELETE, POST, GET,
    etc.) and the value being the function to call. The value should be
    a string indicating the name of the function to dispatch to.

    Example:

    .. code-block:: python

        from pylons.decorators import rest

        class SomeController(BaseController):

            @rest.dispatch_on(POST='create_comment')
            def comment(self):
                # Do something with the comment

            def create_comment(self, id):
                # Do something if its a post to comment
    
    """
    def dispatcher(func, self, *args, **kwargs):
        """Wrapper for dispatch_on"""
        alt_method = method_map.get(get_pylons(args).request.method)
        if alt_method:
            alt_method = getattr(self, alt_method)
            log.debug("Dispatching to %s instead", alt_method)
            return self._inspect_call(alt_method, **kwargs)
        return func(self, *args, **kwargs)
    return decorator(dispatcher)
