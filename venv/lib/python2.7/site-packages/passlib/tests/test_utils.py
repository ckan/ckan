"""tests for passlib.util"""
#=============================================================================
# imports
#=============================================================================
from __future__ import with_statement
# core
from binascii import hexlify, unhexlify
import sys
import random
import warnings
# site
# pkg
# module
from passlib.utils.compat import b, bytes, bascii_to_str, irange, PY2, PY3, u, \
                                 unicode, join_bytes, SUPPORTS_DIR_METHOD
from passlib.tests.utils import TestCase, catch_warnings

def hb(source):
    return unhexlify(b(source))

#=============================================================================
# byte funcs
#=============================================================================
class MiscTest(TestCase):
    """tests various parts of utils module"""

    # NOTE: could test xor_bytes(), but it's exercised well enough by pbkdf2 test

    def test_compat(self):
        """test compat's lazymodule"""
        from passlib.utils import compat
        # "<module 'passlib.utils.compat' from 'passlib/utils/compat.pyc'>"
        self.assertRegex(repr(compat),
                         r"^<module 'passlib.utils.compat' from '.*?'>$")

        # test synthentic dir()
        dir(compat)
        if SUPPORTS_DIR_METHOD:
            self.assertTrue('UnicodeIO' in dir(compat))
            self.assertTrue('irange' in dir(compat))

    def test_classproperty(self):
        from passlib.utils import classproperty

        class test(object):
            xvar = 1
            @classproperty
            def xprop(cls):
                return cls.xvar

        self.assertEqual(test.xprop, 1)
        prop = test.__dict__['xprop']
        self.assertIs(prop.im_func, prop.__func__)

    def test_deprecated_function(self):
        from passlib.utils import deprecated_function
        # NOTE: not comprehensive, just tests the basic behavior

        @deprecated_function(deprecated="1.6", removed="1.8")
        def test_func(*args):
            """test docstring"""
            return args

        self.assertTrue(".. deprecated::" in test_func.__doc__)

        with self.assertWarningList(dict(category=DeprecationWarning,
                message="the function passlib.tests.test_utils.test_func() "
                        "is deprecated as of Passlib 1.6, and will be "
                        "removed in Passlib 1.8."
                )):
            self.assertEqual(test_func(1,2), (1,2))

    def test_memoized_property(self):
        from passlib.utils import memoized_property

        class dummy(object):
            counter = 0

            @memoized_property
            def value(self):
                value = self.counter
                self.counter = value+1
                return value

        d = dummy()
        self.assertEqual(d.value, 0)
        self.assertEqual(d.value, 0)
        self.assertEqual(d.counter, 1)

        prop = dummy.value
        self.assertIs(prop.im_func, prop.__func__)

    def test_getrandbytes(self):
        """test getrandbytes()"""
        from passlib.utils import getrandbytes, rng
        def f(*a,**k):
            return getrandbytes(rng, *a, **k)
        self.assertEqual(len(f(0)), 0)
        a = f(10)
        b = f(10)
        self.assertIsInstance(a, bytes)
        self.assertEqual(len(a), 10)
        self.assertEqual(len(b), 10)
        self.assertNotEqual(a, b)

    def test_getrandstr(self):
        """test getrandstr()"""
        from passlib.utils import getrandstr, rng
        def f(*a,**k):
            return getrandstr(rng, *a, **k)

        # count 0
        self.assertEqual(f('abc',0), '')

        # count <0
        self.assertRaises(ValueError, f, 'abc', -1)

        # letters 0
        self.assertRaises(ValueError, f, '', 0)

        # letters 1
        self.assertEqual(f('a',5), 'aaaaa')

        # letters
        x = f(u('abc'), 16)
        y = f(u('abc'), 16)
        self.assertIsInstance(x, unicode)
        self.assertNotEqual(x,y)
        self.assertEqual(sorted(set(x)), [u('a'),u('b'),u('c')])

        # bytes
        x = f(b('abc'), 16)
        y = f(b('abc'), 16)
        self.assertIsInstance(x, bytes)
        self.assertNotEqual(x,y)
        # NOTE: decoding this due to py3 bytes
        self.assertEqual(sorted(set(x.decode("ascii"))), [u('a'),u('b'),u('c')])

        # generate_password
        from passlib.utils import generate_password
        self.assertEqual(len(generate_password(15)), 15)

    def test_is_crypt_context(self):
        """test is_crypt_context()"""
        from passlib.utils import is_crypt_context
        from passlib.context import CryptContext
        cc = CryptContext(["des_crypt"])
        self.assertTrue(is_crypt_context(cc))
        self.assertFalse(not is_crypt_context(cc))

    def test_genseed(self):
        """test genseed()"""
        import random
        from passlib.utils import genseed
        rng = random.Random(genseed())
        a = rng.randint(0, 100000)

        rng = random.Random(genseed())
        b = rng.randint(0, 100000)

        self.assertNotEqual(a,b)

        rng.seed(genseed(rng))

    def test_crypt(self):
        """test crypt.crypt() wrappers"""
        from passlib.utils import has_crypt, safe_crypt, test_crypt

        # test everything is disabled
        if not has_crypt:
            self.assertEqual(safe_crypt("test", "aa"), None)
            self.assertFalse(test_crypt("test", "aaqPiZY5xR5l."))
            raise self.skipTest("crypt.crypt() not available")

        # XXX: this assumes *every* crypt() implementation supports des_crypt.
        #      if this fails for some platform, this test will need modifying.

        # test return type
        self.assertIsInstance(safe_crypt(u("test"), u("aa")), unicode)

        # test ascii password
        h1 = u('aaqPiZY5xR5l.')
        self.assertEqual(safe_crypt(u('test'), u('aa')), h1)
        self.assertEqual(safe_crypt(b('test'), b('aa')), h1)

        # test utf-8 / unicode password
        h2 = u('aahWwbrUsKZk.')
        self.assertEqual(safe_crypt(u('test\u1234'), 'aa'), h2)
        self.assertEqual(safe_crypt(b('test\xe1\x88\xb4'), 'aa'), h2)

        # test latin-1 password
        hash = safe_crypt(b('test\xff'), 'aa')
        if PY3: # py3 supports utf-8 bytes only.
            self.assertEqual(hash, None)
        else: # but py2 is fine.
            self.assertEqual(hash, u('aaOx.5nbTU/.M'))

        # test rejects null chars in password
        self.assertRaises(ValueError, safe_crypt, '\x00', 'aa')

        # check test_crypt()
        h1x = h1[:-1] + 'x'
        self.assertTrue(test_crypt("test", h1))
        self.assertFalse(test_crypt("test", h1x))

        # check crypt returning variant error indicators
        # some platforms return None on errors, others empty string,
        # The BSDs in some cases return ":"
        import passlib.utils as mod
        orig = mod._crypt
        try:
            fake = None
            mod._crypt = lambda secret, hash: fake
            for fake in [None, "", ":", ":0", "*0"]:
                self.assertEqual(safe_crypt("test", "aa"), None)
                self.assertFalse(test_crypt("test", h1))
            fake = 'xxx'
            self.assertEqual(safe_crypt("test", "aa"), "xxx")
        finally:
            mod._crypt = orig

    def test_consteq(self):
        """test consteq()"""
        # NOTE: this test is kind of over the top, but that's only because
        # this is used for the critical task of comparing hashes for equality.
        from passlib.utils import consteq

        # ensure error raises for wrong types
        self.assertRaises(TypeError, consteq, u(''), b(''))
        self.assertRaises(TypeError, consteq, u(''), 1)
        self.assertRaises(TypeError, consteq, u(''), None)

        self.assertRaises(TypeError, consteq, b(''), u(''))
        self.assertRaises(TypeError, consteq, b(''), 1)
        self.assertRaises(TypeError, consteq, b(''), None)

        self.assertRaises(TypeError, consteq, None, u(''))
        self.assertRaises(TypeError, consteq, None, b(''))
        self.assertRaises(TypeError, consteq, 1, u(''))
        self.assertRaises(TypeError, consteq, 1, b(''))

        # check equal inputs compare correctly
        for value in [
                u("a"),
                u("abc"),
                u("\xff\xa2\x12\x00")*10,
            ]:
            self.assertTrue(consteq(value, value), "value %r:" % (value,))
            value = value.encode("latin-1")
            self.assertTrue(consteq(value, value), "value %r:" % (value,))

        # check non-equal inputs compare correctly
        for l,r in [
                # check same-size comparisons with differing contents fail.
                (u("a"),         u("c")),
                (u("abcabc"),    u("zbaabc")),
                (u("abcabc"),    u("abzabc")),
                (u("abcabc"),    u("abcabz")),
                ((u("\xff\xa2\x12\x00")*10)[:-1] + u("\x01"),
                    u("\xff\xa2\x12\x00")*10),

                # check different-size comparisons fail.
                (u(""),       u("a")),
                (u("abc"),    u("abcdef")),
                (u("abc"),    u("defabc")),
                (u("qwertyuiopasdfghjklzxcvbnm"), u("abc")),
            ]:
            self.assertFalse(consteq(l, r), "values %r %r:" % (l,r))
            self.assertFalse(consteq(r, l), "values %r %r:" % (r,l))
            l = l.encode("latin-1")
            r = r.encode("latin-1")
            self.assertFalse(consteq(l, r), "values %r %r:" % (l,r))
            self.assertFalse(consteq(r, l), "values %r %r:" % (r,l))

        # TODO: add some tests to ensure we take THETA(strlen) time.
        # this might be hard to do reproducably.
        # NOTE: below code was used to generate stats for analysis
        ##from math import log as logb
        ##import timeit
        ##multipliers = [ 1<<s for s in irange(9)]
        ##correct =   u"abcdefgh"*(1<<4)
        ##incorrect = u"abcdxfgh"
        ##print
        ##first = True
        ##for run in irange(1):
        ##    times = []
        ##    chars = []
        ##    for m in multipliers:
        ##        supplied = incorrect * m
        ##        def test():
        ##            self.assertFalse(consteq(supplied,correct))
        ##            ##self.assertFalse(supplied == correct)
        ##        times.append(timeit.timeit(test, number=100000))
        ##        chars.append(len(supplied))
        ##    # output for wolfram alpha
        ##    print ", ".join("{%r, %r}" % (c,round(t,4)) for c,t in zip(chars,times))
        ##    def scale(c):
        ##        return logb(c,2)
        ##    print ", ".join("{%r, %r}" % (scale(c),round(t,4)) for c,t in zip(chars,times))
        ##    # output for spreadsheet
        ##    ##if first:
        ##    ##    print "na, " + ", ".join(str(c) for c in chars)
        ##    ##    first = False
        ##    ##print ", ".join(str(c) for c in [run] + times)

    def test_saslprep(self):
        """test saslprep() unicode normalizer"""
        self.require_stringprep()
        from passlib.utils import saslprep as sp

        # invalid types
        self.assertRaises(TypeError, sp, None)
        self.assertRaises(TypeError, sp, 1)
        self.assertRaises(TypeError, sp, b(''))

        # empty strings
        self.assertEqual(sp(u('')), u(''))
        self.assertEqual(sp(u('\u00AD')), u(''))

        # verify B.1 chars are stripped,
        self.assertEqual(sp(u("$\u00AD$\u200D$")), u("$$$"))

        # verify C.1.2 chars are replaced with space
        self.assertEqual(sp(u("$ $\u00A0$\u3000$")), u("$ $ $ $"))

        # verify normalization to KC
        self.assertEqual(sp(u("a\u0300")), u("\u00E0"))
        self.assertEqual(sp(u("\u00E0")), u("\u00E0"))

        # verify various forbidden characters
            # control chars
        self.assertRaises(ValueError, sp, u("\u0000"))
        self.assertRaises(ValueError, sp, u("\u007F"))
        self.assertRaises(ValueError, sp, u("\u180E"))
        self.assertRaises(ValueError, sp, u("\uFFF9"))
            # private use
        self.assertRaises(ValueError, sp, u("\uE000"))
            # non-characters
        self.assertRaises(ValueError, sp, u("\uFDD0"))
            # surrogates
        self.assertRaises(ValueError, sp, u("\uD800"))
            # non-plaintext chars
        self.assertRaises(ValueError, sp, u("\uFFFD"))
            # non-canon
        self.assertRaises(ValueError, sp, u("\u2FF0"))
            # change display properties
        self.assertRaises(ValueError, sp, u("\u200E"))
        self.assertRaises(ValueError, sp, u("\u206F"))
            # unassigned code points (as of unicode 3.2)
        self.assertRaises(ValueError, sp, u("\u0900"))
        self.assertRaises(ValueError, sp, u("\uFFF8"))
            # tagging characters
        self.assertRaises(ValueError, sp, u("\U000e0001"))

        # verify bidi behavior
            # if starts with R/AL -- must end with R/AL
        self.assertRaises(ValueError, sp, u("\u0627\u0031"))
        self.assertEqual(sp(u("\u0627")), u("\u0627"))
        self.assertEqual(sp(u("\u0627\u0628")), u("\u0627\u0628"))
        self.assertEqual(sp(u("\u0627\u0031\u0628")), u("\u0627\u0031\u0628"))
            # if starts with R/AL --  cannot contain L
        self.assertRaises(ValueError, sp, u("\u0627\u0041\u0628"))
            # if doesn't start with R/AL -- can contain R/AL, but L & EN allowed
        self.assertRaises(ValueError, sp, u("x\u0627z"))
        self.assertEqual(sp(u("x\u0041z")), u("x\u0041z"))

        #------------------------------------------------------
        # examples pulled from external sources, to be thorough
        #------------------------------------------------------

        # rfc 4031 section 3 examples
        self.assertEqual(sp(u("I\u00ADX")), u("IX")) # strip SHY
        self.assertEqual(sp(u("user")), u("user")) # unchanged
        self.assertEqual(sp(u("USER")), u("USER")) # case preserved
        self.assertEqual(sp(u("\u00AA")), u("a")) # normalize to KC form
        self.assertEqual(sp(u("\u2168")), u("IX")) # normalize to KC form
        self.assertRaises(ValueError, sp, u("\u0007")) # forbid control chars
        self.assertRaises(ValueError, sp, u("\u0627\u0031")) # invalid bidi

        # rfc 3454 section 6 examples
            # starts with RAL char, must end with RAL char
        self.assertRaises(ValueError, sp, u("\u0627\u0031"))
        self.assertEqual(sp(u("\u0627\u0031\u0628")), u("\u0627\u0031\u0628"))

    def test_splitcomma(self):
        from passlib.utils import splitcomma
        self.assertEqual(splitcomma(""), [])
        self.assertEqual(splitcomma(","), [])
        self.assertEqual(splitcomma("a"), ['a'])
        self.assertEqual(splitcomma(" a , "), ['a'])
        self.assertEqual(splitcomma(" a , b"), ['a', 'b'])
        self.assertEqual(splitcomma(" a, b, "), ['a', 'b'])

