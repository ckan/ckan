"""tests for passlib.utils.(des|pbkdf2|md4)"""
#=============================================================================
# imports
#=============================================================================
from __future__ import with_statement
# core
from binascii import hexlify, unhexlify
import hashlib
import hmac
import sys
import random
import warnings
# site
try:
    import M2Crypto
except ImportError:
    M2Crypto = None
# pkg
# module
from passlib.utils.compat import b, bytes, bascii_to_str, irange, PY2, PY3, u, \
                                 unicode, join_bytes, PYPY, JYTHON
from passlib.tests.utils import TestCase, TEST_MODE, catch_warnings, skipUnless, skipIf

#=============================================================================
# support
#=============================================================================
def hb(source):
    return unhexlify(b(source))

#=============================================================================
# test assorted crypto helpers
#=============================================================================
class CryptoTest(TestCase):
    """test various crypto functions"""

    ndn_formats = ["hashlib", "iana"]
    ndn_values = [
        # (iana name, hashlib name, ... other unnormalized names)
        ("md5", "md5",          "SCRAM-MD5-PLUS", "MD-5"),
        ("sha1", "sha-1",       "SCRAM-SHA-1", "SHA1"),
        ("sha256", "sha-256",   "SHA_256", "sha2-256"),
        ("ripemd", "ripemd",    "SCRAM-RIPEMD", "RIPEMD"),
        ("ripemd160", "ripemd-160",
                                "SCRAM-RIPEMD-160", "RIPEmd160"),
        ("test128", "test-128", "TEST128"),
        ("test2", "test2", "TEST-2"),
        ("test3128", "test3-128", "TEST-3-128"),
    ]

    def test_norm_hash_name(self):
        """test norm_hash_name()"""
        from itertools import chain
        from passlib.utils.pbkdf2 import norm_hash_name, _nhn_hash_names

        # test formats
        for format in self.ndn_formats:
            norm_hash_name("md4", format)
        self.assertRaises(ValueError, norm_hash_name, "md4", None)
        self.assertRaises(ValueError, norm_hash_name, "md4", "fake")

        # test types
        self.assertEqual(norm_hash_name(u("MD4")), "md4")
        self.assertEqual(norm_hash_name(b("MD4")), "md4")
        self.assertRaises(TypeError, norm_hash_name, None)

        # test selected results
        with catch_warnings():
            warnings.filterwarnings("ignore", '.*unknown hash')
            for row in chain(_nhn_hash_names, self.ndn_values):
                for idx, format in enumerate(self.ndn_formats):
                    correct = row[idx]
                    for value in row:
                        result = norm_hash_name(value, format)
                        self.assertEqual(result, correct,
                                         "name=%r, format=%r:" % (value,
                                                                  format))

    # TODO: write full test of get_prf(), currently relying on pbkdf2 testing

