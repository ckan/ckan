"""passlib.utils -- helpers for writing password hashes"""
#=============================================================================
# imports
#=============================================================================
from passlib.utils.compat import PYPY, JYTHON
# core
from base64 import b64encode, b64decode
from codecs import lookup as _lookup_codec
from functools import update_wrapper
import logging; log = logging.getLogger(__name__)
import math
import os
import sys
import random
if JYTHON: # pragma: no cover -- runtime detection
    # Jython 2.5.2 lacks stringprep module -
    # see http://bugs.jython.org/issue1758320
    try:
        import stringprep
    except ImportError:
        stringprep = None
        _stringprep_missing_reason = "not present under Jython"
else:
    import stringprep
import time
if stringprep:
    import unicodedata
from warnings import warn
# site
# pkg
from passlib.exc import ExpectedStringError
from passlib.utils.compat import add_doc, b, bytes, join_bytes, join_byte_values, \
                                 join_byte_elems, exc_err, irange, imap, PY3, u, \
                                 join_unicode, unicode, byte_elem_value, PY_MIN_32, next_method_attr
# local
__all__ = [
    # constants
    'PYPY',
    'JYTHON',
    'sys_bits',
    'unix_crypt_schemes',
    'rounds_cost_values',

    # decorators
    "classproperty",
##    "deprecated_function",
##    "relocated_function",
##    "memoized_class_property",

    # unicode helpers
    'consteq',
    'saslprep',

    # bytes helpers
    "xor_bytes",
    "render_bytes",

    # encoding helpers
    'is_same_codec',
    'is_ascii_safe',
    'to_bytes',
    'to_unicode',
    'to_native_str',

    # base64 helpers
    "BASE64_CHARS", "HASH64_CHARS", "BCRYPT_CHARS", "AB64_CHARS",
    "Base64Engine", "h64", "h64big",
    "ab64_encode", "ab64_decode",

    # host OS
    'has_crypt',
    'test_crypt',
    'safe_crypt',
    'tick',

    # randomness
    'rng',
    'getrandbytes',
    'getrandstr',
    'generate_password',

    # object type / interface tests
    'is_crypt_handler',
    'is_crypt_context',
    'has_rounds_info',
    'has_salt_info',
]

#=============================================================================
# constants
#=============================================================================

# bitsize of system architecture (32 or 64)
sys_bits = int(math.log(sys.maxsize if PY3 else sys.maxint, 2) + 1.5)

# list of hashes algs supported by crypt() on at least one OS.
unix_crypt_schemes = [
    "sha512_crypt", "sha256_crypt",
    "sha1_crypt", "bcrypt",
    "md5_crypt",
    # "bsd_nthash",
    "bsdi_crypt", "des_crypt",
    ]

# list of rounds_cost constants
rounds_cost_values = [ "linear", "log2" ]

# legacy import, will be removed in 1.8
from passlib.exc import MissingBackendError

# internal helpers
_BEMPTY = b('')
_UEMPTY = u("")
_USPACE = u(" ")

# maximum password size which passlib will allow; see exc.PasswordSizeError
MAX_PASSWORD_SIZE = int(os.environ.get("PASSLIB_MAX_PASSWORD_SIZE") or 4096)

#=============================================================================
# decorators and meta helpers
#=============================================================================
class classproperty(object):
    """Function decorator which acts like a combination of classmethod+property (limited to read-only properties)"""

    def __init__(self, func):
        self.im_func = func

    def __get__(self, obj, cls):
        return self.im_func(cls)

    @property
    def __func__(self):
        """py3 compatible alias"""
        return self.im_func

def deprecated_function(msg=None, deprecated=None, removed=None, updoc=True,
                        replacement=None, _is_method=False):
    """decorator to deprecate a function.

    :arg msg: optional msg, default chosen if omitted
    :kwd deprecated: version when function was first deprecated
    :kwd removed: version when function will be removed
    :kwd replacement: alternate name / instructions for replacing this function.
    :kwd updoc: add notice to docstring (default ``True``)
    """
    if msg is None:
        if _is_method:
            msg = "the method %(mod)s.%(klass)s.%(name)s() is deprecated"
        else:
            msg = "the function %(mod)s.%(name)s() is deprecated"
        if deprecated:
            msg += " as of Passlib %(deprecated)s"
        if removed:
            msg += ", and will be removed in Passlib %(removed)s"
        if replacement:
            msg += ", use %s instead" % replacement
        msg += "."
    def build(func):
        opts = dict(
            mod=func.__module__,
            name=func.__name__,
            deprecated=deprecated,
            removed=removed,
            )
        if _is_method:
            def wrapper(*args, **kwds):
                tmp = opts.copy()
                klass = args[0].__class__
                tmp.update(klass=klass.__name__, mod=klass.__module__)
                warn(msg % tmp, DeprecationWarning, stacklevel=2)
                return func(*args, **kwds)
        else:
            text = msg % opts
            def wrapper(*args, **kwds):
                warn(text, DeprecationWarning, stacklevel=2)
                return func(*args, **kwds)
        update_wrapper(wrapper, func)
        if updoc and (deprecated or removed) and \
                   wrapper.__doc__ and ".. deprecated::" not in wrapper.__doc__:
            txt = deprecated or ''
            if removed or replacement:
                txt += "\n    "
                if removed:
                    txt += "and will be removed in version %s" % (removed,)
                if replacement:
                    if removed:
                        txt += ", "
                    txt += "use %s instead" % replacement
                txt += "."
            if not wrapper.__doc__.strip(" ").endswith("\n"):
                wrapper.__doc__ += "\n"
            wrapper.__doc__ += "\n.. deprecated:: %s\n" % (txt,)
        return wrapper
    return build

def deprecated_method(msg=None, deprecated=None, removed=None, updoc=True,
                      replacement=None):
    """decorator to deprecate a method.

    :arg msg: optional msg, default chosen if omitted
    :kwd deprecated: version when method was first deprecated
    :kwd removed: version when method will be removed
    :kwd replacement: alternate name / instructions for replacing this method.
    :kwd updoc: add notice to docstring (default ``True``)
    """
    return deprecated_function(msg, deprecated, removed, updoc, replacement,
                               _is_method=True)

class memoized_property(object):
    """decorator which invokes method once, then replaces attr with result"""
    def __init__(self, func):
        self.im_func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        func = self.im_func
        value = func(obj)
        setattr(obj, func.__name__, value)
        return value

    @property
    def __func__(self):
        """py3 alias"""
        return self.im_func

