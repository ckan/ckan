# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# (c) 2005 Ian Bicking, Clark C. Evans and contributors
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
# Some of this code was funded by: http://prometheusresearch.com
"""
HTTP Message Header Fields (see RFC 4229)

This contains general support for HTTP/1.1 message headers [1]_ in a
manner that supports WSGI ``environ`` [2]_ and ``response_headers``
[3]_. Specifically, this module defines a ``HTTPHeader`` class whose
instances correspond to field-name items.  The actual field-content for
the message-header is stored in the appropriate WSGI collection (either
the ``environ`` for requests, or ``response_headers`` for responses).

Each ``HTTPHeader`` instance is a callable (defining ``__call__``)
that takes one of the following:

  - an ``environ`` dictionary, returning the corresponding header
    value by according to the WSGI's ``HTTP_`` prefix mechanism, e.g.,
    ``USER_AGENT(environ)`` returns ``environ.get('HTTP_USER_AGENT')``

  - a ``response_headers`` list, giving a comma-delimited string for
    each corresponding ``header_value`` tuple entries (see below).

  - a sequence of string ``*args`` that are comma-delimited into
    a single string value: ``CONTENT_TYPE("text/html","text/plain")``
    returns ``"text/html, text/plain"``

  - a set of ``**kwargs`` keyword arguments that are used to create
    a header value, in a manner dependent upon the particular header in
    question (to make value construction easier and error-free):
    ``CONTENT_DISPOSITION(max_age=CONTENT_DISPOSITION.ONEWEEK)``
    returns ``"public, max-age=60480"``

Each ``HTTPHeader`` instance also provides several methods to act on
a WSGI collection, for removing and setting header values.

  ``delete(collection)``

    This method removes all entries of the corresponding header from
    the given collection (``environ`` or ``response_headers``), e.g.,
    ``USER_AGENT.delete(environ)`` deletes the 'HTTP_USER_AGENT' entry
    from the ``environ``.

  ``update(collection, *args, **kwargs)``

    This method does an in-place replacement of the given header entry,
    for example: ``CONTENT_LENGTH(response_headers,len(body))``

    The first argument is a valid ``environ`` dictionary or
    ``response_headers`` list; remaining arguments are passed on to
    ``__call__(*args, **kwargs)`` for value construction.

  ``apply(collection, **kwargs)``

    This method is similar to update, only that it may affect other
    headers.  For example, according to recommendations in RFC 2616,
    certain Cache-Control configurations should also set the
    ``Expires`` header for HTTP/1.0 clients. By default, ``apply()``
    is simply ``update()`` but limited to keyword arguments.

This particular approach to managing headers within a WSGI collection
has several advantages:

  1. Typos in the header name are easily detected since they become a
     ``NameError`` when executed.  The approach of using header strings
     directly can be problematic; for example, the following should
     return ``None`` : ``environ.get("HTTP_ACCEPT_LANGUAGES")``

  2. For specific headers with validation, using ``__call__`` will
     result in an automatic header value check.  For example, the
     _ContentDisposition header will reject a value having ``maxage``
     or ``max_age`` (the appropriate parameter is ``max-age`` ).

  3. When appending/replacing headers, the field-name has the suggested
     RFC capitalization (e.g. ``Content-Type`` or ``ETag``) for
     user-agents that incorrectly use case-sensitive matches.

  4. Some headers (such as ``Content-Type``) are 0, that is,
     only one entry of this type may occur in a given set of
     ``response_headers``.  This module knows about those cases and
     enforces this cardinality constraint.

  5. The exact details of WSGI header management are abstracted so
     the programmer need not worry about operational differences
     between ``environ`` dictionary or ``response_headers`` list.

  6. Sorting of ``HTTPHeaders`` is done following the RFC suggestion
     that general-headers come first, followed by request and response
     headers, and finishing with entity-headers.

  7. Special care is given to exceptional cases such as Set-Cookie
     which violates the RFC's recommendation about combining header
     content into a single entry using comma separation.

A particular difficulty with HTTP message headers is a categorization
of sorts as described in section 4.2:

    Multiple message-header fields with the same field-name MAY be
    present in a message if and only if the entire field-value for
    that header field is defined as a comma-separated list [i.e.,
    #(values)]. It MUST be possible to combine the multiple header
    fields into one "field-name: field-value" pair, without changing
    the semantics of the message, by appending each subsequent
    field-value to the first, each separated by a comma.

This creates three fundamentally different kinds of headers:

  - Those that do not have a #(values) production, and hence are
    singular and may only occur once in a set of response fields;
    this case is handled by the ``_SingleValueHeader`` subclass.

  - Those which have the #(values) production and follow the
    combining rule outlined above; our ``_MultiValueHeader`` case.

  - Those which are multi-valued, but cannot be combined (such as the
    ``Set-Cookie`` header due to its ``Expires`` parameter); or where
    combining them into a single header entry would cause common
    user-agents to fail (``WWW-Authenticate``, ``Warning``) since
    they fail to handle dates even when properly quoted. This case
    is handled by ``_MultiEntryHeader``.

Since this project does not have time to provide rigorous support
and validation for all headers, it does a basic construction of
headers listed in RFC 2616 (plus a few others) so that they can
be obtained by simply doing ``from paste.httpheaders import *``;
the name of the header instance is the "common name" less any
dashes to give CamelCase style names.

.. [1] http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2
.. [2] http://www.python.org/peps/pep-0333.html#environ-variables
.. [3] http://www.python.org/peps/pep-0333.html#the-start-response-callable

"""
import mimetypes
import urllib2
import re
from rfc822 import formatdate, parsedate_tz, mktime_tz
from time import time as now
from httpexceptions import HTTPBadRequest

