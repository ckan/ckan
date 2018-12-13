"""
helper implementing insecure and obsolete md4 algorithm.
used for NTHASH format, which is also insecure and broken,
since it's just md4(password)

implementated based on rfc at http://www.faqs.org/rfcs/rfc1320.html

"""

#=============================================================================
# imports
#=============================================================================
# core
from binascii import hexlify
import struct
from warnings import warn
# site
from passlib.utils.compat import b, bytes, bascii_to_str, irange, PY3
# local
__all__ = [ "md4" ]
#=============================================================================
# utils
#=============================================================================
def F(x,y,z):
    return (x&y) | ((~x) & z)

def G(x,y,z):
    return (x&y) | (x&z) | (y&z)

##def H(x,y,z):
##    return x ^ y ^ z

MASK_32 = 2**32-1

#=============================================================================
# main class
#=============================================================================
class md4(object):
    """pep-247 compatible implementation of MD4 hash algorithm

    .. attribute:: digest_size

        size of md4 digest in bytes (16 bytes)

    .. method:: update

        update digest by appending additional content

    .. method:: copy

        create clone of digest object, including current state

    .. method:: digest

        return bytes representing md4 digest of current content

    .. method:: hexdigest

        return hexadecimal version of digest
    """
    # FIXME: make this follow hash object PEP better.
    # FIXME: this isn't threadsafe
    # XXX: should we monkeypatch ourselves into hashlib for general use? probably wouldn't be nice.

    name = "md4"
    digest_size = digestsize = 16

    _count = 0 # number of 64-byte blocks processed so far (not including _buf)
    _state = None # list of [a,b,c,d] 32 bit ints used as internal register
    _buf = None # data processed in 64 byte blocks, this holds leftover from last update

    def __init__(self, content=None):
        self._count = 0
        self._state = [0x67452301, 0xefcdab89, 0x98badcfe, 0x10325476]
        self._buf = b('')
        if content:
            self.update(content)

    # round 1 table - [abcd k s]
    _round1 = [
        [0,1,2,3, 0,3],
        [3,0,1,2, 1,7],
        [2,3,0,1, 2,11],
        [1,2,3,0, 3,19],

        [0,1,2,3, 4,3],
        [3,0,1,2, 5,7],
        [2,3,0,1, 6,11],
        [1,2,3,0, 7,19],

        [0,1,2,3, 8,3],
        [3,0,1,2, 9,7],
        [2,3,0,1, 10,11],
        [1,2,3,0, 11,19],

        [0,1,2,3, 12,3],
        [3,0,1,2, 13,7],
        [2,3,0,1, 14,11],
        [1,2,3,0, 15,19],
    ]

    # round 2 table - [abcd k s]
    _round2 = [
        [0,1,2,3, 0,3],
        [3,0,1,2, 4,5],
        [2,3,0,1, 8,9],
        [1,2,3,0, 12,13],

        [0,1,2,3, 1,3],
        [3,0,1,2, 5,5],
        [2,3,0,1, 9,9],
        [1,2,3,0, 13,13],

        [0,1,2,3, 2,3],
        [3,0,1,2, 6,5],
        [2,3,0,1, 10,9],
        [1,2,3,0, 14,13],

        [0,1,2,3, 3,3],
        [3,0,1,2, 7,5],
        [2,3,0,1, 11,9],
        [1,2,3,0, 15,13],
    ]

    # round 3 table - [abcd k s]
    _round3 = [
        [0,1,2,3, 0,3],
        [3,0,1,2, 8,9],
        [2,3,0,1, 4,11],
        [1,2,3,0, 12,15],

        [0,1,2,3, 2,3],
        [3,0,1,2, 10,9],
        [2,3,0,1, 6,11],
        [1,2,3,0, 14,15],

        [0,1,2,3, 1,3],
        [3,0,1,2, 9,9],
        [2,3,0,1, 5,11],
        [1,2,3,0, 13,15],

        [0,1,2,3, 3,3],
        [3,0,1,2, 11,9],
        [2,3,0,1, 7,11],
        [1,2,3,0, 15,15],
    ]

    def _process(self, block):
        """process 64 byte block"""
        # unpack block into 16 32-bit ints
        X = struct.unpack("<16I", block)

        # clone state
        orig = self._state
        state = list(orig)

        # round 1 - F function - (x&y)|(~x & z)
        for a,b,c,d,k,s in self._round1:
            t = (state[a] + F(state[b],state[c],state[d]) + X[k]) & MASK_32
            state[a] = ((t<<s) & MASK_32) + (t>>(32-s))

        # round 2 - G function
        for a,b,c,d,k,s in self._round2:
            t = (state[a] + G(state[b],state[c],state[d]) + X[k] + 0x5a827999) & MASK_32
            state[a] = ((t<<s) & MASK_32) + (t>>(32-s))

        # round 3 - H function - x ^ y ^ z
        for a,b,c,d,k,s in self._round3:
            t = (state[a] + (state[b] ^ state[c] ^ state[d]) + X[k] + 0x6ed9eba1) & MASK_32
            state[a] = ((t<<s) & MASK_32) + (t>>(32-s))

        # add back into original state
        for i in irange(4):
            orig[i] = (orig[i]+state[i]) & MASK_32

    def update(self, content):
        if not isinstance(content, bytes):
            raise TypeError("expected bytes")
        buf = self._buf
        if buf:
            content = buf + content
        idx = 0
        end = len(content)
        while True:
            next = idx + 64
            if next <= end:
                self._process(content[idx:next])
                self._count += 1
                idx = next
            else:
                self._buf = content[idx:]
                return

    def copy(self):
        other = _builtin_md4()
        other._count = self._count
        other._state = list(self._state)
        other._buf = self._buf
        return other

    def digest(self):
        # NOTE: backing up state so we can restore it after _process is called,
        #       in case object is updated again (this is only attr altered by this method)
        orig = list(self._state)

        # final block: buf + 0x80,
        # then 0x00 padding until congruent w/ 56 mod 64 bytes
        # then last 8 bytes = msg length in bits
        buf = self._buf
        msglen = self._count*512 + len(buf)*8
        block = buf + b('\x80') + b('\x00') * ((119-len(buf)) % 64) + \
            struct.pack("<2I", msglen & MASK_32, (msglen>>32) & MASK_32)
        if len(block) == 128:
            self._process(block[:64])
            self._process(block[64:])
        else:
            assert len(block) == 64
            self._process(block)

        # render digest & restore un-finalized state
        out = struct.pack("<4I", *self._state)
        self._state = orig
        return out

    def hexdigest(self):
        return bascii_to_str(hexlify(self.digest()))

    #===================================================================
    # eoc
    #===================================================================

# keep ref around for unittest, 'md4' usually replaced by ssl wrapper, below.
_builtin_md4 = md4

#=============================================================================
# check if hashlib provides accelarated md4
#=============================================================================
import hashlib
from passlib.utils import PYPY

def _has_native_md4(): # pragma: no cover -- runtime detection
    try:
        h = hashlib.new("md4")
    except ValueError:
        # not supported - ssl probably missing (e.g. ironpython)
        return False
    result = h.hexdigest()
    if result == '31d6cfe0d16ae931b73c59d7e0c089c0':
        return True
    if PYPY and result == '':
        # workaround for https://bugs.pypy.org/issue957, fixed in PyPy 1.8
        return False
    # anything else and we should alert user
    from passlib.exc import PasslibRuntimeWarning
    warn("native md4 support disabled, sanity check failed!", PasslibRuntimeWarning)
    return False

if _has_native_md4():
    # overwrite md4 class w/ hashlib wrapper
    def md4(content=None):
        """wrapper for hashlib.new('md4')"""
        return hashlib.new('md4', content or b(''))

#=============================================================================
# eof
#=============================================================================