# works but not used
##class memoized_class_property(object):
##    """function decorator which calls function as classmethod,
##    and replaces itself with result for current and all future invocations.
##    """
##    def __init__(self, func):
##        self.im_func = func
##
##    def __get__(self, obj, cls):
##        func = self.im_func
##        value = func(cls)
##        setattr(cls, func.__name__, value)
##        return value
##
##    @property
##    def __func__(self):
##        "py3 compatible alias"

#=============================================================================
# unicode helpers
#=============================================================================

def consteq(left, right):
    """Check two strings/bytes for equality.
    This is functionally equivalent to ``left == right``,
    but attempts to take constant time relative to the size of the righthand input.

    The purpose of this function is to help prevent timing attacks
    during digest comparisons: the standard ``==`` operator aborts
    after the first mismatched character, causing its runtime to be
    proportional to the longest prefix shared by the two inputs.
    If an attacker is able to predict and control one of the two
    inputs, repeated queries can be leveraged to reveal information about
    the content of the second argument. To minimize this risk, :func:`!consteq`
    is designed to take ``THETA(len(right))`` time, regardless
    of the contents of the two strings.
    It is recommended that the attacker-controlled input
    be passed in as the left-hand value.

    .. warning::

        This function is *not* perfect. Various VM-dependant issues
        (e.g. the VM's integer object instantiation algorithm, internal unicode representation, etc),
        may still cause the function's run time to be affected by the inputs,
        though in a less predictable manner.
        *To minimize such risks, this function should not be passed* :class:`unicode`
        *inputs that might contain non-* ``ASCII`` *characters*.

    .. versionadded:: 1.6
    """
    # NOTE:
    # resources & discussions considered in the design of this function:
    #   hmac timing attack --
    #       http://rdist.root.org/2009/05/28/timing-attack-in-google-keyczar-library/
    #   python developer discussion surrounding similar function --
    #       http://bugs.python.org/issue15061
    #       http://bugs.python.org/issue14955

    # validate types
    if isinstance(left, unicode):
        if not isinstance(right, unicode):
            raise TypeError("inputs must be both unicode or both bytes")
        is_py3_bytes = False
    elif isinstance(left, bytes):
        if not isinstance(right, bytes):
            raise TypeError("inputs must be both unicode or both bytes")
        is_py3_bytes = PY3
    else:
        raise TypeError("inputs must be both unicode or both bytes")

    # do size comparison.
    # NOTE: the double-if construction below is done deliberately, to ensure
    # the same number of operations (including branches) is performed regardless
    # of whether left & right are the same size.
    same_size = (len(left) == len(right))
    if same_size:
        # if sizes are the same, setup loop to perform actual check of contents.
        tmp = left
        result = 0
    if not same_size:
        # if sizes aren't the same, set 'result' so equality will fail regardless
        # of contents. then, to ensure we do exactly 'len(right)' iterations
        # of the loop, just compare 'right' against itself.
        tmp = right
        result = 1

    # run constant-time string comparision
    # TODO: use izip instead (but first verify it's faster than zip for this case)
    if is_py3_bytes:
        for l,r in zip(tmp, right):
            result |= l ^ r
    else:
        for l,r in zip(tmp, right):
            result |= ord(l) ^ ord(r)
    return result == 0

def splitcomma(source, sep=","):
    """split comma-separated string into list of elements,
    stripping whitespace.
    """
    source = source.strip()
    if source.endswith(sep):
        source = source[:-1]
    if not source:
        return []
    return [ elem.strip() for elem in source.split(sep) ]

def saslprep(source, param="value"):
    """Normalizes unicode strings using SASLPrep stringprep profile.

    The SASLPrep profile is defined in :rfc:`4013`.
    It provides a uniform scheme for normalizing unicode usernames
    and passwords before performing byte-value sensitive operations
    such as hashing. Among other things, it normalizes diacritic
    representations, removes non-printing characters, and forbids
    invalid characters such as ``\\n``. Properly internationalized
    applications should run user passwords through this function
    before hashing.

    :arg source:
        unicode string to normalize & validate

    :param param:
        Optional noun used to refer to identify source parameter in error messages
        (Defaults to the string ``"value"``). This is mainly useful to make the caller's error
        messages make more sense.

    :raises ValueError:
        if any characters forbidden by the SASLPrep profile are encountered.

    :returns:
        normalized unicode string

    .. note::

        This function is not available under Jython,
        as the Jython stdlib is missing the :mod:`!stringprep` module
        (`Jython issue 1758320 <http://bugs.jython.org/issue1758320>`_).

    .. versionadded:: 1.6
    """
    # saslprep - http://tools.ietf.org/html/rfc4013
    # stringprep - http://tools.ietf.org/html/rfc3454
    #              http://docs.python.org/library/stringprep.html

    # validate type
    if not isinstance(source, unicode):
        raise TypeError("input must be unicode string, not %s" %
                        (type(source),))

    # mapping stage
    #   - map non-ascii spaces to U+0020 (stringprep C.1.2)
    #   - strip 'commonly mapped to nothing' chars (stringprep B.1)
    in_table_c12 = stringprep.in_table_c12
    in_table_b1 = stringprep.in_table_b1
    data = join_unicode(
        _USPACE if in_table_c12(c) else c
        for c in source
        if not in_table_b1(c)
        )

    # normalize to KC form
    data = unicodedata.normalize('NFKC', data)
    if not data:
        return _UEMPTY

    # check for invalid bi-directional strings.
    # stringprep requires the following:
    #   - chars in C.8 must be prohibited.
    #   - if any R/AL chars in string:
    #       - no L chars allowed in string
    #       - first and last must be R/AL chars
    # this checks if start/end are R/AL chars. if so, prohibited loop
    # will forbid all L chars. if not, prohibited loop will forbid all
    # R/AL chars instead. in both cases, prohibited loop takes care of C.8.
    is_ral_char = stringprep.in_table_d1
    if is_ral_char(data[0]):
        if not is_ral_char(data[-1]):
            raise ValueError("malformed bidi sequence in " + param)
        # forbid L chars within R/AL sequence.
        is_forbidden_bidi_char = stringprep.in_table_d2
    else:
        # forbid R/AL chars if start not setup correctly; L chars allowed.
        is_forbidden_bidi_char = is_ral_char

    # check for prohibited output - stringprep tables A.1, B.1, C.1.2, C.2 - C.9
    in_table_a1 = stringprep.in_table_a1
    in_table_c21_c22 = stringprep.in_table_c21_c22
    in_table_c3 = stringprep.in_table_c3
    in_table_c4 = stringprep.in_table_c4
    in_table_c5 = stringprep.in_table_c5
    in_table_c6 = stringprep.in_table_c6
    in_table_c7 = stringprep.in_table_c7
    in_table_c8 = stringprep.in_table_c8
    in_table_c9 = stringprep.in_table_c9
    for c in data:
        # check for chars mapping stage should have removed
        assert not in_table_b1(c), "failed to strip B.1 in mapping stage"
        assert not in_table_c12(c), "failed to replace C.1.2 in mapping stage"

        # check for forbidden chars
        if in_table_a1(c):
            raise ValueError("unassigned code points forbidden in " + param)
        if in_table_c21_c22(c):
            raise ValueError("control characters forbidden in " + param)
        if in_table_c3(c):
            raise ValueError("private use characters forbidden in " + param)
        if in_table_c4(c):
            raise ValueError("non-char code points forbidden in " + param)
        if in_table_c5(c):
            raise ValueError("surrogate codes forbidden in " + param)
        if in_table_c6(c):
            raise ValueError("non-plaintext chars forbidden in " + param)
        if in_table_c7(c):
            # XXX: should these have been caught by normalize?
            # if so, should change this to an assert
            raise ValueError("non-canonical chars forbidden in " + param)
        if in_table_c8(c):
            raise ValueError("display-modifying / deprecated chars "
                             "forbidden in" + param)
        if in_table_c9(c):
            raise ValueError("tagged characters forbidden in " + param)

        # do bidi constraint check chosen by bidi init, above
        if is_forbidden_bidi_char(c):
            raise ValueError("forbidden bidi character in " + param)

    return data

