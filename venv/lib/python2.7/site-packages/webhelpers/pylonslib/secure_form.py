"""
Secure Form Tag Helpers -- For prevention of Cross-site request forgery (CSRF)
attacks.

Generates form tags that include client-specific authorization tokens to be
verified by the destined web app.

PYRAMID USERS: Use the csrf_token methods built into Pyramid's ``Session``
object.  This implementation is incompatible with Pyramid.

Authorization tokens are stored in the client's session. The web app can then
verify the request's submitted authorization token with the value in the
client's session.

This ensures the request came from the originating page. See
http://en.wikipedia.org/wiki/Cross-site_request_forgery for more information.

Pylons provides an ``authenticate_form`` decorator that does this verification
on the behalf of controllers.

These helpers depend on Pylons' ``session`` object.  Most of them can be easily
ported to another framework by changing the API calls.

The helpers are implemented in such a way that it should be easy to create your
own helpers if you are using helpers for AJAX calls.

authentication_token() returns the current authentication token, creating one
and storing it in the session if it doesn't already exist.

auth_token_hidden_field() creates a hidden field (wrapped in an invisible div;
I don't know if this is necessary, but the old WebHelpers had it like this)
containing the authentication token.

secure_form() is form() plus auth_token_hidden_field().
"""

# Do not import Pylons at module level; only within functions.  All WebHelpers
# modules should be importable on any Python system for the standard
# regression tests.

import random

from webhelpers.html.builder import HTML, literal
from webhelpers.html.tags import form as insecure_form
from webhelpers.html.tags import hidden

token_key = "_authentication_token"

def authentication_token():
    """Return the current authentication token, creating one if one doesn't
    already exist.
    """
    from pylons import session
    if not token_key in session:
        try:
            token = str(random.getrandbits(128))
        except AttributeError: # Python < 2.4
            token = str(random.randrange(2**128))
        session[token_key] = token
        if hasattr(session, 'save'):
            session.save()
    return session[token_key]

def auth_token_hidden_field():
    token = hidden(token_key, authentication_token())
    return HTML.div(token, style="display: none;")

def secure_form(url, method="POST", multipart=False, **attrs):
    """Start a form tag that points the action to an url. This
    form tag will also include the hidden field containing
    the auth token.

    The url options should be given either as a string, or as a 
    ``url()`` function. The method for the form defaults to POST.

    Options:

    ``multipart``
        If set to True, the enctype is set to "multipart/form-data".
    ``method``
        The method to use when submitting the form, usually either 
        "GET" or "POST". If "PUT", "DELETE", or another verb is used, a
        hidden input with name _method is added to simulate the verb
        over POST.

    """
    form = insecure_form(url, method, multipart, **attrs)
    token = auth_token_hidden_field()
    return literal("%s\n%s" % (form, token))