#=============================================================================
# test DES routines
#=============================================================================
class DesTest(TestCase):
    descriptionPrefix = "DES"

    # test vectors taken from http://www.skepticfiles.org/faq/testdes.htm
    des_test_vectors = [
        # key, plaintext, ciphertext
        (0x0000000000000000, 0x0000000000000000, 0x8CA64DE9C1B123A7),
        (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF, 0x7359B2163E4EDC58),
        (0x3000000000000000, 0x1000000000000001, 0x958E6E627A05557B),
        (0x1111111111111111, 0x1111111111111111, 0xF40379AB9E0EC533),
        (0x0123456789ABCDEF, 0x1111111111111111, 0x17668DFC7292532D),
        (0x1111111111111111, 0x0123456789ABCDEF, 0x8A5AE1F81AB8F2DD),
        (0x0000000000000000, 0x0000000000000000, 0x8CA64DE9C1B123A7),
        (0xFEDCBA9876543210, 0x0123456789ABCDEF, 0xED39D950FA74BCC4),
        (0x7CA110454A1A6E57, 0x01A1D6D039776742, 0x690F5B0D9A26939B),
        (0x0131D9619DC1376E, 0x5CD54CA83DEF57DA, 0x7A389D10354BD271),
        (0x07A1133E4A0B2686, 0x0248D43806F67172, 0x868EBB51CAB4599A),
        (0x3849674C2602319E, 0x51454B582DDF440A, 0x7178876E01F19B2A),
        (0x04B915BA43FEB5B6, 0x42FD443059577FA2, 0xAF37FB421F8C4095),
        (0x0113B970FD34F2CE, 0x059B5E0851CF143A, 0x86A560F10EC6D85B),
        (0x0170F175468FB5E6, 0x0756D8E0774761D2, 0x0CD3DA020021DC09),
        (0x43297FAD38E373FE, 0x762514B829BF486A, 0xEA676B2CB7DB2B7A),
        (0x07A7137045DA2A16, 0x3BDD119049372802, 0xDFD64A815CAF1A0F),
        (0x04689104C2FD3B2F, 0x26955F6835AF609A, 0x5C513C9C4886C088),
        (0x37D06BB516CB7546, 0x164D5E404F275232, 0x0A2AEEAE3FF4AB77),
        (0x1F08260D1AC2465E, 0x6B056E18759F5CCA, 0xEF1BF03E5DFA575A),
        (0x584023641ABA6176, 0x004BD6EF09176062, 0x88BF0DB6D70DEE56),
        (0x025816164629B007, 0x480D39006EE762F2, 0xA1F9915541020B56),
        (0x49793EBC79B3258F, 0x437540C8698F3CFA, 0x6FBF1CAFCFFD0556),
        (0x4FB05E1515AB73A7, 0x072D43A077075292, 0x2F22E49BAB7CA1AC),
        (0x49E95D6D4CA229BF, 0x02FE55778117F12A, 0x5A6B612CC26CCE4A),
        (0x018310DC409B26D6, 0x1D9D5C5018F728C2, 0x5F4C038ED12B2E41),
        (0x1C587F1C13924FEF, 0x305532286D6F295A, 0x63FAC0D034D9F793),
        (0x0101010101010101, 0x0123456789ABCDEF, 0x617B3A0CE8F07100),
        (0x1F1F1F1F0E0E0E0E, 0x0123456789ABCDEF, 0xDB958605F8C8C606),
        (0xE0FEE0FEF1FEF1FE, 0x0123456789ABCDEF, 0xEDBFD1C66C29CCC7),
        (0x0000000000000000, 0xFFFFFFFFFFFFFFFF, 0x355550B2150E2451),
        (0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0xCAAAAF4DEAF1DBAE),
        (0x0123456789ABCDEF, 0x0000000000000000, 0xD5D44FF720683D0D),
        (0xFEDCBA9876543210, 0xFFFFFFFFFFFFFFFF, 0x2A2BB008DF97C2F2),
    ]

    def test_01_expand(self):
        """test expand_des_key()"""
        from passlib.utils.des import expand_des_key, shrink_des_key, \
                                      _KDATA_MASK, INT_56_MASK

        # make sure test vectors are preserved (sans parity bits)
        # uses ints, bytes are tested under # 02
        for key1, _, _ in self.des_test_vectors:
            key2 = shrink_des_key(key1)
            key3 = expand_des_key(key2)
            # NOTE: this assumes expand_des_key() sets parity bits to 0
            self.assertEqual(key3, key1 & _KDATA_MASK)

        # type checks
        self.assertRaises(TypeError, expand_des_key, 1.0)

        # too large
        self.assertRaises(ValueError, expand_des_key, INT_56_MASK+1)
        self.assertRaises(ValueError, expand_des_key, b("\x00")*8)

        # too small
        self.assertRaises(ValueError, expand_des_key, -1)
        self.assertRaises(ValueError, expand_des_key, b("\x00")*6)

    def test_02_shrink(self):
        """test shrink_des_key()"""
        from passlib.utils.des import expand_des_key, shrink_des_key, \
                                      INT_64_MASK
        from passlib.utils import random, getrandbytes

        # make sure reverse works for some random keys
        # uses bytes, ints are tested under # 01
        for i in range(20):
            key1 = getrandbytes(random, 7)
            key2 = expand_des_key(key1)
            key3 = shrink_des_key(key2)
            self.assertEqual(key3, key1)

        # type checks
        self.assertRaises(TypeError, shrink_des_key, 1.0)

        # too large
        self.assertRaises(ValueError, shrink_des_key, INT_64_MASK+1)
        self.assertRaises(ValueError, shrink_des_key, b("\x00")*9)

        # too small
        self.assertRaises(ValueError, shrink_des_key, -1)
        self.assertRaises(ValueError, shrink_des_key, b("\x00")*7)

    def _random_parity(self, key):
        """randomize parity bits"""
        from passlib.utils.des import _KDATA_MASK, _KPARITY_MASK, INT_64_MASK
        from passlib.utils import rng
        return (key & _KDATA_MASK) | (rng.randint(0,INT_64_MASK) & _KPARITY_MASK)

    def test_03_encrypt_bytes(self):
        """test des_encrypt_block()"""
        from passlib.utils.des import (des_encrypt_block, shrink_des_key,
                                       _pack64, _unpack64)

        # run through test vectors
        for key, plaintext, correct in self.des_test_vectors:
            # convert to bytes
            key = _pack64(key)
            plaintext = _pack64(plaintext)
            correct = _pack64(correct)

            # test 64-bit key
            result = des_encrypt_block(key, plaintext)
            self.assertEqual(result, correct, "key=%r plaintext=%r:" %
                                              (key, plaintext))

            # test 56-bit version
            key2 = shrink_des_key(key)
            result = des_encrypt_block(key2, plaintext)
            self.assertEqual(result, correct, "key=%r shrink(key)=%r plaintext=%r:" %
                                              (key, key2, plaintext))

            # test with random parity bits
            for _ in range(20):
                key3 = _pack64(self._random_parity(_unpack64(key)))
                result = des_encrypt_block(key3, plaintext)
                self.assertEqual(result, correct, "key=%r rndparity(key)=%r plaintext=%r:" %
                                                  (key, key3, plaintext))

        # check invalid keys
        stub = b('\x00') * 8
        self.assertRaises(TypeError, des_encrypt_block, 0, stub)
        self.assertRaises(ValueError, des_encrypt_block, b('\x00')*6, stub)

        # check invalid input
        self.assertRaises(TypeError, des_encrypt_block, stub, 0)
        self.assertRaises(ValueError, des_encrypt_block, stub, b('\x00')*7)

        # check invalid salts
        self.assertRaises(ValueError, des_encrypt_block, stub, stub, salt=-1)
        self.assertRaises(ValueError, des_encrypt_block, stub, stub, salt=1<<24)

        # check invalid rounds
        self.assertRaises(ValueError, des_encrypt_block, stub, stub, 0, rounds=0)

    def test_04_encrypt_ints(self):
        """test des_encrypt_int_block()"""
        from passlib.utils.des import des_encrypt_int_block

        # run through test vectors
        for key, plaintext, correct in self.des_test_vectors:
            # test 64-bit key
            result = des_encrypt_int_block(key, plaintext)
            self.assertEqual(result, correct, "key=%r plaintext=%r:" %
                                              (key, plaintext))

            # test with random parity bits
            for _ in range(20):
                key3 = self._random_parity(key)
                result = des_encrypt_int_block(key3, plaintext)
                self.assertEqual(result, correct, "key=%r rndparity(key)=%r plaintext=%r:" %
                                                  (key, key3, plaintext))

        # check invalid keys
        self.assertRaises(TypeError, des_encrypt_int_block, b('\x00'), 0)
        self.assertRaises(ValueError, des_encrypt_int_block, -1, 0)

        # check invalid input
        self.assertRaises(TypeError, des_encrypt_int_block, 0, b('\x00'))
        self.assertRaises(ValueError, des_encrypt_int_block, 0, -1)

        # check invalid salts
        self.assertRaises(ValueError, des_encrypt_int_block, 0, 0, salt=-1)
        self.assertRaises(ValueError, des_encrypt_int_block, 0, 0, salt=1<<24)

        # check invalid rounds
        self.assertRaises(ValueError, des_encrypt_int_block, 0, 0, 0, rounds=0)