# replace saslprep() with stub when stringprep is missing
if stringprep is None: # pragma: no cover -- runtime detection
    def saslprep(source, param="value"):
        """stub for saslprep()"""
        raise NotImplementedError("saslprep() support requires the 'stringprep' "
                            "module, which is " + _stringprep_missing_reason)

#=============================================================================
# bytes helpers
#=============================================================================
def render_bytes(source, *args):
    """Peform ``%`` formating using bytes in a uniform manner across Python 2/3.

    This function is motivated by the fact that
    :class:`bytes` instances do not support ``%`` or ``{}`` formatting under Python 3.
    This function is an attempt to provide a replacement:
    it converts everything to unicode (decoding bytes instances as ``latin-1``),
    performs the required formatting, then encodes the result to ``latin-1``.

    Calling ``render_bytes(source, *args)`` should function roughly the same as
    ``source % args`` under Python 2.
    """
    if isinstance(source, bytes):
        source = source.decode("latin-1")
    result = source % tuple(arg.decode("latin-1") if isinstance(arg, bytes)
                            else arg for arg in args)
    return result.encode("latin-1")

if PY_MIN_32:
    def bytes_to_int(value):
        return int.from_bytes(value, 'big')
    def int_to_bytes(value, count):
        return value.to_bytes(count, 'big')
else:
    # XXX: can any of these be sped up?
    from binascii import hexlify, unhexlify
    def bytes_to_int(value):
        return int(hexlify(value),16)
    if PY3:
        # grr, why did py3 have to break % for bytes?
        def int_to_bytes(value, count):
            return unhexlify((('%%0%dx' % (count<<1)) % value).encode("ascii"))
    else:
        def int_to_bytes(value, count):
            return unhexlify(('%%0%dx' % (count<<1)) % value)

add_doc(bytes_to_int, "decode byte string as single big-endian integer")
add_doc(int_to_bytes, "encode integer as single big-endian byte string")

def xor_bytes(left, right):
    """Perform bitwise-xor of two byte strings (must be same size)"""
    return int_to_bytes(bytes_to_int(left) ^ bytes_to_int(right), len(left))

def repeat_string(source, size):
    """repeat or truncate <source> string, so it has length <size>"""
    cur = len(source)
    if size > cur:
        mult = (size+cur-1)//cur
        return (source*mult)[:size]
    else:
        return source[:size]

_BNULL = b("\x00")
_UNULL = u("\x00")

def right_pad_string(source, size, pad=None):
    """right-pad or truncate <source> string, so it has length <size>"""
    cur = len(source)
    if size > cur:
        if pad is None:
            pad = _UNULL if isinstance(source, unicode) else _BNULL
        return source+pad*(size-cur)
    else:
        return source[:size]

#=============================================================================
# encoding helpers
#=============================================================================
_ASCII_TEST_BYTES = b("\x00\n aA:#!\x7f")
_ASCII_TEST_UNICODE = _ASCII_TEST_BYTES.decode("ascii")

def is_ascii_codec(codec):
    """Test if codec is compatible with 7-bit ascii (e.g. latin-1, utf-8; but not utf-16)"""
    return _ASCII_TEST_UNICODE.encode(codec) == _ASCII_TEST_BYTES

def is_same_codec(left, right):
    """Check if two codec names are aliases for same codec"""
    if left == right:
        return True
    if not (left and right):
        return False
    return _lookup_codec(left).name == _lookup_codec(right).name

_B80 = b('\x80')[0]
_U80 = u('\x80')
def is_ascii_safe(source):
    """Check if string (bytes or unicode) contains only 7-bit ascii"""
    r = _B80 if isinstance(source, bytes) else _U80
    return all(c < r for c in source)

def to_bytes(source, encoding="utf-8", param="value", source_encoding=None):
    """Helper to normalize input to bytes.

    :arg source:
        Source bytes/unicode to process.

    :arg encoding:
        Target encoding (defaults to ``"utf-8"``).

    :param param:
        Optional name of variable/noun to reference when raising errors

    :param source_encoding:
        If this is specified, and the source is bytes,
        the source will be transcoded from *source_encoding* to *encoding*
        (via unicode).

    :raises TypeError: if source is not unicode or bytes.

    :returns:
        * unicode strings will be encoded using *encoding*, and returned.
        * if *source_encoding* is not specified, byte strings will be
          returned unchanged.
        * if *source_encoding* is specified, byte strings will be transcoded
          to *encoding*.
    """
    assert encoding
    if isinstance(source, bytes):
        if source_encoding and not is_same_codec(source_encoding, encoding):
            return source.decode(source_encoding).encode(encoding)
        else:
            return source
    elif isinstance(source, unicode):
        return source.encode(encoding)
    else:
        raise ExpectedStringError(source, param)

