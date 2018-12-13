# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""Routines to generate WSGI responses"""

############################################################
## Headers
############################################################
import warnings

class HeaderDict(dict):

    """
    This represents response headers.  It handles the headers as a
    dictionary, with case-insensitive keys.

    Also there is an ``.add(key, value)`` method, which sets the key,
    or adds the value to the current value (turning it into a list if
    necessary).

    For passing to WSGI there is a ``.headeritems()`` method which is
    like ``.items()`` but unpacks value that are lists.  It also
    handles encoding -- all headers are encoded in ASCII (if they are
    unicode).

    @@: Should that encoding be ISO-8859-1 or UTF-8?  I'm not sure
    what the spec says.
    """

    def __getitem__(self, key):
        return dict.__getitem__(self, self.normalize(key))

    def __setitem__(self, key, value):
        dict.__setitem__(self, self.normalize(key), value)

    def __delitem__(self, key):
        dict.__delitem__(self, self.normalize(key))

    def __contains__(self, key):
        return dict.__contains__(self, self.normalize(key))

    has_key = __contains__

    def get(self, key, failobj=None):
        return dict.get(self, self.normalize(key), failobj)

    def setdefault(self, key, failobj=None):
        return dict.setdefault(self, self.normalize(key), failobj)

    def pop(self, key, *args):
        return dict.pop(self, self.normalize(key), *args)

    def update(self, other):
        for key in other:
            self[self.normalize(key)] = other[key]

    def normalize(self, key):
        return str(key).lower().strip()

    def add(self, key, value):
        key = self.normalize(key)
        if key in self:
            if isinstance(self[key], list):
                self[key].append(value)
            else:
                self[key] = [self[key], value]
        else:
            self[key] = value

    def headeritems(self):
        result = []
        for key, value in self.items():
            if isinstance(value, list):
                for v in value:
                    result.append((key, str(v)))
            else:
                result.append((key, str(value)))
        return result

    #@classmethod
    def fromlist(cls, seq):
        self = cls()
        for name, value in seq:
            self.add(name, value)
        return self

    fromlist = classmethod(fromlist)

def has_header(headers, name):
    """
    Is header named ``name`` present in headers?
    """
    name = name.lower()
    for header, value in headers:
        if header.lower() == name:
            return True
    return False

def header_value(headers, name):
    """
    Returns the header's value, or None if no such header.  If a
    header appears more than once, all the values of the headers
    are joined with ','.   Note that this is consistent /w RFC 2616
    section 4.2 which states:

        It MUST be possible to combine the multiple header fields
        into one "field-name: field-value" pair, without changing
        the semantics of the message, by appending each subsequent
        field-value to the first, each separated by a comma.

    However, note that the original netscape usage of 'Set-Cookie',
    especially in MSIE which contains an 'expires' date will is not
    compatible with this particular concatination method.
    """
    name = name.lower()
    result = [value for header, value in headers
              if header.lower() == name]
    if result:
        return ','.join(result)
    else:
        return None

def remove_header(headers, name):
    """
    Removes the named header from the list of headers.  Returns the
    value of that header, or None if no header found.  If multiple
    headers are found, only the last one is returned.
    """
    name = name.lower()
    i = 0
    result = None
    while i < len(headers):
        if headers[i][0].lower() == name:
            result = headers[i][1]
            del headers[i]
            continue
        i += 1
    return result

def replace_header(headers, name, value):
    """
    Updates the headers replacing the first occurance of the given name
    with the value provided; asserting that no further occurances
    happen. Note that this is _not_ the same as remove_header and then
    append, as two distinct operations (del followed by an append) are
    not atomic in a threaded environment. Returns the previous header
    value for the provided name, if any.   Clearly one should not use
    this function with ``set-cookie`` or other names that may have more
    than one occurance in the headers.
    """
    name = name.lower()
    i = 0
    result = None
    while i < len(headers):
        if headers[i][0].lower() == name:
            assert not result, "two values for the header '%s' found" % name
            result = headers[i][1]
            headers[i] = (name, value)
        i += 1
    if not result:
        headers.append((name, value))
    return result


############################################################
## Deprecated methods
############################################################

def error_body_response(error_code, message, __warn=True):
    """
    Returns a standard HTML response page for an HTTP error.
    **Note:** Deprecated
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_body_response is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 2)
    return '''\
<html>
  <head>
    <title>%(error_code)s</title>
  </head>
  <body>
  <h1>%(error_code)s</h1>
  %(message)s
  </body>
</html>''' % {
        'error_code': error_code,
        'message': message,
        }


def error_response(environ, error_code, message,
                   debug_message=None, __warn=True):
    """
    Returns the status, headers, and body of an error response.

    Use like:

    .. code-block:: python

        status, headers, body = wsgilib.error_response(
            '301 Moved Permanently', 'Moved to <a href="%s">%s</a>'
            % (url, url))
        start_response(status, headers)
        return [body]

    **Note:** Deprecated
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_response is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 2)
    if debug_message and environ.get('paste.config', {}).get('debug'):
        message += '\n\n<!-- %s -->' % debug_message
    body = error_body_response(error_code, message, __warn=False)
    headers = [('content-type', 'text/html'),
               ('content-length', str(len(body)))]
    return error_code, headers, body

def error_response_app(error_code, message, debug_message=None,
                       __warn=True):
    """
    An application that emits the given error response.

    **Note:** Deprecated
    """
    if __warn:
        warnings.warn(
            'wsgilib.error_response_app is deprecated; use the '
            'wsgi_application method on an HTTPException object '
            'instead', DeprecationWarning, 2)
    def application(environ, start_response):
        status, headers, body = error_response(
            environ, error_code, message,
            debug_message=debug_message, __warn=False)
        start_response(status, headers)
        return [body]
    return application
