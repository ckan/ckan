# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php

"""
Creates a human-readable identifier, using numbers and digits,
avoiding ambiguous numbers and letters.  hash_identifier can be used
to create compact representations that are unique for a certain string
(or concatenation of strings)
"""

try:
    from hashlib import md5
except ImportError:
    from md5 import md5

good_characters = "23456789abcdefghjkmnpqrtuvwxyz"

base = len(good_characters)

def lazy_result(return_type, dummy_initial=None):
    """Decorator to allow for on-demand evaluation (limited scope of use!)"""
    if not issubclass(return_type, basestring):
        raise NotImplementedError

    class _lazy_class(return_type):
        """lazified access to value of %s type""" % return_type.__name__
        def __new__(self, *args, **kwargs):
            return super(_lazy_class, self).__new__(self, dummy_initial)
        def __init__(self, *args, **kwargs):
            self._args = args
            self._kwargs = kwargs
            self._active = Ellipsis
        def __call__(self, **kwargs):
            if self._active is Ellipsis:
                # explicit caller can possibly override keyword arguments
                kwargs.update(self._kwargs)
                self._active = self._generator(*self._args, **kwargs)
            return self._active
    _lazy_class.__name__ = "lazy_%s" % return_type.__name__

    # not everything implemented (and will never be 100%)
    _lazy_class.__str__ = lambda self: str(self())
    _lazy_class.__repr__ = lambda self: repr(self())
    _lazy_class.__cmp__ = lambda self, other: cmp(self(), other)
    _lazy_class.__getslice__ = lambda self, **kws: slice(self(), **kws)

    def _generating_lazy_class(generator):
        _lazy_class._generator = staticmethod(generator)
        return _lazy_class

    return _generating_lazy_class

def make_identifier(number):
    """
    Encodes a number as an identifier.
    """
    if not isinstance(number, (int, long)):
        raise ValueError(
            "You can only make identifiers out of integers (not %r)"
            % number)
    if number < 0:
        raise ValueError(
            "You cannot make identifiers out of negative numbers: %r"
            % number)
    result = []
    while number:
        next = number % base
        result.append(good_characters[next])
        # Note, this depends on integer rounding of results:
        number = number / base
    return ''.join(result)

@lazy_result(str)
def hash_identifier(s, length, pad=True, hasher=md5, prefix='',
                    group=None, upper=False):
    """
    Hashes the string (with the given hashing module), then turns that
    hash into an identifier of the given length (using modulo to
    reduce the length of the identifier).  If ``pad`` is False, then
    the minimum-length identifier will be used; otherwise the
    identifier will be padded with 0's as necessary.

    ``prefix`` will be added last, and does not count towards the
    target length.  ``group`` will group the characters with ``-`` in
    the given lengths, and also does not count towards the target
    length.  E.g., ``group=4`` will cause a identifier like
    ``a5f3-hgk3-asdf``.  Grouping occurs before the prefix.
    """
    if not callable(hasher):
        # Accept sha/md5 modules as well as callables
        hasher = hasher.new
    if length > 26 and hasher is md5:
        raise ValueError, (
            "md5 cannot create hashes longer than 26 characters in "
            "length (you gave %s)" % length)
    if isinstance(s, unicode):
        s = s.encode('utf-8')
    h = hasher(str(s))
    bin_hash = h.digest()
    modulo = base ** length
    number = 0
    for c in list(bin_hash):
        number = (number * 256 + ord(c)) % modulo
    ident = make_identifier(number)
    if pad:
        ident = good_characters[0]*(length-len(ident)) + ident
    if group:
        parts = []
        while ident:
            parts.insert(0, ident[-group:])
            ident = ident[:-group]
        ident = '-'.join(parts)
    if upper:
        ident = ident.upper()
    return prefix + ident

# doctest tests:
__test__ = {
    'make_identifier': """
    >>> make_identifier(0)
    ''
    >>> make_identifier(1000)
    'c53'
    >>> make_identifier(-100)
    Traceback (most recent call last):
        ...
    ValueError: You cannot make identifiers out of negative numbers: -100
    >>> make_identifier('test')
    Traceback (most recent call last):
        ...
    ValueError: You can only make identifiers out of integers (not 'test')
    >>> make_identifier(1000000000000)
    'c53x9rqh3'
    """,
    'hash_identifier': """
    >>> hash_identifier(0, 5)
    'cy2dr'
    >>> hash_identifier(0, 10)
    'cy2dr6rg46'
    >>> hash_identifier('this is a test of a long string', 5)
    'awatu'
    >>> hash_identifier(0, 26)
    'cy2dr6rg46cx8t4w2f3nfexzk4'
    >>> hash_identifier(0, 30)
    Traceback (most recent call last):
        ...
    ValueError: md5 cannot create hashes longer than 26 characters in length (you gave 30)
    >>> hash_identifier(0, 10, group=4)
    'cy-2dr6-rg46'
    >>> hash_identifier(0, 10, group=4, upper=True, prefix='M-')
    'M-CY-2DR6-RG46'
    """}

if __name__ == '__main__':
    import doctest
    doctest.testmod()