def to_unicode(source, encoding="utf-8", param="value"):
    """Helper to normalize input to unicode.

    :arg source:
        source bytes/unicode to process.

    :arg encoding:
        encoding to use when decoding bytes instances.

    :param param:
        optional name of variable/noun to reference when raising errors.

    :raises TypeError: if source is not unicode or bytes.

    :returns:
        * returns unicode strings unchanged.
        * returns bytes strings decoded using *encoding*
    """
    assert encoding
    if isinstance(source, unicode):
        return source
    elif isinstance(source, bytes):
        return source.decode(encoding)
    else:
        raise ExpectedStringError(source, param)

if PY3:
    def to_native_str(source, encoding="utf-8", param="value"):
        if isinstance(source, bytes):
            return source.decode(encoding)
        elif isinstance(source, unicode):
            return source
        else:
            raise ExpectedStringError(source, param)
else:
    def to_native_str(source, encoding="utf-8", param="value"):
        if isinstance(source, bytes):
            return source
        elif isinstance(source, unicode):
            return source.encode(encoding)
        else:
            raise ExpectedStringError(source, param)

add_doc(to_native_str,
    """Take in unicode or bytes, return native string.

    Python 2: encodes unicode using specified encoding, leaves bytes alone.
    Python 3: leaves unicode alone, decodes bytes using specified encoding.

    :raises TypeError: if source is not unicode or bytes.

    :arg source:
        source unicode or bytes string.

    :arg encoding:
        encoding to use when encoding unicode or decoding bytes.
        this defaults to ``"utf-8"``.

    :param param:
        optional name of variable/noun to reference when raising errors.

    :returns: :class:`str` instance
    """)

@deprecated_function(deprecated="1.6", removed="1.7")
def to_hash_str(source, encoding="ascii"): # pragma: no cover -- deprecated & unused
    """deprecated, use to_native_str() instead"""
    return to_native_str(source, encoding, param="hash")

#=============================================================================
# base64-variant encoding
#=============================================================================