#=============================================================================
# test pure-python MD4 implementation
#=============================================================================
from passlib.utils.md4 import _has_native_md4
has_native_md4 = _has_native_md4()

class _MD4_Test(TestCase):
    _disable_native = False

    def setUp(self):
        super(_MD4_Test, self).setUp()
        import passlib.utils.md4 as mod
        if has_native_md4 and self._disable_native:
            self.addCleanup(setattr, mod, "md4", mod.md4)
            mod.md4 = mod._builtin_md4

    vectors = [
        # input -> hex digest
        # test vectors from http://www.faqs.org/rfcs/rfc1320.html - A.5
        (b(""), "31d6cfe0d16ae931b73c59d7e0c089c0"),
        (b("a"), "bde52cb31de33e46245e05fbdbd6fb24"),
        (b("abc"), "a448017aaf21d8525fc10ae87aa6729d"),
        (b("message digest"), "d9130a8164549fe818874806e1c7014b"),
        (b("abcdefghijklmnopqrstuvwxyz"), "d79e1c308aa5bbcdeea8ed63df412da9"),
        (b("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"), "043f8582f241db351ce627e153e7f0e4"),
        (b("12345678901234567890123456789012345678901234567890123456789012345678901234567890"), "e33b4ddc9c38f2199c3e7b164fcc0536"),
    ]

    def test_md4_update(self):
        """test md4 update"""
        from passlib.utils.md4 import md4
        h = md4(b(''))
        self.assertEqual(h.hexdigest(), "31d6cfe0d16ae931b73c59d7e0c089c0")

        # NOTE: under py2, hashlib methods try to encode to ascii,
        #       though shouldn't rely on that.
        if PY3 or self._disable_native:
            self.assertRaises(TypeError, h.update, u('x'))

        h.update(b('a'))
        self.assertEqual(h.hexdigest(), "bde52cb31de33e46245e05fbdbd6fb24")

        h.update(b('bcdefghijklmnopqrstuvwxyz'))
        self.assertEqual(h.hexdigest(), "d79e1c308aa5bbcdeea8ed63df412da9")

    def test_md4_hexdigest(self):
        """test md4 hexdigest()"""
        from passlib.utils.md4 import md4
        for input, hex in self.vectors:
            out = md4(input).hexdigest()
            self.assertEqual(out, hex)

    def test_md4_digest(self):
        """test md4 digest()"""
        from passlib.utils.md4 import md4
        for input, hex in self.vectors:
            out = bascii_to_str(hexlify(md4(input).digest()))
            self.assertEqual(out, hex)

    def test_md4_copy(self):
        """test md4 copy()"""
        from passlib.utils.md4 import md4
        h = md4(b('abc'))

        h2 = h.copy()
        h2.update(b('def'))
        self.assertEqual(h2.hexdigest(), '804e7f1c2586e50b49ac65db5b645131')

        h.update(b('ghi'))
        self.assertEqual(h.hexdigest(), 'c5225580bfe176f6deeee33dee98732c')