#=============================================================================
# byte/unicode helpers
#=============================================================================
class CodecTest(TestCase):
    """tests bytes/unicode helpers in passlib.utils"""

    def test_bytes(self):
        """test b() helper, bytes and native str type"""
        if PY3:
            import builtins
            self.assertIs(bytes, builtins.bytes)
        else:
            import __builtin__ as builtins
            self.assertIs(bytes, builtins.str)

        self.assertIsInstance(b(''), bytes)
        self.assertIsInstance(b('\x00\xff'), bytes)
        if PY3:
            self.assertEqual(b('\x00\xff').decode("latin-1"), "\x00\xff")
        else:
            self.assertEqual(b('\x00\xff'), "\x00\xff")

    def test_to_bytes(self):
        """test to_bytes()"""
        from passlib.utils import to_bytes

        # check unicode inputs
        self.assertEqual(to_bytes(u('abc')),                  b('abc'))
        self.assertEqual(to_bytes(u('\x00\xff')),             b('\x00\xc3\xbf'))

        # check unicode w/ encodings
        self.assertEqual(to_bytes(u('\x00\xff'), 'latin-1'),  b('\x00\xff'))
        self.assertRaises(ValueError, to_bytes, u('\x00\xff'), 'ascii')

        # check bytes inputs
        self.assertEqual(to_bytes(b('abc')),                b('abc'))
        self.assertEqual(to_bytes(b('\x00\xff')),           b('\x00\xff'))
        self.assertEqual(to_bytes(b('\x00\xc3\xbf')),       b('\x00\xc3\xbf'))

        # check byte inputs ignores enocding
        self.assertEqual(to_bytes(b('\x00\xc3\xbf'), "latin-1"),
                                                            b('\x00\xc3\xbf'))

        # check bytes transcoding
        self.assertEqual(to_bytes(b('\x00\xc3\xbf'), "latin-1", "", "utf-8"),
                                                            b('\x00\xff'))

        # check other
        self.assertRaises(AssertionError, to_bytes, 'abc', None)
        self.assertRaises(TypeError, to_bytes, None)

    def test_to_unicode(self):
        """test to_unicode()"""
        from passlib.utils import to_unicode

        # check unicode inputs
        self.assertEqual(to_unicode(u('abc')),                u('abc'))
        self.assertEqual(to_unicode(u('\x00\xff')),           u('\x00\xff'))

        # check unicode input ignores encoding
        self.assertEqual(to_unicode(u('\x00\xff'), "ascii"),  u('\x00\xff'))

        # check bytes input
        self.assertEqual(to_unicode(b('abc')),              u('abc'))
        self.assertEqual(to_unicode(b('\x00\xc3\xbf')),     u('\x00\xff'))
        self.assertEqual(to_unicode(b('\x00\xff'), 'latin-1'),
                                                            u('\x00\xff'))
        self.assertRaises(ValueError, to_unicode, b('\x00\xff'))

        # check other
        self.assertRaises(AssertionError, to_unicode, 'abc', None)
        self.assertRaises(TypeError, to_unicode, None)

    def test_to_native_str(self):
        """test to_native_str()"""
        from passlib.utils import to_native_str

        # test plain ascii
        self.assertEqual(to_native_str(u('abc'), 'ascii'), 'abc')
        self.assertEqual(to_native_str(b('abc'), 'ascii'), 'abc')

        # test invalid ascii
        if PY3:
            self.assertEqual(to_native_str(u('\xE0'), 'ascii'), '\xE0')
            self.assertRaises(UnicodeDecodeError, to_native_str, b('\xC3\xA0'),
                              'ascii')
        else:
            self.assertRaises(UnicodeEncodeError, to_native_str, u('\xE0'),
                              'ascii')
            self.assertEqual(to_native_str(b('\xC3\xA0'), 'ascii'), '\xC3\xA0')

        # test latin-1
        self.assertEqual(to_native_str(u('\xE0'), 'latin-1'), '\xE0')
        self.assertEqual(to_native_str(b('\xE0'), 'latin-1'), '\xE0')

        # test utf-8
        self.assertEqual(to_native_str(u('\xE0'), 'utf-8'),
                         '\xE0' if PY3 else '\xC3\xA0')
        self.assertEqual(to_native_str(b('\xC3\xA0'), 'utf-8'),
                         '\xE0' if PY3 else '\xC3\xA0')

        # other types rejected
        self.assertRaises(TypeError, to_native_str, None, 'ascii')

    def test_is_ascii_safe(self):
        """test is_ascii_safe()"""
        from passlib.utils import is_ascii_safe
        self.assertTrue(is_ascii_safe(b("\x00abc\x7f")))
        self.assertTrue(is_ascii_safe(u("\x00abc\x7f")))
        self.assertFalse(is_ascii_safe(b("\x00abc\x80")))
        self.assertFalse(is_ascii_safe(u("\x00abc\x80")))

    def test_is_same_codec(self):
        """test is_same_codec()"""
        from passlib.utils import is_same_codec

        self.assertTrue(is_same_codec(None, None))
        self.assertFalse(is_same_codec(None, 'ascii'))

        self.assertTrue(is_same_codec("ascii", "ascii"))
        self.assertTrue(is_same_codec("ascii", "ASCII"))

        self.assertTrue(is_same_codec("utf-8", "utf-8"))
        self.assertTrue(is_same_codec("utf-8", "utf8"))
        self.assertTrue(is_same_codec("utf-8", "UTF_8"))

        self.assertFalse(is_same_codec("ascii", "utf-8"))