__all__ = ['get_header', 'list_headers', 'normalize_headers',
           'HTTPHeader', 'EnvironVariable' ]

class EnvironVariable(str):
    """
    a CGI ``environ`` variable as described by WSGI

    This is a helper object so that standard WSGI ``environ`` variables
    can be extracted w/o syntax error possibility.
    """
    def __call__(self, environ):
        return environ.get(self,'')
    def __repr__(self):
        return '<EnvironVariable %s>' % self
    def update(self, environ, value):
        environ[self] = value
REMOTE_USER    = EnvironVariable("REMOTE_USER")
REMOTE_SESSION = EnvironVariable("REMOTE_SESSION")
AUTH_TYPE      = EnvironVariable("AUTH_TYPE")
REQUEST_METHOD = EnvironVariable("REQUEST_METHOD")
SCRIPT_NAME    = EnvironVariable("SCRIPT_NAME")
PATH_INFO      = EnvironVariable("PATH_INFO")

for _name, _obj in globals().items():
    if isinstance(_obj, EnvironVariable):
        __all__.append(_name)

_headers = {}

class HTTPHeader(object):
    """
    an HTTP header

    HTTPHeader instances represent a particular ``field-name`` of an
    HTTP message header. They do not hold a field-value, but instead
    provide operations that work on is corresponding values.  Storage
    of the actual field values is done with WSGI ``environ`` or
    ``response_headers`` as appropriate.  Typically, a sub-classes that
    represent a specific HTTP header, such as _ContentDisposition, are
    0.  Once constructed the HTTPHeader instances themselves
    are immutable and stateless.

    For purposes of documentation a "container" refers to either a
    WSGI ``environ`` dictionary, or a ``response_headers`` list.

    Member variables (and correspondingly constructor arguments).

      ``name``

          the ``field-name`` of the header, in "common form"
          as presented in RFC 2616; e.g. 'Content-Type'

      ``category``

          one of 'general', 'request', 'response', or 'entity'

      ``version``

          version of HTTP (informational) with which the header should
          be recognized

      ``sort_order``

          sorting order to be applied before sorting on
          field-name when ordering headers in a response

    Special Methods:

       ``__call__``

           The primary method of the HTTPHeader instance is to make
           it a callable, it takes either a collection, a string value,
           or keyword arguments and attempts to find/construct a valid
           field-value

       ``__lt__``

           This method is used so that HTTPHeader objects can be
           sorted in a manner suggested by RFC 2616.

       ``__str__``

           The string-value for instances of this class is
           the ``field-name``.

    Primary Methods:

       ``delete()``

           remove the all occurrences (if any) of the given
           header in the collection provided

       ``update()``

           replaces (if they exist) all field-value items
           in the given collection with the value provided

       ``tuples()``

           returns a set of (field-name, field-value) tuples
           5 for extending ``response_headers``

    Custom Methods (these may not be implemented):

       ``apply()``

           similar to ``update``, but with two differences; first,
           only keyword arguments can be used, and second, specific
           sub-classes may introduce side-effects

       ``parse()``

           converts a string value of the header into a more usable
           form, such as time in seconds for a date header, etc.

    The collected versions of initialized header instances are immediately
    registered and accessible through the ``get_header`` function.  Do not
    inherit from this directly, use one of ``_SingleValueHeader``,
    ``_MultiValueHeader``, or ``_MultiEntryHeader`` as appropriate.
    """

    #
    # Things which can be customized
    #
    version = '1.1'
    category = 'general'
    reference = ''
    extensions = {}

    def compose(self, **kwargs):
        """
        build header value from keyword arguments

        This method is used to build the corresponding header value when
        keyword arguments (or no arguments) were provided.  The result
        should be a sequence of values.  For example, the ``Expires``
        header takes a keyword argument ``time`` (e.g. time.time()) from
        which it returns a the corresponding date.
        """
        raise NotImplementedError()

    def parse(self, *args, **kwargs):
        """
        convert raw header value into more usable form

        This method invokes ``values()`` with the arguments provided,
        parses the header results, and then returns a header-specific
        data structure corresponding to the header.  For example, the
        ``Expires`` header returns seconds (as returned by time.time())
        """
        raise NotImplementedError()

    def apply(self, collection, **kwargs):
        """
        update the collection /w header value (may have side effects)

        This method is similar to ``update`` only that usage may result
        in other headers being changed as recommended by the corresponding
        specification.  The return value is defined by the particular
        sub-class. For example, the ``_CacheControl.apply()`` sets the
        ``Expires`` header in addition to its normal behavior.
        """
        self.update(collection, **kwargs)

    #
    # Things which are standardized (mostly)
    #
    def __new__(cls, name, category=None, reference=None, version=None):
        """
        construct a new ``HTTPHeader`` instance

        We use the ``__new__`` operator to ensure that only one
        ``HTTPHeader`` instance exists for each field-name, and to
        register the header so that it can be found/enumerated.
        """
        self = get_header(name, raiseError=False)
        if self:
            # Allow the registration to happen again, but assert
            # that everything is identical.
            assert self.name == name, \
                "duplicate registration with different capitalization"
            assert self.category == category, \
                "duplicate registration with different category"
            assert cls == self.__class__, \
                "duplicate registration with different class"
            return self

        self = object.__new__(cls)
        self.name = name
        assert isinstance(self.name, str)
        self.category = category or self.category
        self.version  = version or self.version
        self.reference = reference or self.reference
        _headers[self.name.lower()] = self
        self.sort_order = {'general': 1, 'request': 2,
                           'response': 3, 'entity': 4 }[self.category]
        self._environ_name = getattr(self, '_environ_name',
                                'HTTP_'+ self.name.upper().replace("-","_"))
        self._headers_name = getattr(self, '_headers_name',
                                 self.name.lower())
        assert self.version in ('1.1', '1.0', '0.9')
        return self

    def __str__(self):
        return self.name

    def __lt__(self, other):
        """
        sort header instances as specified by RFC 2616

        Re-define sorting so that general headers are first, followed
        by request/response headers, and then entity headers.  The
        list.sort() methods use the less-than operator for this purpose.
        """
        if isinstance(other, HTTPHeader):
            if self.sort_order != other.sort_order:
                return self.sort_order < other.sort_order
            return self.name < other.name
        return False

    def __repr__(self):
        ref = self.reference and (' (%s)' % self.reference) or ''
        return '<%s %s%s>' % (self.__class__.__name__, self.name, ref)

    def values(self, *args, **kwargs):
        """
        find/construct field-value(s) for the given header

        Resolution is done according to the following arguments:

        - If only keyword arguments are given, then this is equivalent
          to ``compose(**kwargs)``.

        - If the first (and only) argument is a dict, it is assumed
          to be a WSGI ``environ`` and the result of the corresponding
          ``HTTP_`` entry is returned.

        - If the first (and only) argument is a list, it is assumed
          to be a WSGI ``response_headers`` and the field-value(s)
          for this header are collected and returned.

        - In all other cases, the arguments are collected, checked that
          they are string values, possibly verified by the header's
          logic, and returned.

        At this time it is an error to provide keyword arguments if args
        is present (this might change).  It is an error to provide both
        a WSGI object and also string arguments.  If no arguments are
        provided, then ``compose()`` is called to provide a default
        value for the header; if there is not default it is an error.
        """
        if not args:
            return self.compose(**kwargs)
        if list == type(args[0]):
            assert 1 == len(args)
            result = []
            name = self.name.lower()
            for value in [value for header, value in args[0]
                         if header.lower() == name]:
                result.append(value)
            return result
        if dict == type(args[0]):
            assert 1 == len(args) and 'wsgi.version' in args[0]
            value = args[0].get(self._environ_name)
            if not value:
                return ()
            return (value,)
        for item in args:
            assert not type(item) in (dict, list)
        return args

    def __call__(self, *args, **kwargs):
        """
        converts ``values()`` into a string value

        This method converts the results of ``values()`` into a string
        value for common usage.  By default, it is asserted that only
        one value exists; if you need to access all values then either
        call ``values()`` directly, or inherit ``_MultiValueHeader``
        which overrides this method to return a comma separated list of
        values as described by section 4.2 of RFC 2616.
        """
        values = self.values(*args, **kwargs)
        assert isinstance(values, (tuple, list))
        if not values:
            return ''
        assert len(values) == 1, "more than one value: %s" % repr(values)
        return str(values[0]).strip()

    def delete(self, collection):
        """
        removes all occurances of the header from the collection provided
        """
        if type(collection) == dict:
            if self._environ_name in collection:
                del collection[self._environ_name]
            return self
        assert list == type(collection)
        i = 0
        while i < len(collection):
            if collection[i][0].lower() == self._headers_name:
                del collection[i]
                continue
            i += 1

    def update(self, collection, *args, **kwargs):
        """
        updates the collection with the provided header value

        This method replaces (in-place when possible) all occurrences of
        the given header with the provided value.  If no value is
        provided, this is the same as ``remove`` (note that this case
        can only occur if the target is a collection w/o a corresponding
        header value). The return value is the new header value (which
        could be a list for ``_MultiEntryHeader`` instances).
        """
        value = self.__call__(*args, **kwargs)
        if not value:
            self.delete(collection)
            return
        if type(collection) == dict:
            collection[self._environ_name] = value
            return
        assert list == type(collection)
        i = 0
        found = False
        while i < len(collection):
            if collection[i][0].lower() == self._headers_name:
                if found:
                    del collection[i]
                    continue
                collection[i] = (self.name, value)
                found = True
            i += 1
        if not found:
            collection.append((self.name, value))

    def tuples(self, *args, **kwargs):
        value = self.__call__(*args, **kwargs)
        if not value:
            return ()
        return [(self.name, value)]

