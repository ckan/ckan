import sys
from ._compat import http_cookies

# Some versions of Python 2.7 and later won't need this encoding bug fix:
_cookie_encodes_correctly = http_cookies.SimpleCookie().value_encode(';') == (';', '"\\073"')

# Cookie pickling bug is fixed in Python 2.7.9 and Python 3.4.3+
# http://bugs.python.org/issue22775
cookie_pickles_properly = (
    (sys.version_info[:2] == (2, 7) and sys.version_info >= (2, 7, 9)) or
    sys.version_info >= (3, 4, 3)
)

# Add support for the SameSite attribute (obsolete when PY37 is unsupported).
http_cookies.Morsel._reserved.setdefault('samesite', 'SameSite')


# Adapted from Django.http.cookies and always enabled the bad_cookies
# behaviour to cope with any invalid cookie key while keeping around
# the session.
class SimpleCookie(http_cookies.SimpleCookie):
    if not cookie_pickles_properly:
        def __setitem__(self, key, value):
            # Apply the fix from http://bugs.python.org/issue22775 where
            # it's not fixed in Python itself
            if isinstance(value, http_cookies.Morsel):
                # allow assignment of constructed Morsels (e.g. for pickling)
                dict.__setitem__(self, key, value)
            else:
                super(SimpleCookie, self).__setitem__(key, value)

    if not _cookie_encodes_correctly:
        def value_encode(self, val):
            # Some browsers do not support quoted-string from RFC 2109,
            # including some versions of Safari and Internet Explorer.
            # These browsers split on ';', and some versions of Safari
            # are known to split on ', '. Therefore, we encode ';' and ','

            # SimpleCookie already does the hard work of encoding and decoding.
            # It uses octal sequences like '\\012' for newline etc.
            # and non-ASCII chars. We just make use of this mechanism, to
            # avoid introducing two encoding schemes which would be confusing
            # and especially awkward for javascript.

            # NB, contrary to Python docs, value_encode returns a tuple containing
            # (real val, encoded_val)
            val, encoded = super(SimpleCookie, self).value_encode(val)

            encoded = encoded.replace(";", "\\073").replace(",", "\\054")
            # If encoded now contains any quoted chars, we need double quotes
            # around the whole string.
            if "\\" in encoded and not encoded.startswith('"'):
                encoded = '"' + encoded + '"'

            return val, encoded

    def load(self, rawdata):
        self.bad_cookies = set()
        super(SimpleCookie, self).load(rawdata)
        for key in self.bad_cookies:
            del self[key]

    # override private __set() method:
    # (needed for using our Morsel, and for laxness with CookieError
    def _BaseCookie__set(self, key, real_value, coded_value):
        try:
            super(SimpleCookie, self)._BaseCookie__set(key, real_value, coded_value)
        except http_cookies.CookieError:
            if not hasattr(self, 'bad_cookies'):
                self.bad_cookies = set()
            self.bad_cookies.add(key)
            dict.__setitem__(self, key, http_cookies.Morsel())