#=============================================================================
# base64engine
#=============================================================================
class Base64EngineTest(TestCase):
    """test standalone parts of Base64Engine"""
    # NOTE: most Base64Engine testing done via _Base64Test subclasses below.

    def test_constructor(self):
        from passlib.utils import Base64Engine, AB64_CHARS

        # bad charmap type
        self.assertRaises(TypeError, Base64Engine, 1)

        # bad charmap size
        self.assertRaises(ValueError, Base64Engine, AB64_CHARS[:-1])

        # dup charmap letter
        self.assertRaises(ValueError, Base64Engine, AB64_CHARS[:-1] + "A")

    def test_ab64(self):
        from passlib.utils import ab64_decode
        # TODO: make ab64_decode (and a b64 variant) *much* stricter about
        # padding chars, etc.

        # 1 mod 4 not valid
        self.assertRaises(ValueError, ab64_decode, "abcde")

class _Base64Test(TestCase):
    """common tests for all Base64Engine instances"""
    #===================================================================
    # class attrs
    #===================================================================

    # Base64Engine instance to test
    engine = None

    # pairs of (raw, encoded) bytes to test - should encode/decode correctly
    encoded_data = None

    # tuples of (encoded, value, bits) for known integer encodings
    encoded_ints = None

    # invalid encoded byte
    bad_byte = b("?")

    # helper to generate bytemap-specific strings
    def m(self, *offsets):
        """generate byte string from offsets"""
        return join_bytes(self.engine.bytemap[o:o+1] for o in offsets)

    #===================================================================
    # test encode_bytes
    #===================================================================
    def test_encode_bytes(self):
        """test encode_bytes() against reference inputs"""
        engine = self.engine
        encode = engine.encode_bytes
        for raw, encoded in self.encoded_data:
            result = encode(raw)
            self.assertEqual(result, encoded, "encode %r:" % (raw,))

    def test_encode_bytes_bad(self):
        """test encode_bytes() with bad input"""
        engine = self.engine
        encode = engine.encode_bytes
        self.assertRaises(TypeError, encode, u('\x00'))
        self.assertRaises(TypeError, encode, None)

    #===================================================================
    # test decode_bytes
    #===================================================================
    def test_decode_bytes(self):
        """test decode_bytes() against reference inputs"""
        engine = self.engine
        decode = engine.decode_bytes
        for raw, encoded in self.encoded_data:
            result = decode(encoded)
            self.assertEqual(result, raw, "decode %r:" % (encoded,))

    def test_decode_bytes_padding(self):
        """test decode_bytes() ignores padding bits"""
        bchr = (lambda v: bytes([v])) if PY3 else chr
        engine = self.engine
        m = self.m
        decode = engine.decode_bytes
        BNULL = b("\x00")

        # length == 2 mod 4: 4 bits of padding
        self.assertEqual(decode(m(0,0)), BNULL)
        for i in range(0,6):
            if engine.big: # 4 lsb padding
                correct = BNULL if i < 4 else bchr(1<<(i-4))
            else: # 4 msb padding
                correct = bchr(1<<(i+6)) if i < 2 else BNULL
            self.assertEqual(decode(m(0,1<<i)), correct, "%d/4 bits:" % i)

        # length == 3 mod 4: 2 bits of padding
        self.assertEqual(decode(m(0,0,0)), BNULL*2)
        for i in range(0,6):
            if engine.big: # 2 lsb are padding
                correct = BNULL if i < 2 else bchr(1<<(i-2))
            else: # 2 msg are padding
                correct = bchr(1<<(i+4)) if i < 4 else BNULL
            self.assertEqual(decode(m(0,0,1<<i)), BNULL + correct,
                             "%d/2 bits:" % i)

    def test_decode_bytes_bad(self):
        """test decode_bytes() with bad input"""
        engine = self.engine
        decode = engine.decode_bytes

        # wrong size (1 % 4)
        self.assertRaises(ValueError, decode, engine.bytemap[:5])

        # wrong char
        self.assertTrue(self.bad_byte not in engine.bytemap)
        self.assertRaises(ValueError, decode, self.bad_byte*4)

        # wrong type
        self.assertRaises(TypeError, decode, engine.charmap[:4])
        self.assertRaises(TypeError, decode, None)

    #===================================================================
    # encode_bytes+decode_bytes
    #===================================================================
    def test_codec(self):
        """test encode_bytes/decode_bytes against random data"""
        engine = self.engine
        from passlib.utils import getrandbytes, getrandstr
        saw_zero = False
        for i in irange(500):
            #
            # test raw -> encode() -> decode() -> raw
            #

            # generate some random bytes
            size = random.randint(1 if saw_zero else 0, 12)
            if not size:
                saw_zero = True
            enc_size = (4*size+2)//3
            raw = getrandbytes(random, size)

            # encode them, check invariants
            encoded = engine.encode_bytes(raw)
            self.assertEqual(len(encoded), enc_size)

            # make sure decode returns original
            result = engine.decode_bytes(encoded)
            self.assertEqual(result, raw)

            #
            # test encoded -> decode() -> encode() -> encoded
            #

            # generate some random encoded data
            if size % 4 == 1:
                size += random.choice([-1,1,2])
            raw_size = 3*size//4
            encoded = getrandstr(random, engine.bytemap, size)

            # decode them, check invariants
            raw = engine.decode_bytes(encoded)
            self.assertEqual(len(raw), raw_size, "encoded %d:" % size)

            # make sure encode returns original (barring padding bits)
            result = engine.encode_bytes(raw)
            if size % 4:
                self.assertEqual(result[:-1], encoded[:-1])
            else:
                self.assertEqual(result, encoded)

    def test_repair_unused(self):
        """test repair_unused()"""
        # NOTE: this test relies on encode_bytes() always returning clear
        # padding bits - which should be ensured by test vectors.
        from passlib.utils import rng, getrandstr
        engine = self.engine
        check_repair_unused = self.engine.check_repair_unused
        i = 0
        while i < 300:
            size = rng.randint(0,23)
            cdata = getrandstr(rng, engine.charmap, size).encode("ascii")
            if size & 3 == 1:
                # should throw error
                self.assertRaises(ValueError, check_repair_unused, cdata)
                continue
            rdata = engine.encode_bytes(engine.decode_bytes(cdata))
            if rng.random() < .5:
                cdata = cdata.decode("ascii")
                rdata = rdata.decode("ascii")
            if cdata == rdata:
                # should leave unchanged
                ok, result = check_repair_unused(cdata)
                self.assertFalse(ok)
                self.assertEqual(result, rdata)
            else:
                # should repair bits
                self.assertNotEqual(size % 4, 0)
                ok, result = check_repair_unused(cdata)
                self.assertTrue(ok)
                self.assertEqual(result, rdata)
            i += 1

    #===================================================================
    # test transposed encode/decode - encoding independant
    #===================================================================
    # NOTE: these tests assume normal encode/decode has been tested elsewhere.

    transposed = [
        # orig, result, transpose map
        (b("\x33\x22\x11"), b("\x11\x22\x33"),[2,1,0]),
        (b("\x22\x33\x11"), b("\x11\x22\x33"),[1,2,0]),
    ]

    transposed_dups = [
        # orig, result, transpose projection
        (b("\x11\x11\x22"), b("\x11\x22\x33"),[0,0,1]),
    ]

    def test_encode_transposed_bytes(self):
        """test encode_transposed_bytes()"""
        engine = self.engine
        for result, input, offsets in self.transposed + self.transposed_dups:
            tmp = engine.encode_transposed_bytes(input, offsets)
            out = engine.decode_bytes(tmp)
            self.assertEqual(out, result)

        self.assertRaises(TypeError, engine.encode_transposed_bytes, u("a"), [])

    def test_decode_transposed_bytes(self):
        """test decode_transposed_bytes()"""
        engine = self.engine
        for input, result, offsets in self.transposed:
            tmp = engine.encode_bytes(input)
            out = engine.decode_transposed_bytes(tmp, offsets)
            self.assertEqual(out, result)

    def test_decode_transposed_bytes_bad(self):
        """test decode_transposed_bytes() fails if map is a one-way"""
        engine = self.engine
        for input, _, offsets in self.transposed_dups:
            tmp = engine.encode_bytes(input)
            self.assertRaises(TypeError, engine.decode_transposed_bytes, tmp,
                              offsets)

    #===================================================================
    # test 6bit handling
    #===================================================================
    def check_int_pair(self, bits, encoded_pairs):
        """helper to check encode_intXX & decode_intXX functions"""
        engine = self.engine
        encode = getattr(engine, "encode_int%s" % bits)
        decode = getattr(engine, "decode_int%s" % bits)
        pad = -bits % 6
        chars = (bits+pad)//6
        upper = 1<<bits

        # test encode func
        for value, encoded in encoded_pairs:
            result = encode(value)
            self.assertIsInstance(result, bytes)
            self.assertEqual(result, encoded)
        self.assertRaises(ValueError, encode, -1)
        self.assertRaises(ValueError, encode, upper)

        # test decode func
        for value, encoded in encoded_pairs:
            self.assertEqual(decode(encoded), value, "encoded %r:" % (encoded,))
        m = self.m
        self.assertRaises(ValueError, decode, m(0)*(chars+1))
        self.assertRaises(ValueError, decode, m(0)*(chars-1))
        self.assertRaises(ValueError, decode, self.bad_byte*chars)
        self.assertRaises(TypeError, decode, engine.charmap[0])
        self.assertRaises(TypeError, decode, None)

        # do random testing.
        from passlib.utils import getrandstr
        for i in irange(100):
            # generate random value, encode, and then decode
            value = random.randint(0, upper-1)
            encoded = encode(value)
            self.assertEqual(len(encoded), chars)
            self.assertEqual(decode(encoded), value)

            # generate some random encoded data, decode, then encode.
            encoded = getrandstr(random, engine.bytemap, chars)
            value = decode(encoded)
            self.assertGreaterEqual(value, 0, "decode %r out of bounds:" % encoded)
            self.assertLess(value, upper, "decode %r out of bounds:" % encoded)
            result = encode(value)
            if pad:
                self.assertEqual(result[:-2], encoded[:-2])
            else:
                self.assertEqual(result, encoded)

    def test_int6(self):
        engine = self.engine
        m = self.m
        self.check_int_pair(6, [(0, m(0)), (63, m(63))])

    def test_int12(self):
        engine = self.engine
        m = self.m
        self.check_int_pair(12,[(0, m(0,0)),
            (63, m(0,63) if engine.big else m(63,0)), (0xFFF, m(63,63))])

    def test_int24(self):
        engine = self.engine
        m = self.m
        self.check_int_pair(24,[(0, m(0,0,0,0)),
            (63, m(0,0,0,63) if engine.big else m(63,0,0,0)),
            (0xFFFFFF, m(63,63,63,63))])

    def test_int64(self):
        # NOTE: this isn't multiple of 6, it has 2 padding bits appended
        # before encoding.
        engine = self.engine
        m = self.m
        self.check_int_pair(64, [(0, m(0,0,0,0, 0,0,0,0, 0,0,0)),
                (63, m(0,0,0,0, 0,0,0,0, 0,3,60) if engine.big else
                     m(63,0,0,0, 0,0,0,0, 0,0,0)),
                ((1<<64)-1, m(63,63,63,63, 63,63,63,63, 63,63,60) if engine.big
                    else m(63,63,63,63, 63,63,63,63, 63,63,15))])

    def test_encoded_ints(self):
        """test against reference integer encodings"""
        if not self.encoded_ints:
            raise self.skipTests("none defined for class")
        engine = self.engine
        for data, value, bits in self.encoded_ints:
            encode = getattr(engine, "encode_int%d" % bits)
            decode = getattr(engine, "decode_int%d" % bits)
            self.assertEqual(encode(value), data)
            self.assertEqual(decode(data), value)

    #===================================================================
    # eoc
    #===================================================================