class _SingleValueHeader(HTTPHeader):
    """
    a ``HTTPHeader`` with exactly a single value

    This is the default behavior of ``HTTPHeader`` where returning a
    the string-value of headers via ``__call__`` assumes that only
    a single value exists.
    """
    pass

class _MultiValueHeader(HTTPHeader):
    """
    a ``HTTPHeader`` with one or more values

    The field-value for these header instances is is allowed to be more
    than one value; whereby the ``__call__`` method returns a comma
    separated list as described by section 4.2 of RFC 2616.
    """

    def __call__(self, *args, **kwargs):
        results = self.values(*args, **kwargs)
        if not results:
            return ''
        return ", ".join([str(v).strip() for v in results])

    def parse(self, *args, **kwargs):
        value = self.__call__(*args, **kwargs)
        values = value.split(',')
        return [
            v.strip() for v in values
            if v.strip()]

class _MultiEntryHeader(HTTPHeader):
    """
    a multi-value ``HTTPHeader`` where items cannot be combined with a comma

    This header is multi-valued, but the values should not be combined
    with a comma since the header is not in compliance with RFC 2616
    (Set-Cookie due to Expires parameter) or which common user-agents do
    not behave well when the header values are combined.
    """

    def update(self, collection, *args, **kwargs):
        assert list == type(collection), "``environ`` may not be updated"
        self.delete(collection)
        collection.extend(self.tuples(*args, **kwargs))

    def tuples(self, *args, **kwargs):
        values = self.values(*args, **kwargs)
        if not values:
            return ()
        return [(self.name, value.strip()) for value in values]