# create subclasses to test with and without native backend
class MD4_SSL_Test(_MD4_Test):
    descriptionPrefix = "MD4 (ssl version)"
MD4_SSL_TEST = skipUnless(has_native_md4, "hashlib lacks ssl support")(MD4_SSL_Test)

class MD4_Builtin_Test(_MD4_Test):
    descriptionPrefix = "MD4 (builtin version)"
    _disable_native = True
MD4_Builtin_Test = skipUnless(TEST_MODE("full") or not has_native_md4,
                              "skipped under current test mode")(MD4_Builtin_Test)

#=============================================================================
# test PBKDF1 support
#=============================================================================
class Pbkdf1_Test(TestCase):
    """test kdf helpers"""
    descriptionPrefix = "pbkdf1"

    pbkdf1_tests = [
        # (password, salt, rounds, keylen, hash, result)

        #
        # from http://www.di-mgt.com.au/cryptoKDFs.html
        #
        (b('password'), hb('78578E5A5D63CB06'), 1000, 16, 'sha1', hb('dc19847e05c64d2faf10ebfb4a3d2a20')),

        #
        # custom
        #
        (b('password'), b('salt'), 1000, 0, 'md5',    b('')),
        (b('password'), b('salt'), 1000, 1, 'md5',    hb('84')),
        (b('password'), b('salt'), 1000, 8, 'md5',    hb('8475c6a8531a5d27')),
        (b('password'), b('salt'), 1000, 16, 'md5', hb('8475c6a8531a5d27e386cd496457812c')),
        (b('password'), b('salt'), 1000, None, 'md5', hb('8475c6a8531a5d27e386cd496457812c')),
        (b('password'), b('salt'), 1000, None, 'sha1', hb('4a8fd48e426ed081b535be5769892fa396293efb')),
    ]
    if not (PYPY or JYTHON):
        pbkdf1_tests.append(
            (b('password'), b('salt'), 1000, None, 'md4', hb('f7f2e91100a8f96190f2dd177cb26453'))
        )

    def test_known(self):
        """test reference vectors"""
        from passlib.utils.pbkdf2 import pbkdf1
        for secret, salt, rounds, keylen, digest, correct in self.pbkdf1_tests:
            result = pbkdf1(secret, salt, rounds, keylen, digest)
            self.assertEqual(result, correct)

    def test_border(self):
        """test border cases"""
        from passlib.utils.pbkdf2 import pbkdf1
        def helper(secret=b('secret'), salt=b('salt'), rounds=1, keylen=1, hash='md5'):
            return pbkdf1(secret, salt, rounds, keylen, hash)
        helper()

        # salt/secret wrong type
        self.assertRaises(TypeError, helper, secret=1)
        self.assertRaises(TypeError, helper, salt=1)

        # non-existent hashes
        self.assertRaises(ValueError, helper, hash='missing')

        # rounds < 1 and wrong type
        self.assertRaises(ValueError, helper, rounds=0)
        self.assertRaises(TypeError, helper, rounds='1')

        # keylen < 0, keylen > block_size, and wrong type
        self.assertRaises(ValueError, helper, keylen=-1)
        self.assertRaises(ValueError, helper, keylen=17, hash='md5')
        self.assertRaises(TypeError, helper, keylen='1')