class Base64Engine(object):
    """Provides routines for encoding/decoding base64 data using
    arbitrary character mappings, selectable endianness, etc.

    :arg charmap:
        A string of 64 unique characters,
        which will be used to encode successive 6-bit chunks of data.
        A character's position within the string should correspond
        to its 6-bit value.

    :param big:
        Whether the encoding should be big-endian (default False).

    .. note::
        This class does not currently handle base64's padding characters
        in any way what so ever.

    Raw Bytes <-> Encoded Bytes
    ===========================
    The following methods convert between raw bytes,
    and strings encoded using the engine's specific base64 variant:

    .. automethod:: encode_bytes
    .. automethod:: decode_bytes
    .. automethod:: encode_transposed_bytes
    .. automethod:: decode_transposed_bytes

    ..
        .. automethod:: check_repair_unused
        .. automethod:: repair_unused

    Integers <-> Encoded Bytes
    ==========================
    The following methods allow encoding and decoding
    unsigned integers to and from the engine's specific base64 variant.
    Endianess is determined by the engine's ``big`` constructor keyword.

    .. automethod:: encode_int6
    .. automethod:: decode_int6

    .. automethod:: encode_int12
    .. automethod:: decode_int12

    .. automethod:: encode_int24
    .. automethod:: decode_int24

    .. automethod:: encode_int64
    .. automethod:: decode_int64

    Informational Attributes
    ========================
    .. attribute:: charmap

        unicode string containing list of characters used in encoding;
        position in string matches 6bit value of character.

    .. attribute:: bytemap

        bytes version of :attr:`charmap`

    .. attribute:: big

        boolean flag indicating this using big-endian encoding.
    """

    #===================================================================
    # instance attrs
    #===================================================================
    # public config
    bytemap = None # charmap as bytes
    big = None # little or big endian

    # filled in by init based on charmap.
    # (byte elem: single byte under py2, 8bit int under py3)
    _encode64 = None # maps 6bit value -> byte elem
    _decode64 = None # maps byte elem -> 6bit value

    # helpers filled in by init based on endianness
    _encode_bytes = None # throws IndexError if bad value (shouldn't happen)
    _decode_bytes = None # throws KeyError if bad char.

    #===================================================================
    # init
    #===================================================================
    def __init__(self, charmap, big=False):
        # validate charmap, generate encode64/decode64 helper functions.
        if isinstance(charmap, unicode):
            charmap = charmap.encode("latin-1")
        elif not isinstance(charmap, bytes):
            raise ExpectedStringError(charmap, "charmap")
        if len(charmap) != 64:
            raise ValueError("charmap must be 64 characters in length")
        if len(set(charmap)) != 64:
            raise ValueError("charmap must not contain duplicate characters")
        self.bytemap = charmap
        self._encode64 = charmap.__getitem__
        lookup = dict((value, idx) for idx, value in enumerate(charmap))
        self._decode64 = lookup.__getitem__

        # validate big, set appropriate helper functions.
        self.big = big
        if big:
            self._encode_bytes = self._encode_bytes_big
            self._decode_bytes = self._decode_bytes_big
        else:
            self._encode_bytes = self._encode_bytes_little
            self._decode_bytes = self._decode_bytes_little

        # TODO: support padding character
        ##if padding is not None:
        ##    if isinstance(padding, unicode):
        ##        padding = padding.encode("latin-1")
        ##    elif not isinstance(padding, bytes):
        ##        raise TypeError("padding char must be unicode or bytes")
        ##    if len(padding) != 1:
        ##        raise ValueError("padding must be single character")
        ##self.padding = padding

    @property
    def charmap(self):
        """charmap as unicode"""
        return self.bytemap.decode("latin-1")

    #===================================================================
    # encoding byte strings
    #===================================================================
    def encode_bytes(self, source):
        """encode bytes to base64 string.

        :arg source: byte string to encode.
        :returns: byte string containing encoded data.
        """
        if not isinstance(source, bytes):
            raise TypeError("source must be bytes, not %s" % (type(source),))
        chunks, tail = divmod(len(source), 3)
        if PY3:
            next_value = iter(source).__next__
        else:
            next_value = (ord(elem) for elem in source).next
        gen = self._encode_bytes(next_value, chunks, tail)
        out = join_byte_elems(imap(self._encode64, gen))
        ##if tail:
        ##    padding = self.padding
        ##    if padding:
        ##        out += padding * (3-tail)
        return out

    def _encode_bytes_little(self, next_value, chunks, tail):
        """helper used by encode_bytes() to handle little-endian encoding"""
        #
        # output bit layout:
        #
        # first byte:   v1 543210
        #
        # second byte:  v1 ....76
        #              +v2 3210..
        #
        # third byte:   v2 ..7654
        #              +v3 10....
        #
        # fourth byte:  v3 765432
        #
        idx = 0
        while idx < chunks:
            v1 = next_value()
            v2 = next_value()
            v3 = next_value()
            yield v1 & 0x3f
            yield ((v2 & 0x0f)<<2)|(v1>>6)
            yield ((v3 & 0x03)<<4)|(v2>>4)
            yield v3>>2
            idx += 1
        if tail:
            v1 = next_value()
            if tail == 1:
                # note: 4 msb of last byte are padding
                yield v1 & 0x3f
                yield v1>>6
            else:
                assert tail == 2
                # note: 2 msb of last byte are padding
                v2 = next_value()
                yield v1 & 0x3f
                yield ((v2 & 0x0f)<<2)|(v1>>6)
                yield v2>>4

    def _encode_bytes_big(self, next_value, chunks, tail):
        """helper used by encode_bytes() to handle big-endian encoding"""
        #
        # output bit layout:
        #
        # first byte:   v1 765432
        #
        # second byte:  v1 10....
        #              +v2 ..7654
        #
        # third byte:   v2 3210..
        #              +v3 ....76
        #
        # fourth byte:  v3 543210
        #
        idx = 0
        while idx < chunks:
            v1 = next_value()
            v2 = next_value()
            v3 = next_value()
            yield v1>>2
            yield ((v1&0x03)<<4)|(v2>>4)
            yield ((v2&0x0f)<<2)|(v3>>6)
            yield v3 & 0x3f
            idx += 1
        if tail:
            v1 = next_value()
            if tail == 1:
                # note: 4 lsb of last byte are padding
                yield v1>>2
                yield (v1&0x03)<<4
            else:
                assert tail == 2
                # note: 2 lsb of last byte are padding
                v2 = next_value()
                yield v1>>2
                yield ((v1&0x03)<<4)|(v2>>4)
                yield ((v2&0x0f)<<2)

    #===================================================================
    # decoding byte strings
    #===================================================================

    def decode_bytes(self, source):
        """decode bytes from base64 string.

        :arg source: byte string to decode.
        :returns: byte string containing decoded data.
        """
        if not isinstance(source, bytes):
            raise TypeError("source must be bytes, not %s" % (type(source),))
        ##padding = self.padding
        ##if padding:
        ##    # TODO: add padding size check?
        ##    source = source.rstrip(padding)
        chunks, tail = divmod(len(source), 4)
        if tail == 1:
            # only 6 bits left, can't encode a whole byte!
            raise ValueError("input string length cannot be == 1 mod 4")
        next_value = getattr(imap(self._decode64, source), next_method_attr)
        try:
            return join_byte_values(self._decode_bytes(next_value, chunks, tail))
        except KeyError:
            err = exc_err()
            raise ValueError("invalid character: %r" % (err.args[0],))

    def _decode_bytes_little(self, next_value, chunks, tail):
        """helper used by decode_bytes() to handle little-endian encoding"""
        #
        # input bit layout:
        #
        # first byte:   v1 ..543210
        #              +v2 10......
        #
        # second byte:  v2 ....5432
        #              +v3 3210....
        #
        # third byte:   v3 ......54
        #              +v4 543210..
        #
        idx = 0
        while idx < chunks:
            v1 = next_value()
            v2 = next_value()
            v3 = next_value()
            v4 = next_value()
            yield v1 | ((v2 & 0x3) << 6)
            yield (v2>>2) | ((v3 & 0xF) << 4)
            yield (v3>>4) | (v4<<2)
            idx += 1
        if tail:
            # tail is 2 or 3
            v1 = next_value()
            v2 = next_value()
            yield v1 | ((v2 & 0x3) << 6)
            # NOTE: if tail == 2, 4 msb of v2 are ignored (should be 0)
            if tail == 3:
                # NOTE: 2 msb of v3 are ignored (should be 0)
                v3 = next_value()
                yield (v2>>2) | ((v3 & 0xF) << 4)

    def _decode_bytes_big(self, next_value, chunks, tail):
        """helper used by decode_bytes() to handle big-endian encoding"""
        #
        # input bit layout:
        #
        # first byte:   v1 543210..
        #              +v2 ......54
        #
        # second byte:  v2 3210....
        #              +v3 ....5432
        #
        # third byte:   v3 10......
        #              +v4 ..543210
        #
        idx = 0
        while idx < chunks:
            v1 = next_value()
            v2 = next_value()
            v3 = next_value()
            v4 = next_value()
            yield (v1<<2) | (v2>>4)
            yield ((v2&0xF)<<4) | (v3>>2)
            yield ((v3&0x3)<<6) | v4
            idx += 1
        if tail:
            # tail is 2 or 3
            v1 = next_value()
            v2 = next_value()
            yield (v1<<2) | (v2>>4)
            # NOTE: if tail == 2, 4 lsb of v2 are ignored (should be 0)
            if tail == 3:
                # NOTE: 2 lsb of v3 are ignored (should be 0)
                v3 = next_value()
                yield ((v2&0xF)<<4) | (v3>>2)

    #===================================================================
    # encode/decode helpers
    #===================================================================

    # padmap2/3 - dict mapping last char of string ->
    # equivalent char with no padding bits set.

    def __make_padset(self, bits):
        """helper to generate set of valid last chars & bytes"""
        pset = set(c for i,c in enumerate(self.bytemap) if not i & bits)
        pset.update(c for i,c in enumerate(self.charmap) if not i & bits)
        return frozenset(pset)

    @memoized_property
    def _padinfo2(self):
        """mask to clear padding bits, and valid last bytes (for strings 2 % 4)"""
        # 4 bits of last char unused (lsb for big, msb for little)
        bits = 15 if self.big else (15<<2)
        return ~bits, self.__make_padset(bits)

    @memoized_property
    def _padinfo3(self):
        """mask to clear padding bits, and valid last bytes (for strings 3 % 4)"""
        # 2 bits of last char unused (lsb for big, msb for little)
        bits = 3 if self.big else (3<<4)
        return ~bits, self.__make_padset(bits)

    def check_repair_unused(self, source):
        """helper to detect & clear invalid unused bits in last character.

        :arg source:
            encoded data (as ascii bytes or unicode).

        :returns:
            `(True, result)` if the string was repaired,
            `(False, source)` if the string was ok as-is.
        """
        # figure out how many padding bits there are in last char.
        tail = len(source) & 3
        if tail == 2:
            mask, padset = self._padinfo2
        elif tail == 3:
            mask, padset = self._padinfo3
        elif not tail:
            return False, source
        else:
            raise ValueError("source length must != 1 mod 4")

        # check if last char is ok (padset contains bytes & unicode versions)
        last = source[-1]
        if last in padset:
            return False, source

        # we have dirty bits - repair the string by decoding last char,
        # clearing the padding bits via <mask>, and encoding new char.
        if isinstance(source, unicode):
            cm = self.charmap
            last = cm[cm.index(last) & mask]
            assert last in padset, "failed to generate valid padding char"
        else:
            # NOTE: this assumes ascii-compat encoding, and that
            # all chars used by encoding are 7-bit ascii.
            last = self._encode64(self._decode64(last) & mask)
            assert last in padset, "failed to generate valid padding char"
            if PY3:
                last = bytes([last])
        return True, source[:-1] + last

    def repair_unused(self, source):
        return self.check_repair_unused(source)[1]

    ##def transcode(self, source, other):
    ##    return ''.join(
    ##        other.charmap[self.charmap.index(char)]
    ##        for char in source
    ##    )

    ##def random_encoded_bytes(self, size, random=None, unicode=False):
    ##    "return random encoded string of given size"
    ##    data = getrandstr(random or rng,
    ##                      self.charmap if unicode else self.bytemap, size)
    ##    return self.repair_unused(data)

    #===================================================================
    # transposed encoding/decoding
    #===================================================================
    def encode_transposed_bytes(self, source, offsets):
        """encode byte string, first transposing source using offset list"""
        if not isinstance(source, bytes):
            raise TypeError("source must be bytes, not %s" % (type(source),))
        tmp = join_byte_elems(source[off] for off in offsets)
        return self.encode_bytes(tmp)

    def decode_transposed_bytes(self, source, offsets):
        """decode byte string, then reverse transposition described by offset list"""
        # NOTE: if transposition does not use all bytes of source,
        # the original can't be recovered... and join_byte_elems() will throw
        # an error because 1+ values in <buf> will be None.
        tmp = self.decode_bytes(source)
        buf = [None] * len(offsets)
        for off, char in zip(offsets, tmp):
            buf[off] = char
        return join_byte_elems(buf)

    #===================================================================
    # integer decoding helpers - mainly used by des_crypt family
    #===================================================================
    def _decode_int(self, source, bits):
        """decode base64 string -> integer

        :arg source: base64 string to decode.
        :arg bits: number of bits in resulting integer.

        :raises ValueError:
            * if the string contains invalid base64 characters.
            * if the string is not long enough - it must be at least
              ``int(ceil(bits/6))`` in length.

        :returns:
            a integer in the range ``0 <= n < 2**bits``
        """
        if not isinstance(source, bytes):
            raise TypeError("source must be bytes, not %s" % (type(source),))
        big = self.big
        pad = -bits % 6
        chars = (bits+pad)/6
        if len(source) != chars:
            raise ValueError("source must be %d chars" % (chars,))
        decode = self._decode64
        out = 0
        try:
            for c in source if big else reversed(source):
                out = (out<<6) + decode(c)
        except KeyError:
            raise ValueError("invalid character in string: %r" % (c,))
        if pad:
            # strip padding bits
            if big:
                out >>= pad
            else:
                out &= (1<<bits)-1
        return out

    #---------------------------------------------------------------
    # optimized versions for common integer sizes
    #---------------------------------------------------------------

    def decode_int6(self, source):
        """decode single character -> 6 bit integer"""
        if not isinstance(source, bytes):
            raise TypeError("source must be bytes, not %s" % (type(source),))
        if len(source) != 1:
            raise ValueError("source must be exactly 1 byte")
        if PY3:
            # convert to 8bit int before doing lookup
            source = source[0]
        try:
            return self._decode64(source)
        except KeyError:
            raise ValueError("invalid character")

    def decode_int12(self, source):
        """decodes 2 char string -> 12-bit integer"""
        if not isinstance(source, bytes):
            raise TypeError("source must be bytes, not %s" % (type(source),))
        if len(source) != 2:
            raise ValueError("source must be exactly 2 bytes")
        decode = self._decode64
        try:
            if self.big:
                return decode(source[1]) + (decode(source[0])<<6)
            else:
                return decode(source[0]) + (decode(source[1])<<6)
        except KeyError:
            raise ValueError("invalid character")

    def decode_int24(self, source):
        """decodes 4 char string -> 24-bit integer"""
        if not isinstance(source, bytes):
            raise TypeError("source must be bytes, not %s" % (type(source),))
        if len(source) != 4:
            raise ValueError("source must be exactly 4 bytes")
        decode = self._decode64
        try:
            if self.big:
                return decode(source[3]) + (decode(source[2])<<6)+ \
                       (decode(source[1])<<12) + (decode(source[0])<<18)
            else:
                return decode(source[0]) + (decode(source[1])<<6)+ \
                       (decode(source[2])<<12) + (decode(source[3])<<18)
        except KeyError:
            raise ValueError("invalid character")

    def decode_int64(self, source):
        """decode 11 char base64 string -> 64-bit integer

        this format is used primarily by des-crypt & variants to encode
        the DES output value used as a checksum.
        """
        return self._decode_int(source, 64)

    #===================================================================
    # integer encoding helpers - mainly used by des_crypt family
    #===================================================================
    def _encode_int(self, value, bits):
        """encode integer into base64 format

        :arg value: non-negative integer to encode
        :arg bits: number of bits to encode

        :returns:
            a string of length ``int(ceil(bits/6.0))``.
        """
        assert value >= 0, "caller did not sanitize input"
        pad = -bits % 6
        bits += pad
        if self.big:
            itr = irange(bits-6, -6, -6)
            # shift to add lsb padding.
            value <<= pad
        else:
            itr = irange(0, bits, 6)
            # padding is msb, so no change needed.
        return join_byte_elems(imap(self._encode64,
                                ((value>>off) & 0x3f for off in itr)))

    #---------------------------------------------------------------
    # optimized versions for common integer sizes
    #---------------------------------------------------------------

    def encode_int6(self, value):
        """encodes 6-bit integer -> single hash64 character"""
        if value < 0 or value > 63:
            raise ValueError("value out of range")
        if PY3:
            return self.bytemap[value:value+1]
        else:
            return self._encode64(value)

    def encode_int12(self, value):
        """encodes 12-bit integer -> 2 char string"""
        if value < 0 or value > 0xFFF:
            raise ValueError("value out of range")
        raw = [value & 0x3f, (value>>6) & 0x3f]
        if self.big:
            raw = reversed(raw)
        return join_byte_elems(imap(self._encode64, raw))

    def encode_int24(self, value):
        """encodes 24-bit integer -> 4 char string"""
        if value < 0 or value > 0xFFFFFF:
            raise ValueError("value out of range")
        raw = [value & 0x3f, (value>>6) & 0x3f,
               (value>>12) & 0x3f, (value>>18) & 0x3f]
        if self.big:
            raw = reversed(raw)
        return join_byte_elems(imap(self._encode64, raw))

    def encode_int64(self, value):
        """encode 64-bit integer -> 11 char hash64 string

        this format is used primarily by des-crypt & variants to encode
        the DES output value used as a checksum.
        """
        if value < 0 or value > 0xffffffffffffffff:
            raise ValueError("value out of range")
        return self._encode_int(value, 64)

    #===================================================================
    # eof
    #===================================================================