def get_header(name, raiseError=True):
    """
    find the given ``HTTPHeader`` instance

    This function finds the corresponding ``HTTPHeader`` for the
    ``name`` provided.  So that python-style names can be used,
    underscores are converted to dashes before the lookup.
    """
    retval = _headers.get(str(name).strip().lower().replace("_","-"))
    if not retval and raiseError:
        raise AssertionError("'%s' is an unknown header" % name)
    return retval

def list_headers(general=None, request=None, response=None, entity=None):
    " list all headers for a given category "
    if not (general or request or response or entity):
        general = request = response = entity = True
    search = []
    for (bool, strval) in ((general, 'general'), (request, 'request'),
                           (response, 'response'), (entity, 'entity')):
        if bool:
            search.append(strval)
    return [head for head in _headers.values() if head.category in search]

def normalize_headers(response_headers, strict=True):
    """
    sort headers as suggested by  RFC 2616

    This alters the underlying response_headers to use the common
    name for each header; as well as sorting them with general
    headers first, followed by request/response headers, then
    entity headers, and unknown headers last.
    """
    category = {}
    for idx in range(len(response_headers)):
        (key, val) = response_headers[idx]
        head = get_header(key, strict)
        if not head:
            newhead = '-'.join([x.capitalize() for x in
                                key.replace("_","-").split("-")])
            response_headers[idx] = (newhead, val)
            category[newhead] = 4
            continue
        response_headers[idx] = (str(head), val)
        category[str(head)] = head.sort_order
    def compare(a, b):
        ac = category[a[0]]
        bc = category[b[0]]
        if ac == bc:
            return cmp(a[0], b[0])
        return cmp(ac, bc)
    response_headers.sort(compare)

