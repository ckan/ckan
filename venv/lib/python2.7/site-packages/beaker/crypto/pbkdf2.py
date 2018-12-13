"""
PBKDF2 Implementation adapted from django.utils.crypto.

This is used to generate the encryption key for enciphered sessions.
"""
from beaker._compat import bytes_, xrange_

import hmac
import struct
import hashlib
import binascii


def _bin_to_long(x):
    """Convert a binary string into a long integer"""
    return int(binascii.hexlify(x), 16)


def _long_to_bin(x, hex_format_string):
    """
    Convert a long integer into a binary string.
    hex_format_string is like "%020x" for padding 10 characters.
    """
    return binascii.unhexlify((hex_format_string % x).encode('ascii'))


if hasattr(hashlib, "pbkdf2_hmac"):
    def pbkdf2(password, salt, iterations, dklen=0, digest=None):
        """
        Implements PBKDF2 using the stdlib. This is used in Python 2.7.8+ and 3.4+.

        HMAC+SHA256 is used as the default pseudo random function.

        As of 2014, 100,000 iterations was the recommended default which took
        100ms on a 2.7Ghz Intel i7 with an optimized implementation. This is
        probably the bare minimum for security given 1000 iterations was
        recommended in 2001.
        """
        if digest is None:
            digest = hashlib.sha1
        if not dklen:
            dklen = None
        password = bytes_(password)
        salt = bytes_(salt)
        return hashlib.pbkdf2_hmac(
            digest().name, password, salt, iterations, dklen)
else:
    def pbkdf2(password, salt, iterations, dklen=0, digest=None):
        """
        Implements PBKDF2 as defined in RFC 2898, section 5.2

        HMAC+SHA256 is used as the default pseudo random function.

        As of 2014, 100,000 iterations was the recommended default which took
        100ms on a 2.7Ghz Intel i7 with an optimized implementation. This is
        probably the bare minimum for security given 1000 iterations was
        recommended in 2001. This code is very well optimized for CPython and
        is about five times slower than OpenSSL's implementation.
        """
        assert iterations > 0
        if not digest:
            digest = hashlib.sha1
        password = bytes_(password)
        salt = bytes_(salt)
        hlen = digest().digest_size
        if not dklen:
            dklen = hlen
        if dklen > (2 ** 32 - 1) * hlen:
            raise OverflowError('dklen too big')
        l = -(-dklen // hlen)
        r = dklen - (l - 1) * hlen

        hex_format_string = "%%0%ix" % (hlen * 2)

        inner, outer = digest(), digest()
        if len(password) > inner.block_size:
            password = digest(password).digest()
        password += b'\x00' * (inner.block_size - len(password))
        inner.update(password.translate(hmac.trans_36))
        outer.update(password.translate(hmac.trans_5C))

        def F(i):
            u = salt + struct.pack(b'>I', i)
            result = 0
            for j in xrange_(int(iterations)):
                dig1, dig2 = inner.copy(), outer.copy()
                dig1.update(u)
                dig2.update(dig1.digest())
                u = dig2.digest()
                result ^= _bin_to_long(u)
            return _long_to_bin(result, hex_format_string)

        T = [F(x) for x in xrange_(1, l)]
        return b''.join(T) + F(l)[:r]
