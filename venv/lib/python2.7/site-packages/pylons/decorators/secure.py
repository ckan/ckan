"""Security related decorators"""
import logging

from decorator import decorator
from webhelpers.html import secure_form

from pylons.controllers.util import abort, redirect_to
from pylons.decorators.util import get_pylons

__all__ = ['authenticate_form', 'https']

log = logging.getLogger(__name__)

csrf_detected_message = (
    "Cross-site request forgery detected, request denied. See "
    "http://en.wikipedia.org/wiki/Cross-site_request_forgery for more "
    "information.")

def authenticated_form(params):
    submitted_token = params.get(secure_form.token_key)
    return submitted_token is not None and \
        submitted_token == secure_form.authentication_token()

def authenticate_form(func, *args, **kwargs):
    """Decorator for authenticating a form
    
    This decorator uses an authorization token stored in the client's
    session for prevention of certain Cross-site request forgery (CSRF)
    attacks (See
    http://en.wikipedia.org/wiki/Cross-site_request_forgery for more
    information).

    For use with the ``webhelpers.html.secure_form`` helper functions.
    
    """
    request = get_pylons(args).request
    if authenticated_form(request.POST):
        del request.POST[secure_form.token_key]
        return func(*args, **kwargs)
    else:
        log.warn('Cross-site request forgery detected, request denied: %r '
                 'REMOTE_ADDR: %s' % (request, request.remote_addr))
        abort(403, detail=csrf_detected_message)
authenticate_form = decorator(authenticate_form)

def https(*redirect_args, **redirect_kwargs):
    """Decorator to redirect to the SSL version of a page if not currently
    using HTTPS. Takes as arguments the parameters to pass to redirect_to.
    (Specify no arguments necessary to redirect the current page).  Apply this
    decorator to controller methods (actions).

    Non-https POST requests are aborted (405 response code) by this decorator.

    Example:
    
    .. code-block:: python

        @https('/pylons') # redirect to HTTPS /pylons
        def index(self):
            #...

        # redirect to HTTPS /auth/login
        @https(controller='auth', action='login')
        def login(self):
            #...

        @https() # redirect to HTTPS version of myself
        def get(self):
            #...

    """
    def wrapper(func, *args, **kwargs):
        """Decorator Wrapper function"""
        request = get_pylons(args).request
        if request.scheme.lower() == 'https':
            return func(*args, **kwargs)
        else:
            if request.method.upper() != 'POST':
                redirect_kwargs['protocol'] = 'https' # ensure https
                log.debug('Redirecting non-https request: %s to redirect '
                          'args: *%r, **%r', request.path_info, redirect_args,
                          redirect_kwargs)
                redirect_to(*redirect_args, **redirect_kwargs)
            else:
                abort(405, headers=[('Allow', 'GET')]) # don't allow POSTs.
    return decorator(wrapper)