class _DateHeader(_SingleValueHeader):
    """
    handle date-based headers

    This extends the ``_SingleValueHeader`` object with specific
    treatment of time values:

    - It overrides ``compose`` to provide a sole keyword argument
      ``time`` which is an offset in seconds from the current time.

    - A ``time`` method is provided which parses the given value
      and returns the current time value.
    """

    def compose(self, time=None, delta=None):
        time = time or now()
        if delta:
            assert type(delta) == int
            time += delta
        return (formatdate(time),)

    def parse(self, *args, **kwargs):
        """ return the time value (in seconds since 1970) """
        value = self.__call__(*args, **kwargs)
        if value:
            try:
                return mktime_tz(parsedate_tz(value))
            except (TypeError, OverflowError):
                raise HTTPBadRequest((
                    "Received an ill-formed timestamp for %s: %s\r\n") %
                    (self.name, value))

#
# Following are specific HTTP headers. Since these classes are mostly
# singletons, there is no point in keeping the class around once it has
# been instantiated, so we use the same name.
#

class _CacheControl(_MultiValueHeader):
    """
    Cache-Control, RFC 2616 14.9  (use ``CACHE_CONTROL``)

    This header can be constructed (using keyword arguments), by
    first specifying one of the following mechanisms:

      ``public``

          if True, this argument specifies that the
          response, as a whole, may be cashed.

      ``private``

          if True, this argument specifies that the response, as a
          whole, may be cashed; this implementation does not support
          the enumeration of private fields

      ``no_cache``

          if True, this argument specifies that the response, as a
          whole, may not be cashed; this implementation does not
          support the enumeration of private fields

    In general, only one of the above three may be True, the other 2
    must then be False or None.  If all three are None, then the cache
    is assumed to be ``public``.  Following one of these mechanism
    specifiers are various modifiers:

      ``no_store``

          indicates if content may be stored on disk;
          otherwise cache is limited to memory (note:
          users can still save the data, this applies
          to intermediate caches)

      ``max_age``

          the maximum duration (in seconds) for which
          the content should be cached; if ``no-cache``
          is specified, this defaults to 0 seconds

      ``s_maxage``

          the maximum duration (in seconds) for which the
          content should be allowed in a shared cache.

      ``no_transform``

          specifies that an intermediate cache should
          not convert the content from one type to
          another (e.g. transform a BMP to a PNG).

      ``extensions``

          gives additional cache-control extensions,
          such as items like, community="UCI" (14.9.6)

    The usage of ``apply()`` on this header has side-effects. As
    recommended by RFC 2616, if ``max_age`` is provided, then then the
    ``Expires`` header is also calculated for HTTP/1.0 clients and
    proxies (this is done at the time ``apply()`` is called).  For
    ``no-cache`` and for ``private`` cases, we either do not want the
    response cached or do not want any response accidently returned to
    other users; so to prevent this case, we set the ``Expires`` header
    to the time of the request, signifying to HTTP/1.0 transports that
    the content isn't to be cached.  If you are using SSL, your
    communication is already "private", so to work with HTTP/1.0
    browsers over SSL, consider specifying your cache as ``public`` as
    the distinction between public and private is moot.
    """

    # common values for max-age; "good enough" approximates
    ONE_HOUR  = 60*60
    ONE_DAY   = ONE_HOUR * 24
    ONE_WEEK  = ONE_DAY * 7
    ONE_MONTH = ONE_DAY * 30
    ONE_YEAR  = ONE_WEEK * 52

    def _compose(self, public=None, private=None, no_cache=None,
                 no_store=False, max_age=None, s_maxage=None,
                 no_transform=False, **extensions):
        assert isinstance(max_age, (type(None), int))
        assert isinstance(s_maxage, (type(None), int))
        expires = 0
        result = []
        if private is True:
            assert not public and not no_cache and not s_maxage
            result.append('private')
        elif no_cache is True:
            assert not public and not private and not max_age
            result.append('no-cache')
        else:
            assert public is None or public is True
            assert not private and not no_cache
            expires = max_age
            result.append('public')
        if no_store:
            result.append('no-store')
        if no_transform:
            result.append('no-transform')
        if max_age is not None:
            result.append('max-age=%d' % max_age)
        if s_maxage is not None:
            result.append('s-maxage=%d' % s_maxage)
        for (k, v) in extensions.items():
            if k not in self.extensions:
                raise AssertionError("unexpected extension used: '%s'" % k)
            result.append('%s="%s"' % (k.replace("_", "-"), v))
        return (result, expires)

    def compose(self, **kwargs):
        (result, expires) = self._compose(**kwargs)
        return result

    def apply(self, collection, **kwargs):
        """ returns the offset expiration in seconds """
        (result, expires) = self._compose(**kwargs)
        if expires is not None:
            EXPIRES.update(collection, delta=expires)
        self.update(collection, *result)
        return expires

_CacheControl('Cache-Control', 'general', 'RFC 2616, 14.9')

