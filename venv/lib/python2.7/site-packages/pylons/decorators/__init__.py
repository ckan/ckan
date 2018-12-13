"""Pylons Decorators

Common decorators intended for use in controllers. Additional
decorators for use with controllers are in the
:mod:`~pylons.decorators.cache`, :mod:`~pylons.decorators.rest` and
:mod:`~pylons.decorators.secure` modules.

"""
import logging
import sys
import warnings

import formencode
import simplejson
from decorator import decorator
from formencode import api, htmlfill, variabledecode
from webob import UnicodeMultiDict

from pylons.decorators.util import get_pylons
from pylons.i18n import _ as pylons_gettext

__all__ = ['jsonify', 'validate']

log = logging.getLogger(__name__)

def jsonify(func, *args, **kwargs):
    """Action decorator that formats output for JSON

    Given a function that will return content, this decorator will turn
    the result into JSON, with a content-type of 'application/json' and
    output it.
    
    """
    pylons = get_pylons(args)
    pylons.response.headers['Content-Type'] = 'application/json'
    data = func(*args, **kwargs)
    if isinstance(data, (list, tuple)):
        msg = "JSON responses with Array envelopes are susceptible to " \
              "cross-site data leak attacks, see " \
              "http://pylonshq.com/warnings/JSONArray"
        warnings.warn(msg, Warning, 2)
        log.warning(msg)
    log.debug("Returning JSON wrapped action output")
    return simplejson.dumps(data)
jsonify = decorator(jsonify)


def validate(schema=None, validators=None, form=None, variable_decode=False,
             dict_char='.', list_char='-', post_only=True, state=None,
             on_get=False, **htmlfill_kwargs):
    """Validate input either for a FormEncode schema, or individual
    validators

    Given a form schema or dict of validators, validate will attempt to
    validate the schema or validator list.

    If validation was successful, the valid result dict will be saved
    as ``self.form_result``. Otherwise, the action will be re-run as if
    it was a GET, and the output will be filled by FormEncode's
    htmlfill to fill in the form field errors.

    ``schema``
        Refers to a FormEncode Schema object to use during validation.
    ``form``
        Method used to display the form, which will be used to get the 
        HTML representation of the form for error filling.
    ``variable_decode``
        Boolean to indicate whether FormEncode's variable decode
        function should be run on the form input before validation.
    ``dict_char``
        Passed through to FormEncode. Toggles the form field naming 
        scheme used to determine what is used to represent a dict. This
        option is only applicable when used with variable_decode=True.
    ``list_char``
        Passed through to FormEncode. Toggles the form field naming
        scheme used to determine what is used to represent a list. This
        option is only applicable when used with variable_decode=True.
    ``post_only``
        Boolean that indicates whether or not GET (query) variables
        should be included during validation.
        
        .. warning::
            ``post_only`` applies to *where* the arguments to be
            validated come from. It does *not* restrict the form to
            only working with post, merely only checking POST vars.
    ``state``
        Passed through to FormEncode for use in validators that utilize
        a state object.
    ``on_get``
        Whether to validate on GET requests. By default only POST
        requests are validated.

    Example::

        class SomeController(BaseController):

            def create(self, id):
                return render('/myform.mako')

            @validate(schema=model.forms.myshema(), form='create')
            def update(self, id):
                # Do something with self.form_result
                pass

    """
    if state is None:
        state = PylonsFormEncodeState
    def wrapper(func, self, *args, **kwargs):
        """Decorator Wrapper function"""
        request = self._py_object.request
        errors = {}
        
        # Skip the validation if on_get is False and its a GET
        if not on_get and request.environ['REQUEST_METHOD'] == 'GET':
            return func(self, *args, **kwargs)
        
        # If they want post args only, use just the post args
        if post_only:
            params = request.POST
        else:
            params = request.params
        
        is_unicode_params = isinstance(params, UnicodeMultiDict)
        params = params.mixed()
        if variable_decode:
            log.debug("Running variable_decode on params")
            decoded = variabledecode.variable_decode(params, dict_char,
                                                     list_char)
        else:
            decoded = params

        if schema:
            log.debug("Validating against a schema")
            try:
                self.form_result = schema.to_python(decoded, state)
            except formencode.Invalid, e:
                errors = e.unpack_errors(variable_decode, dict_char, list_char)
        if validators:
            log.debug("Validating against provided validators")
            if isinstance(validators, dict):
                if not hasattr(self, 'form_result'):
                    self.form_result = {}
                for field, validator in validators.iteritems():
                    try:
                        self.form_result[field] = \
                            validator.to_python(decoded.get(field), state)
                    except formencode.Invalid, error:
                        errors[field] = error
        if errors:
            log.debug("Errors found in validation, parsing form with htmlfill "
                      "for errors")
            request.environ['REQUEST_METHOD'] = 'GET'
            self._py_object.c.form_errors = errors

            # If there's no form supplied, just continue with the current
            # function call.
            if not form:
                return func(self, *args, **kwargs)

            request.environ['pylons.routes_dict']['action'] = form
            response = self._dispatch_call()
            # XXX: Legacy WSGIResponse support
            legacy_response = False
            if hasattr(response, 'content'):
                form_content = ''.join(response.content)
                legacy_response = True
            else:
                form_content = response
                response = self._py_object.response
            
            # If the form_content is an exception response, return it
            if hasattr(form_content, '_exception'):
                return form_content
            
            # Ensure htmlfill can safely combine the form_content, params and
            # errors variables (that they're all of the same string type)
            if not is_unicode_params:
                log.debug("Raw string form params: ensuring the '%s' form and "
                          "FormEncode errors are converted to raw strings for "
                          "htmlfill", form)
                encoding = determine_response_charset(response)

                # WSGIResponse's content may (unlikely) be unicode
                if isinstance(form_content, unicode):
                    form_content = form_content.encode(encoding,
                                                       response.errors)

                # FormEncode>=0.7 errors are unicode (due to being localized
                # via ugettext). Convert any of the possible formencode
                # unpack_errors formats to contain raw strings
                errors = encode_formencode_errors(errors, encoding,
                                                  response.errors)
            elif not isinstance(form_content, unicode):
                log.debug("Unicode form params: ensuring the '%s' form is "
                          "converted to unicode for htmlfill", form)
                encoding = determine_response_charset(response)
                form_content = form_content.decode(encoding)

            form_content = htmlfill.render(form_content, defaults=params,
                                           errors=errors, **htmlfill_kwargs)
            if legacy_response:
                # Let the Controller merge the legacy response
                response.content = form_content
                return response
            else:
                return form_content
        return func(self, *args, **kwargs)
    return decorator(wrapper)