class LazyBase64Engine(Base64Engine):
    """Base64Engine which delays initialization until it's accessed"""
    _lazy_opts = None

    def __init__(self, *args, **kwds):
        self._lazy_opts = (args, kwds)

    def _lazy_init(self):
        args, kwds = self._lazy_opts
        super(LazyBase64Engine, self).__init__(*args, **kwds)
        del self._lazy_opts
        self.__class__ = Base64Engine

    def __getattribute__(self, attr):
        if not attr.startswith("_"):
            self._lazy_init()
        return object.__getattribute__(self, attr)

# common charmaps
BASE64_CHARS = u("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/")
AB64_CHARS =   u("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789./")
HASH64_CHARS = u("./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
BCRYPT_CHARS = u("./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")

# common variants
h64 = LazyBase64Engine(HASH64_CHARS)
h64big = LazyBase64Engine(HASH64_CHARS, big=True)
bcrypt64 = LazyBase64Engine(BCRYPT_CHARS, big=True)

#=============================================================================
# adapted-base64 encoding
#=============================================================================
_A64_ALTCHARS = b("./")
_A64_STRIP = b("=\n")
_A64_PAD1 = b("=")
_A64_PAD2 = b("==")

def ab64_encode(data):
    """encode using variant of base64

    the output of this function is identical to stdlib's b64_encode,
    except that it uses ``.`` instead of ``+``,
    and omits trailing padding ``=`` and whitepsace.

    it is primarily used by Passlib's custom pbkdf2 hashes.
    """
    return b64encode(data, _A64_ALTCHARS).strip(_A64_STRIP)

def ab64_decode(data):
    """decode using variant of base64

    the input of this function is identical to stdlib's b64_decode,
    except that it uses ``.`` instead of ``+``,
    and should not include trailing padding ``=`` or whitespace.

    it is primarily used by Passlib's custom pbkdf2 hashes.
    """
    off = len(data) & 3
    if off == 0:
        return b64decode(data, _A64_ALTCHARS)
    elif off == 2:
        return b64decode(data + _A64_PAD2, _A64_ALTCHARS)
    elif off == 3:
        return b64decode(data + _A64_PAD1, _A64_ALTCHARS)
    else: # off == 1
        raise ValueError("invalid base64 input")

#=============================================================================
# host OS helpers
#=============================================================================

try:
    from crypt import crypt as _crypt
except ImportError: # pragma: no cover
    _crypt = None
    has_crypt = False
    def safe_crypt(secret, hash):
        return None
else:
    has_crypt = True
    _NULL = '\x00'

    # some crypt() variants will return various constant strings when
    # an invalid/unrecognized config string is passed in; instead of
    # returning NULL / None. examples include ":", ":0", "*0", etc.
    # safe_crypt() returns None for any string starting with one of the
    # chars in this string...
    _invalid_prefixes = u("*:!")

    if PY3:
        def safe_crypt(secret, hash):
            if isinstance(secret, bytes):
                # Python 3's crypt() only accepts unicode, which is then
                # encoding using utf-8 before passing to the C-level crypt().
                # so we have to decode the secret.
                orig = secret
                try:
                    secret = secret.decode("utf-8")
                except UnicodeDecodeError:
                    return None
                assert secret.encode("utf-8") == orig, \
                            "utf-8 spec says this can't happen!"
            if _NULL in secret:
                raise ValueError("null character in secret")
            if isinstance(hash, bytes):
                hash = hash.decode("ascii")
            result = _crypt(secret, hash)
            if not result or result[0] in _invalid_prefixes:
                return None
            return result
    else:
        def safe_crypt(secret, hash):
            if isinstance(secret, unicode):
                secret = secret.encode("utf-8")
            if _NULL in secret:
                raise ValueError("null character in secret")
            if isinstance(hash, unicode):
                hash = hash.encode("ascii")
            result = _crypt(secret, hash)
            if not result:
                return None
            result = result.decode("ascii")
            if result[0] in _invalid_prefixes:
                return None
            return result

add_doc(safe_crypt, """Wrapper around stdlib's crypt.

    This is a wrapper around stdlib's :func:`!crypt.crypt`, which attempts
    to provide uniform behavior across Python 2 and 3.

    :arg secret:
        password, as bytes or unicode (unicode will be encoded as ``utf-8``).

    :arg hash:
        hash or config string, as ascii bytes or unicode.

    :returns:
        resulting hash as ascii unicode; or ``None`` if the password
        couldn't be hashed due to one of the issues:

        * :func:`crypt()` not available on platform.

        * Under Python 3, if *secret* is specified as bytes,
          it must be use ``utf-8`` or it can't be passed
          to :func:`crypt()`.

        * Some OSes will return ``None`` if they don't recognize
          the algorithm being used (though most will simply fall
          back to des-crypt).

        * Some OSes will return an error string if the input config
          is recognized but malformed; current code converts these to ``None``
          as well.
    """)

def test_crypt(secret, hash):
    """check if :func:`crypt.crypt` supports specific hash
    :arg secret: password to test
    :arg hash: known hash of password to use as reference
    :returns: True or False
    """
    assert secret and hash
    return safe_crypt(secret, hash) == hash

# pick best timer function to expose as "tick" - lifted from timeit module.
if sys.platform == "win32":
    # On Windows, the best timer is time.clock()
    from time import clock as tick
else:
    # On most other platforms the best timer is time.time()
    from time import time as tick

#=============================================================================
# randomness
#=============================================================================

#------------------------------------------------------------------------
# setup rng for generating salts
#------------------------------------------------------------------------

# NOTE:
# generating salts (e.g. h64_gensalt, below) doesn't require cryptographically
# strong randomness. it just requires enough range of possible outputs
# that making a rainbow table is too costly. so it should be ok to
# fall back on python's builtin mersenne twister prng, as long as it's seeded each time
# this module is imported, using a couple of minor entropy sources.

try:
    os.urandom(1)
    has_urandom = True
except NotImplementedError: # pragma: no cover
    has_urandom = False

def genseed(value=None):
    """generate prng seed value from system resources"""
    from hashlib import sha512
    text = u("%s %s %s %s %.15f %.15f %s") % (
        # if caller specified a seed value, mix it in
        value,

        # if caller's seed value was an RNG, mix in bits from its state
        value.getrandbits(1<<15) if hasattr(value, "getrandbits") else None,

        # add current process id
        # NOTE: not available in some environments, e.g. GAE
        os.getpid() if hasattr(os, "getpid") else None,

        # id of a freshly created object.
        # (at least 1 byte of which should be hard to predict)
        id(object()),

        # the current time, to whatever precision os uses
        time.time(),
        time.clock(),

        # if urandom available, might as well mix some bytes in.
        os.urandom(32).decode("latin-1") if has_urandom else 0,
        )
    # hash it all up and return it as int/long
    return int(sha512(text.encode("utf-8")).hexdigest(), 16)

if has_urandom:
    rng = random.SystemRandom()
else: # pragma: no cover -- runtime detection
    # NOTE: to reseed use ``rng.seed(genseed(rng))``
    rng = random.Random(genseed())

#------------------------------------------------------------------------
# some rng helpers
#------------------------------------------------------------------------
def getrandbytes(rng, count):
    """return byte-string containing *count* number of randomly generated bytes, using specified rng"""
    # NOTE: would be nice if this was present in stdlib Random class

    ###just in case rng provides this...
    ##meth = getattr(rng, "getrandbytes", None)
    ##if meth:
    ##    return meth(count)

    if not count:
        return _BEMPTY
    def helper():
        # XXX: break into chunks for large number of bits?
        value = rng.getrandbits(count<<3)
        i = 0
        while i < count:
            yield value & 0xff
            value >>= 3
            i += 1
    return join_byte_values(helper())

def getrandstr(rng, charset, count):
    """return string containing *count* number of chars/bytes, whose elements are drawn from specified charset, using specified rng"""
    # NOTE: tests determined this is 4x faster than rng.sample(),
    # which is why that's not being used here.

    # check alphabet & count
    if count < 0:
        raise ValueError("count must be >= 0")
    letters = len(charset)
    if letters == 0:
        raise ValueError("alphabet must not be empty")
    if letters == 1:
        return charset * count

    # get random value, and write out to buffer
    def helper():
        # XXX: break into chunks for large number of letters?
        value = rng.randrange(0, letters**count)
        i = 0
        while i < count:
            yield charset[value % letters]
            value //= letters
            i += 1

    if isinstance(charset, unicode):
        return join_unicode(helper())
    else:
        return join_byte_elems(helper())

_52charset = '2346789ABCDEFGHJKMNPQRTUVWXYZabcdefghjkmnpqrstuvwxyz'

def generate_password(size=10, charset=_52charset):
    """generate random password using given length & charset

    :param size:
        size of password.

    :param charset:
        optional string specified set of characters to draw from.

        the default charset contains all normal alphanumeric characters,
        except for the characters ``1IiLl0OoS5``, which were omitted
        due to their visual similarity.

    :returns: :class:`!str` containing randomly generated password.

    .. note::

        Using the default character set, on a OS with :class:`!SystemRandom` support,
        this function should generate passwords with 5.7 bits of entropy per character.
    """
    return getrandstr(rng, charset, size)

#=============================================================================
# object type / interface tests
#=============================================================================
_handler_attrs = (
        "name",
        "setting_kwds", "context_kwds",
        "genconfig", "genhash",
        "verify", "encrypt", "identify",
        )

def is_crypt_handler(obj):
    """check if object follows the :ref:`password-hash-api`"""
    # XXX: change to use isinstance(obj, PasswordHash) under py26+?
    return all(hasattr(obj, name) for name in _handler_attrs)

_context_attrs = (
        "needs_update",
        "genconfig", "genhash",
        "verify", "encrypt", "identify",
        )

def is_crypt_context(obj):
    """check if object appears to be a :class:`~passlib.context.CryptContext` instance"""
    # XXX: change to use isinstance(obj, CryptContext)?
    return all(hasattr(obj, name) for name in _context_attrs)

##def has_many_backends(handler):
##    "check if handler provides multiple baceknds"
##    # NOTE: should also provide get_backend(), .has_backend(), and .backends attr
##    return hasattr(handler, "set_backend")

def has_rounds_info(handler):
    """check if handler provides the optional :ref:`rounds information <rounds-attributes>` attributes"""
    return ('rounds' in handler.setting_kwds and
            getattr(handler, "min_rounds", None) is not None)

def has_salt_info(handler):
    """check if handler provides the optional :ref:`salt information <salt-attributes>` attributes"""
    return ('salt' in handler.setting_kwds and
            getattr(handler, "min_salt_size", None) is not None)

##def has_raw_salt(handler):
##    "check if handler takes in encoded salt as unicode (False), or decoded salt as bytes (True)"
##    sc = getattr(handler, "salt_chars", None)
##    if sc is None:
##        return None
##    elif isinstance(sc, unicode):
##        return False
##    elif isinstance(sc, bytes):
##        return True
##    else:
##        raise TypeError("handler.salt_chars must be None/unicode/bytes")

#=============================================================================
# eof
#=============================================================================