class _ContentType(_SingleValueHeader):
    """
    Content-Type, RFC 2616 section 14.17

    Unlike other headers, use the CGI variable instead.
    """
    version = '1.0'
    _environ_name = 'CONTENT_TYPE'

    # common mimetype constants
    UNKNOWN    = 'application/octet-stream'
    TEXT_PLAIN = 'text/plain'
    TEXT_HTML  = 'text/html'
    TEXT_XML   = 'text/xml'

    def compose(self, major=None, minor=None, charset=None):
        if not major:
            if minor in ('plain', 'html', 'xml'):
                major = 'text'
            else:
                assert not minor and not charset
                return (self.UNKNOWN,)
        if not minor:
            minor = "*"
        result = "%s/%s" % (major, minor)
        if charset:
            result += "; charset=%s" % charset
        return (result,)

_ContentType('Content-Type', 'entity', 'RFC 2616, 14.17')

class _ContentLength(_SingleValueHeader):
    """
    Content-Length, RFC 2616 section 14.13

    Unlike other headers, use the CGI variable instead.
    """
    version = "1.0"
    _environ_name = 'CONTENT_LENGTH'

_ContentLength('Content-Length', 'entity', 'RFC 2616, 14.13')

class _ContentDisposition(_SingleValueHeader):
    """
    Content-Disposition, RFC 2183 (use ``CONTENT_DISPOSITION``)

    This header can be constructed (using keyword arguments),
    by first specifying one of the following mechanisms:

      ``attachment``

          if True, this specifies that the content should not be
          shown in the browser and should be handled externally,
          even if the browser could render the content

      ``inline``

         exclusive with attachment; indicates that the content
         should be rendered in the browser if possible, but
         otherwise it should be handled externally

    Only one of the above 2 may be True.  If both are None, then
    the disposition is assumed to be an ``attachment``. These are
    distinct fields since support for field enumeration may be
    added in the future.

      ``filename``

          the filename parameter, if any, to be reported; if
          this is None, then the current object's filename
          attribute is used

    The usage of ``apply()`` on this header has side-effects. If
    filename is provided, and Content-Type is not set or is
    'application/octet-stream', then the mimetypes.guess is used to
    upgrade the Content-Type setting.
    """

    def _compose(self, attachment=None, inline=None, filename=None):
        result = []
        if inline is True:
            assert not attachment
            result.append('inline')
        else:
            assert not inline
            result.append('attachment')
        if filename:
            assert '"' not in filename
            filename = filename.split("/")[-1]
            filename = filename.split("\\")[-1]
            result.append('filename="%s"' % filename)
        return (("; ".join(result),), filename)

    def compose(self, **kwargs):
        (result, mimetype) = self._compose(**kwargs)
        return result

    def apply(self, collection, **kwargs):
        """ return the new Content-Type side-effect value """
        (result, filename) = self._compose(**kwargs)
        mimetype = CONTENT_TYPE(collection)
        if filename and (not mimetype or CONTENT_TYPE.UNKNOWN == mimetype):
            mimetype, _ = mimetypes.guess_type(filename)
            if mimetype and CONTENT_TYPE.UNKNOWN != mimetype:
                CONTENT_TYPE.update(collection, mimetype)
        self.update(collection, *result)
        return mimetype

_ContentDisposition('Content-Disposition', 'entity', 'RFC 2183')

class _IfModifiedSince(_DateHeader):
    """
    If-Modified-Since, RFC 2616 section 14.25
    """
    version = '1.0'

    def __call__(self, *args, **kwargs):
        """
        Split the value on ';' incase the header includes extra attributes. E.g.
        IE 6 is known to send:
        If-Modified-Since: Sun, 25 Jun 2006 20:36:35 GMT; length=1506
        """
        return _DateHeader.__call__(self, *args, **kwargs).split(';', 1)[0]

    def parse(self, *args, **kwargs):
        value = _DateHeader.parse(self, *args, **kwargs)
        if value and value > now():
            raise HTTPBadRequest((
              "Please check your system clock.\r\n"
              "According to this server, the time provided in the\r\n"
              "%s header is in the future.\r\n") % self.name)
        return value
_IfModifiedSince('If-Modified-Since', 'request', 'RFC 2616, 14.25')

class _Range(_MultiValueHeader):
    """
    Range, RFC 2616 14.35 (use ``RANGE``)

    According to section 14.16, the response to this message should be a
    206 Partial Content and that if multiple non-overlapping byte ranges
    are requested (it is an error to request multiple overlapping
    ranges) the result should be sent as multipart/byteranges mimetype.

    The server should respond with '416 Requested Range Not Satisfiable'
    if the requested ranges are out-of-bounds.  The specification also
    indicates that a syntax error in the Range request should result in
    the header being ignored rather than a '400 Bad Request'.
    """

    def parse(self, *args, **kwargs):
        """
        Returns a tuple (units, list), where list is a sequence of
        (begin, end) tuples; and end is None if it was not provided.
        """
        value = self.__call__(*args, **kwargs)
        if not value:
            return None
        ranges = []
        last_end   = -1
        try:
            (units, range) = value.split("=", 1)
            units = units.strip().lower()
            for item in range.split(","):
                (begin, end) = item.split("-")
                if not begin.strip():
                    begin = 0
                else:
                    begin = int(begin)
                if begin <= last_end:
                    raise ValueError()
                if not end.strip():
                    end = None
                else:
                    end = int(end)
                last_end = end
                ranges.append((begin, end))
        except ValueError:
            # In this case where the Range header is malformed,
            # section 14.16 says to treat the request as if the
            # Range header was not present.  How do I log this?
            return None
        return (units, ranges)