def determine_response_charset(response):
    """Determine the charset of the specified Response object,
    returning the default system encoding when none is set"""
    charset = response.charset
    if charset is None:
        charset = sys.getdefaultencoding()
    log.debug("Determined result charset to be: %s", charset)
    return charset


def encode_formencode_errors(errors, encoding, encoding_errors='strict'):
    """Encode any unicode values contained in a FormEncode errors dict
    to raw strings of the specified encoding"""
    if errors is None or isinstance(errors, str):
        # None or Just incase this is FormEncode<=0.7
        pass
    elif isinstance(errors, unicode):
        errors = errors.encode(encoding, encoding_errors)
    elif isinstance(errors, dict):
        for key, value in errors.iteritems():
            errors[key] = encode_formencode_errors(value, encoding,
                                                   encoding_errors)
    else:
        # Fallback to an iterable (a list)
        errors = [encode_formencode_errors(error, encoding, encoding_errors) \
                      for error in errors]
    return errors


def pylons_formencode_gettext(value):
    """Translates a string ``value`` using pylons gettext first and if
    that fails, formencode gettext.
    
    This allows to "merge" localized error messages from built-in
    FormEncode's validators with application-specific validators.

    """
    trans = pylons_gettext(value)
    if trans == value:
        # translation failed, try formencode
        trans = api._stdtrans(value)
    return trans


class PylonsFormEncodeState(object):
    """A ``state`` for FormEncode validate API that includes smart
    ``_`` hook.

    The FormEncode library used by validate() decorator has some
    provision for localizing error messages. In particular, it looks
    for attribute ``_`` in the application-specific state object that
    gets passed to every ``.to_python()`` call. If it is found, the
    ``_`` is assumed to be a gettext-like function and is called to
    localize error messages.

    One complication is that FormEncode ships with localized error
    messages for standard validators so the user may want to re-use
    them instead of gathering and translating everything from scratch.
    To allow this, we pass as ``_`` a function which looks up
    translation both in application and formencode message catalogs.
    
    """
    _ = staticmethod(pylons_formencode_gettext)