#=============================================================================
# test PBKDF2 support
#=============================================================================
class _Pbkdf2_Test(TestCase):
    """test pbkdf2() support"""
    _disable_m2crypto = False

    def setUp(self):
        super(_Pbkdf2_Test, self).setUp()
        import passlib.utils.pbkdf2 as mod

        # disable m2crypto support, and use software backend
        if M2Crypto and self._disable_m2crypto:
            self.addCleanup(setattr, mod, "_EVP", mod._EVP)
            mod._EVP = None

        # flush cached prf functions, since we're screwing with their backend.
        mod._clear_prf_cache()
        self.addCleanup(mod._clear_prf_cache)

    pbkdf2_test_vectors = [
        # (result, secret, salt, rounds, keylen, prf="sha1")

        #
        # from rfc 3962
        #

            # test case 1 / 128 bit
            (
                hb("cdedb5281bb2f801565a1122b2563515"),
                b("password"), b("ATHENA.MIT.EDUraeburn"), 1, 16
            ),

            # test case 2 / 128 bit
            (
                hb("01dbee7f4a9e243e988b62c73cda935d"),
                b("password"), b("ATHENA.MIT.EDUraeburn"), 2, 16
            ),

            # test case 2 / 256 bit
            (
                hb("01dbee7f4a9e243e988b62c73cda935da05378b93244ec8f48a99e61ad799d86"),
                b("password"), b("ATHENA.MIT.EDUraeburn"), 2, 32
            ),

            # test case 3 / 256 bit
            (
                hb("5c08eb61fdf71e4e4ec3cf6ba1f5512ba7e52ddbc5e5142f708a31e2e62b1e13"),
                b("password"), b("ATHENA.MIT.EDUraeburn"), 1200, 32
            ),

            # test case 4 / 256 bit
            (
                hb("d1daa78615f287e6a1c8b120d7062a493f98d203e6be49a6adf4fa574b6e64ee"),
                b("password"), b('\x12\x34\x56\x78\x78\x56\x34\x12'), 5, 32
            ),

            # test case 5 / 256 bit
            (
                hb("139c30c0966bc32ba55fdbf212530ac9c5ec59f1a452f5cc9ad940fea0598ed1"),
                b("X"*64), b("pass phrase equals block size"), 1200, 32
            ),

            # test case 6 / 256 bit
            (
                hb("9ccad6d468770cd51b10e6a68721be611a8b4d282601db3b36be9246915ec82a"),
                b("X"*65), b("pass phrase exceeds block size"), 1200, 32
            ),

        #
        # from rfc 6070
        #
            (
                hb("0c60c80f961f0e71f3a9b524af6012062fe037a6"),
                b("password"), b("salt"), 1, 20,
            ),

            (
                hb("ea6c014dc72d6f8ccd1ed92ace1d41f0d8de8957"),
                b("password"), b("salt"), 2, 20,
            ),

            (
                hb("4b007901b765489abead49d926f721d065a429c1"),
                b("password"), b("salt"), 4096, 20,
            ),

            # just runs too long - could enable if ALL option is set
            ##(
            ##
            ##    unhexlify("eefe3d61cd4da4e4e9945b3d6ba2158c2634e984"),
            ##    "password", "salt", 16777216, 20,
            ##),

            (
                hb("3d2eec4fe41c849b80c8d83662c0e44a8b291a964cf2f07038"),
                b("passwordPASSWORDpassword"),
                b("saltSALTsaltSALTsaltSALTsaltSALTsalt"),
                4096, 25,
            ),

            (
                hb("56fa6aa75548099dcc37d7f03425e0c3"),
                b("pass\00word"), b("sa\00lt"), 4096, 16,
            ),

        #
        # from example in http://grub.enbug.org/Authentication
        #
            (
               hb("887CFF169EA8335235D8004242AA7D6187A41E3187DF0CE14E256D85ED"
                  "97A97357AAA8FF0A3871AB9EEFF458392F462F495487387F685B7472FC"
                  "6C29E293F0A0"),
               b("hello"),
               hb("9290F727ED06C38BA4549EF7DE25CF5642659211B7FC076F2D28FEFD71"
                  "784BB8D8F6FB244A8CC5C06240631B97008565A120764C0EE9C2CB0073"
                  "994D79080136"),
               10000, 64, "hmac-sha512"
            ),

        #
        # custom
        #
            (
                hb('e248fb6b13365146f8ac6307cc222812'),
                b("secret"), b("salt"), 10, 16, "hmac-sha1",
            ),
            (
                hb('e248fb6b13365146f8ac6307cc2228127872da6d'),
                b("secret"), b("salt"), 10, None, "hmac-sha1",
            ),

        ]

    def test_known(self):
        """test reference vectors"""
        from passlib.utils.pbkdf2 import pbkdf2
        for row in self.pbkdf2_test_vectors:
            correct, secret, salt, rounds, keylen = row[:5]
            prf = row[5] if len(row) == 6 else "hmac-sha1"
            result = pbkdf2(secret, salt, rounds, keylen, prf)
            self.assertEqual(result, correct)

    def test_border(self):
        """test border cases"""
        from passlib.utils.pbkdf2 import pbkdf2
        def helper(secret=b('password'), salt=b('salt'), rounds=1, keylen=None, prf="hmac-sha1"):
            return pbkdf2(secret, salt, rounds, keylen, prf)
        helper()

        # invalid rounds
        self.assertRaises(ValueError, helper, rounds=0)
        self.assertRaises(TypeError, helper, rounds='x')

        # invalid keylen
        helper(keylen=0)
        self.assertRaises(ValueError, helper, keylen=-1)
        self.assertRaises(ValueError, helper, keylen=20*(2**32-1)+1)
        self.assertRaises(TypeError, helper, keylen='x')

        # invalid secret/salt type
        self.assertRaises(TypeError, helper, salt=5)
        self.assertRaises(TypeError, helper, secret=5)

        # invalid hash
        self.assertRaises(ValueError, helper, prf='hmac-foo')
        self.assertRaises(ValueError, helper, prf='foo')
        self.assertRaises(TypeError, helper, prf=5)

    def test_default_keylen(self):
        """test keylen==None"""
        from passlib.utils.pbkdf2 import pbkdf2
        def helper(secret=b('password'), salt=b('salt'), rounds=1, keylen=None, prf="hmac-sha1"):
            return pbkdf2(secret, salt, rounds, keylen, prf)
        self.assertEqual(len(helper(prf='hmac-sha1')), 20)
        self.assertEqual(len(helper(prf='hmac-sha256')), 32)

    def test_custom_prf(self):
        """test custom prf function"""
        from passlib.utils.pbkdf2 import pbkdf2
        def prf(key, msg):
            return hashlib.md5(key+msg+b('fooey')).digest()
        result = pbkdf2(b('secret'), b('salt'), 1000, 20, prf)
        self.assertEqual(result, hb('5fe7ce9f7e379d3f65cbc66ba8aa6440474a6849'))

# create subclasses to test with and without m2crypto
class Pbkdf2_M2Crypto_Test(_Pbkdf2_Test):
    descriptionPrefix = "pbkdf2 (m2crypto backend)"
Pbkdf2_M2Crypto_Test = skipUnless(M2Crypto, "M2Crypto not found")(Pbkdf2_M2Crypto_Test)

class Pbkdf2_Builtin_Test(_Pbkdf2_Test):
    descriptionPrefix = "pbkdf2 (builtin backend)"
    _disable_m2crypto = True
Pbkdf2_Builtin_Test = skipUnless(TEST_MODE("full") or not M2Crypto,
                                 "skipped under current test mode")(Pbkdf2_Builtin_Test)

#=============================================================================
# eof
#=============================================================================