_Range('Range', 'request', 'RFC 2616, 14.35')

class _AcceptLanguage(_MultiValueHeader):
    """
    Accept-Language, RFC 2616 section 14.4
    """

    def parse(self, *args, **kwargs):
        """
        Return a list of language tags sorted by their "q" values.  For example,
        "en-us,en;q=0.5" should return ``["en-us", "en"]``.  If there is no
        ``Accept-Language`` header present, default to ``[]``.
        """
        header = self.__call__(*args, **kwargs)
        if header is None:
            return []
        langs = [v for v in header.split(",") if v]
        qs = []
        for lang in langs:
            pieces = lang.split(";")
            lang, params = pieces[0].strip().lower(), pieces[1:]
            q = 1
            for param in params:
                if '=' not in param:
                    # Malformed request; probably a bot, we'll ignore
                    continue
                lvalue, rvalue = param.split("=")
                lvalue = lvalue.strip().lower()
                rvalue = rvalue.strip()
                if lvalue == "q":
                    q = float(rvalue)
            qs.append((lang, q))
        qs.sort(lambda a, b: -cmp(a[1], b[1]))
        return [lang for (lang, q) in qs]
_AcceptLanguage('Accept-Language', 'request', 'RFC 2616, 14.4')

class _AcceptRanges(_MultiValueHeader):
    """
    Accept-Ranges, RFC 2616 section 14.5
    """
    def compose(self, none=None, bytes=None):
        if bytes:
            return ('bytes',)
        return ('none',)
_AcceptRanges('Accept-Ranges', 'response', 'RFC 2616, 14.5')

class _ContentRange(_SingleValueHeader):
    """
    Content-Range, RFC 2616 section 14.6
    """
    def compose(self, first_byte=None, last_byte=None, total_length=None):
        retval = "bytes %d-%d/%d" % (first_byte, last_byte, total_length)
        assert last_byte == -1 or first_byte <= last_byte
        assert last_byte  < total_length
        return (retval,)
_ContentRange('Content-Range', 'entity', 'RFC 2616, 14.6')

class _Authorization(_SingleValueHeader):
    """
    Authorization, RFC 2617 (RFC 2616, 14.8)
    """
    def compose(self, digest=None, basic=None, username=None, password=None,
                challenge=None, path=None, method=None):
        assert username and password
        if basic or not challenge:
            assert not digest
            userpass = "%s:%s" % (username.strip(), password.strip())
            return "Basic %s" % userpass.encode('base64').strip()
        assert challenge and not basic
        path = path or "/"
        (_, realm) = challenge.split('realm="')
        (realm, _) = realm.split('"', 1)
        auth = urllib2.AbstractDigestAuthHandler()
        auth.add_password(realm, path, username, password)
        (token, challenge) = challenge.split(' ', 1)
        chal = urllib2.parse_keqv_list(urllib2.parse_http_list(challenge))
        class FakeRequest(object):
            def get_full_url(self):
                return path
            def has_data(self):
                return False
            def get_method(self):
                return method or "GET"
            get_selector = get_full_url
        retval = "Digest %s" % auth.get_authorization(FakeRequest(), chal)
        return (retval,)
_Authorization('Authorization', 'request', 'RFC 2617')