# NOTE: testing H64 & H64Big should be sufficient to verify
# that Base64Engine() works in general.
from passlib.utils import h64, h64big

class H64_Test(_Base64Test):
    """test H64 codec functions"""
    engine = h64
    descriptionPrefix = "h64 codec"

    encoded_data = [
        # test lengths 0..6 to ensure tail is encoded properly
        (b(""),b("")),
        (b("\x55"),b("J/")),
        (b("\x55\xaa"),b("Jd8")),
        (b("\x55\xaa\x55"),b("JdOJ")),
        (b("\x55\xaa\x55\xaa"),b("JdOJe0")),
        (b("\x55\xaa\x55\xaa\x55"),b("JdOJeK3")),
        (b("\x55\xaa\x55\xaa\x55\xaa"),b("JdOJeKZe")),

        # test padding bits are null
        (b("\x55\xaa\x55\xaf"),b("JdOJj0")), # len = 1 mod 3
        (b("\x55\xaa\x55\xaa\x5f"),b("JdOJey3")), # len = 2 mod 3
    ]

    encoded_ints = [
        (b("z."), 63, 12),
        (b(".z"), 4032, 12),
    ]

class H64Big_Test(_Base64Test):
    """test H64Big codec functions"""
    engine = h64big
    descriptionPrefix = "h64big codec"

    encoded_data = [
        # test lengths 0..6 to ensure tail is encoded properly
        (b(""),b("")),
        (b("\x55"),b("JE")),
        (b("\x55\xaa"),b("JOc")),
        (b("\x55\xaa\x55"),b("JOdJ")),
        (b("\x55\xaa\x55\xaa"),b("JOdJeU")),
        (b("\x55\xaa\x55\xaa\x55"),b("JOdJeZI")),
        (b("\x55\xaa\x55\xaa\x55\xaa"),b("JOdJeZKe")),

        # test padding bits are null
        (b("\x55\xaa\x55\xaf"),b("JOdJfk")), # len = 1 mod 3
        (b("\x55\xaa\x55\xaa\x5f"),b("JOdJeZw")), # len = 2 mod 3
    ]

    encoded_ints = [
        (b(".z"), 63, 12),
        (b("z."), 4032, 12),
    ]

#=============================================================================
# eof
#=============================================================================