#
# For now, construct a minimalistic version of the field-names; at a
# later date more complicated headers may sprout content constructors.
# The items commented out have concrete variants.
#
for (name,              category, version, style,      comment) in \
(("Accept"             ,'request' ,'1.1','multi-value','RFC 2616, 14.1' )
,("Accept-Charset"     ,'request' ,'1.1','multi-value','RFC 2616, 14.2' )
,("Accept-Encoding"    ,'request' ,'1.1','multi-value','RFC 2616, 14.3' )
#,("Accept-Language"    ,'request' ,'1.1','multi-value','RFC 2616, 14.4' )
#,("Accept-Ranges"      ,'response','1.1','multi-value','RFC 2616, 14.5' )
,("Age"                ,'response','1.1','singular'   ,'RFC 2616, 14.6' )
,("Allow"              ,'entity'  ,'1.0','multi-value','RFC 2616, 14.7' )
#,("Authorization"      ,'request' ,'1.0','singular'   ,'RFC 2616, 14.8' )
#,("Cache-Control"      ,'general' ,'1.1','multi-value','RFC 2616, 14.9' )
,("Cookie"             ,'request' ,'1.0','multi-value','RFC 2109/Netscape')
,("Connection"         ,'general' ,'1.1','multi-value','RFC 2616, 14.10')
,("Content-Encoding"   ,'entity'  ,'1.0','multi-value','RFC 2616, 14.11')
#,("Content-Disposition",'entity'  ,'1.1','multi-value','RFC 2616, 15.5' )
,("Content-Language"   ,'entity'  ,'1.1','multi-value','RFC 2616, 14.12')
#,("Content-Length"     ,'entity'  ,'1.0','singular'   ,'RFC 2616, 14.13')
,("Content-Location"   ,'entity'  ,'1.1','singular'   ,'RFC 2616, 14.14')
,("Content-MD5"        ,'entity'  ,'1.1','singular'   ,'RFC 2616, 14.15')
#,("Content-Range"      ,'entity'  ,'1.1','singular'   ,'RFC 2616, 14.16')
#,("Content-Type"       ,'entity'  ,'1.0','singular'   ,'RFC 2616, 14.17')
,("Date"               ,'general' ,'1.0','date-header','RFC 2616, 14.18')
,("ETag"               ,'response','1.1','singular'   ,'RFC 2616, 14.19')
,("Expect"             ,'request' ,'1.1','multi-value','RFC 2616, 14.20')
,("Expires"            ,'entity'  ,'1.0','date-header','RFC 2616, 14.21')
,("From"               ,'request' ,'1.0','singular'   ,'RFC 2616, 14.22')
,("Host"               ,'request' ,'1.1','singular'   ,'RFC 2616, 14.23')
,("If-Match"           ,'request' ,'1.1','multi-value','RFC 2616, 14.24')
#,("If-Modified-Since"  ,'request' ,'1.0','date-header','RFC 2616, 14.25')
,("If-None-Match"      ,'request' ,'1.1','multi-value','RFC 2616, 14.26')
,("If-Range"           ,'request' ,'1.1','singular'   ,'RFC 2616, 14.27')
,("If-Unmodified-Since",'request' ,'1.1','date-header' ,'RFC 2616, 14.28')
,("Last-Modified"      ,'entity'  ,'1.0','date-header','RFC 2616, 14.29')
,("Location"           ,'response','1.0','singular'   ,'RFC 2616, 14.30')
,("Max-Forwards"       ,'request' ,'1.1','singular'   ,'RFC 2616, 14.31')
,("Pragma"             ,'general' ,'1.0','multi-value','RFC 2616, 14.32')
,("Proxy-Authenticate" ,'response','1.1','multi-value','RFC 2616, 14.33')
,("Proxy-Authorization",'request' ,'1.1','singular'   ,'RFC 2616, 14.34')
#,("Range"              ,'request' ,'1.1','multi-value','RFC 2616, 14.35')
,("Referer"            ,'request' ,'1.0','singular'   ,'RFC 2616, 14.36')
,("Retry-After"        ,'response','1.1','singular'   ,'RFC 2616, 14.37')
,("Server"             ,'response','1.0','singular'   ,'RFC 2616, 14.38')
,("Set-Cookie"         ,'response','1.0','multi-entry','RFC 2109/Netscape')
,("TE"                 ,'request' ,'1.1','multi-value','RFC 2616, 14.39')
,("Trailer"            ,'general' ,'1.1','multi-value','RFC 2616, 14.40')
,("Transfer-Encoding"  ,'general' ,'1.1','multi-value','RFC 2616, 14.41')
,("Upgrade"            ,'general' ,'1.1','multi-value','RFC 2616, 14.42')
,("User-Agent"         ,'request' ,'1.0','singular'   ,'RFC 2616, 14.43')
,("Vary"               ,'response','1.1','multi-value','RFC 2616, 14.44')
,("Via"                ,'general' ,'1.1','multi-value','RFC 2616, 14.45')
,("Warning"            ,'general' ,'1.1','multi-entry','RFC 2616, 14.46')
,("WWW-Authenticate"   ,'response','1.0','multi-entry','RFC 2616, 14.47')):
    klass = {'multi-value': _MultiValueHeader,
             'multi-entry': _MultiEntryHeader,
             'date-header': _DateHeader,
             'singular'   : _SingleValueHeader}[style]
    klass(name, category, comment, version).__doc__ = comment
    del klass

for head in _headers.values():
    headname = head.name.replace("-","_").upper()
    locals()[headname] = head
    __all__.append(headname)

__pudge_all__ = __all__[:]
for _name, _obj in globals().items():
    if isinstance(_obj, type) and issubclass(_obj, HTTPHeader):
        __pudge_all__.append(_name)
