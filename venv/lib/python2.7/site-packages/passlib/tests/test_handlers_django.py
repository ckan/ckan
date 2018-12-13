"""passlib.tests.test_handlers_django - tests for passlib hash algorithms"""
#=============================================================================
# imports
#=============================================================================
from __future__ import with_statement
# core
import hashlib
import logging; log = logging.getLogger(__name__)
import os
import warnings
# site
# pkg
from passlib import hash
from passlib.utils import repeat_string
from passlib.utils.compat import irange, PY3, u, get_method_function
from passlib.tests.utils import TestCase, HandlerCase, skipUnless, \
        TEST_MODE, b, catch_warnings, UserHandlerMixin, randintgauss, EncodingHandlerMixin
from passlib.tests.test_handlers import UPASS_WAV, UPASS_USD, UPASS_TABLE
# module

#=============================================================================
# django
#=============================================================================

# standard string django uses
UPASS_LETMEIN = u('l\xe8tmein')

def vstr(version):
    return ".".join(str(e) for e in version)

class _DjangoHelper(object):
    # NOTE: not testing against Django < 1.0 since it doesn't support
    # most of these hash formats.

    # flag that hash wasn't added until specified version
    min_django_version = ()

    def fuzz_verifier_django(self):
        from passlib.tests.test_ext_django import DJANGO_VERSION
        # check_password() not added until 1.0
        min_django_version = max(self.min_django_version, (1,0))
        if DJANGO_VERSION < min_django_version:
            return None
        from django.contrib.auth.models import check_password
        def verify_django(secret, hash):
            """django/check_password"""
            if (1,4) <= DJANGO_VERSION < (1,6) and not secret:
                return "skip"
            if self.handler.name == "django_bcrypt" and hash.startswith("bcrypt$$2y$"):
                hash = hash.replace("$$2y$", "$$2a$")
            if DJANGO_VERSION >= (1,5) and self.django_has_encoding_glitch and isinstance(secret, bytes):
                # e.g. unsalted_md5 on 1.5 and higher try to combine
                # salt + password before encoding to bytes, leading to ascii error.
                # this works around that issue.
                secret = secret.decode("utf-8")
            return check_password(secret, hash)
        return verify_django

    def test_90_django_reference(self):
        """run known correct hashes through Django's check_password()"""
        from passlib.tests.test_ext_django import DJANGO_VERSION
        # check_password() not added until 1.0
        min_django_version = max(self.min_django_version, (1,0))
        if DJANGO_VERSION < min_django_version:
            raise self.skipTest("Django >= %s not installed" % vstr(min_django_version))
        from django.contrib.auth.models import check_password
        assert self.known_correct_hashes
        for secret, hash in self.iter_known_hashes():
            if (1,4) <= DJANGO_VERSION < (1,6) and not secret:
                # django 1.4-1.5 rejects empty passwords
                self.assertFalse(check_password(secret, hash),
                                "empty string should not have verified")
                continue
            self.assertTrue(check_password(secret, hash),
                            "secret=%r hash=%r failed to verify" %
                            (secret, hash))
            self.assertFalse(check_password('x' + secret, hash),
                            "mangled secret=%r hash=%r incorrect verified" %
                            (secret, hash))

    django_has_encoding_glitch = False

    def test_91_django_generation(self):
        """test against output of Django's make_password()"""
        from passlib.tests.test_ext_django import DJANGO_VERSION
        # make_password() not added until 1.4
        min_django_version = max(self.min_django_version, (1,4))
        if DJANGO_VERSION < min_django_version:
            raise self.skipTest("Django >= %s not installed" % vstr(min_django_version))
        from passlib.utils import tick
        from django.contrib.auth.hashers import make_password
        name = self.handler.django_name # set for all the django_* handlers
        end = tick() + self.max_fuzz_time/2
        while tick() < end:
            secret, other = self.get_fuzz_password_pair()
            if not secret: # django 1.4 rejects empty passwords.
                continue
            if DJANGO_VERSION >= (1,5) and self.django_has_encoding_glitch and isinstance(secret, bytes):
                # e.g. unsalted_md5 on 1.5 and higher try to combine
                # salt + password before encoding to bytes, leading to ascii error.
                # this works around that issue.
                secret = secret.decode("utf-8")
            hash = make_password(secret, hasher=name)
            self.assertTrue(self.do_identify(hash))
            self.assertTrue(self.do_verify(secret, hash))
            self.assertFalse(self.do_verify(other, hash))

class django_disabled_test(HandlerCase):
    """test django_disabled"""
    handler = hash.django_disabled
    is_disabled_handler = True

    known_correct_hashes = [
        # *everything* should hash to "!", and nothing should verify
        ("password", "!"),
        ("", "!"),
        (UPASS_TABLE, "!"),
    ]

    known_alternate_hashes = [
        # django 1.6 appends random alpnum string
        ("!9wa845vn7098ythaehasldkfj", "password", "!"),
    ]

class django_des_crypt_test(HandlerCase, _DjangoHelper):
    """test django_des_crypt"""
    handler = hash.django_des_crypt
    secret_size = 8

    known_correct_hashes = [
        # ensures only first two digits of salt count.
        ("password",         'crypt$c2$c2M87q...WWcU'),
        ("password",         'crypt$c2e86$c2M87q...WWcU'),
        ("passwordignoreme", 'crypt$c2.AZ$c2M87q...WWcU'),

        # ensures utf-8 used for unicode
        (UPASS_USD, 'crypt$c2e86$c2hN1Bxd6ZiWs'),
        (UPASS_TABLE, 'crypt$0.aQs$0.wB.TT0Czvlo'),
        (u("hell\u00D6"), "crypt$sa$saykDgk3BPZ9E"),

        # prevent regression of issue 22
        ("foo", 'crypt$MNVY.9ajgdvDQ$MNVY.9ajgdvDQ'),
    ]

    known_alternate_hashes = [
        # ensure django 1.4 empty salt field is accepted;
        # but that salt field is re-filled (for django 1.0 compatibility)
        ('crypt$$c2M87q...WWcU', "password", 'crypt$c2$c2M87q...WWcU'),
    ]

    known_unidentified_hashes = [
        'sha1$aa$bb',
    ]

    known_malformed_hashes = [
        # checksum too short
        'crypt$c2$c2M87q',

        # salt must be >2
        'crypt$f$c2M87q...WWcU',

        # make sure first 2 chars of salt & chk field agree.
        'crypt$ffe86$c2M87q...WWcU',
    ]

class django_salted_md5_test(HandlerCase, _DjangoHelper):
    """test django_salted_md5"""
    handler = hash.django_salted_md5

    django_has_encoding_glitch = True

    known_correct_hashes = [
        # test extra large salt
        ("password",    'md5$123abcdef$c8272612932975ee80e8a35995708e80'),

        # test django 1.4 alphanumeric salt
        ("test", 'md5$3OpqnFAHW5CT$54b29300675271049a1ebae07b395e20'),

        # ensures utf-8 used for unicode
        (UPASS_USD,     'md5$c2e86$92105508419a81a6babfaecf876a2fa0'),
        (UPASS_TABLE,   'md5$d9eb8$01495b32852bffb27cf5d4394fe7a54c'),
    ]

    known_unidentified_hashes = [
        'sha1$aa$bb',
    ]

    known_malformed_hashes = [
        # checksum too short
        'md5$aa$bb',
    ]

    def fuzz_setting_salt_size(self):
        # workaround for django14 regression --
        # 1.4 won't accept hashes with empty salt strings, unlike 1.3 and earlier.
        # looks to be fixed in a future release -- https://code.djangoproject.com/ticket/18144
        # for now, we avoid salt_size==0 under 1.4
        handler = self.handler
        from passlib.tests.test_ext_django import has_django14
        default = handler.default_salt_size
        assert handler.min_salt_size == 0
        lower = 1 if has_django14 else 0
        upper = handler.max_salt_size or default*4
        return randintgauss(lower, upper, default, default*.5)

class django_salted_sha1_test(HandlerCase, _DjangoHelper):
    """test django_salted_sha1"""
    handler = hash.django_salted_sha1

    django_has_encoding_glitch = True

    known_correct_hashes = [
        # test extra large salt
        ("password",'sha1$123abcdef$e4a1877b0e35c47329e7ed7e58014276168a37ba'),

        # test django 1.4 alphanumeric salt
        ("test", 'sha1$bcwHF9Hy8lxS$6b4cfa0651b43161c6f1471ce9523acf1f751ba3'),

        # ensures utf-8 used for unicode
        (UPASS_USD,     'sha1$c2e86$0f75c5d7fbd100d587c127ef0b693cde611b4ada'),
        (UPASS_TABLE,   'sha1$6d853$ef13a4d8fb57aed0cb573fe9c82e28dc7fd372d4'),

        # generic password
        ("MyPassword",  'sha1$54123$893cf12e134c3c215f3a76bd50d13f92404a54d3'),
    ]

    known_unidentified_hashes = [
        'md5$aa$bb',
    ]

    known_malformed_hashes = [
        # checksum too short
        'sha1$c2e86$0f75',
    ]

    fuzz_setting_salt_size = get_method_function(django_salted_md5_test.fuzz_setting_salt_size)

class django_pbkdf2_sha256_test(HandlerCase, _DjangoHelper):
    """test django_pbkdf2_sha256"""
    handler = hash.django_pbkdf2_sha256
    min_django_version = (1,4)

    known_correct_hashes = [
        #
        # custom - generated via django 1.4 hasher
        #
        ('not a password',
         'pbkdf2_sha256$10000$kjVJaVz6qsnJ$5yPHw3rwJGECpUf70daLGhOrQ5+AMxIJdz1c3bqK1Rs='),
        (UPASS_TABLE,
         'pbkdf2_sha256$10000$bEwAfNrH1TlQ$OgYUblFNUX1B8GfMqaCYUK/iHyO0pa7STTDdaEJBuY0='),
    ]

class django_pbkdf2_sha1_test(HandlerCase, _DjangoHelper):
    """test django_pbkdf2_sha1"""
    handler = hash.django_pbkdf2_sha1
    min_django_version = (1,4)

    known_correct_hashes = [
        #
        # custom - generated via django 1.4 hashers
        #
        ('not a password',
         'pbkdf2_sha1$10000$wz5B6WkasRoF$atJmJ1o+XfJxKq1+Nu1f1i57Z5I='),
        (UPASS_TABLE,
         'pbkdf2_sha1$10000$KZKWwvqb8BfL$rw5pWsxJEU4JrZAQhHTCO+u0f5Y='),
    ]

class django_bcrypt_test(HandlerCase, _DjangoHelper):
    """test django_bcrypt"""
    handler = hash.django_bcrypt
    secret_size = 72
    min_django_version = (1,4)
    fuzz_salts_need_bcrypt_repair = True

    known_correct_hashes = [
        #
        # just copied and adapted a few test vectors from bcrypt (above),
        # since django_bcrypt is just a wrapper for the real bcrypt class.
        #
        ('', 'bcrypt$$2a$06$DCq7YPn5Rq63x1Lad4cll.TV4S6ytwfsfvkgY8jIucDrjc8deX1s.'),
        ('abcdefghijklmnopqrstuvwxyz',
             'bcrypt$$2a$10$fVH8e28OQRj9tqiDXs1e1uxpsjN0c7II7YPKXua2NAKYvM6iQk7dq'),
        (UPASS_TABLE,
                'bcrypt$$2a$05$Z17AXnnlpzddNUvnC6cZNOSwMA/8oNiKnHTHTwLlBijfucQQlHjaG'),
    ]

    # NOTE: the following have been cloned from _bcrypt_test()

    def populate_settings(self, kwds):
        # speed up test w/ lower rounds
        kwds.setdefault("rounds", 4)
        super(django_bcrypt_test, self).populate_settings(kwds)

    def fuzz_setting_rounds(self):
        # decrease default rounds for fuzz testing to speed up volume.
        return randintgauss(5, 8, 6, 1)

    def fuzz_setting_ident(self):
        # omit multi-ident tests, only $2a$ counts for this class
        return None

django_bcrypt_test = skipUnless(hash.bcrypt.has_backend(),
                                "no bcrypt backends available")(django_bcrypt_test)

class django_bcrypt_sha256_test(HandlerCase, _DjangoHelper):
    """test django_bcrypt_sha256"""
    handler = hash.django_bcrypt_sha256
    min_django_version = (1,6)
    forbidden_characters = None
    fuzz_salts_need_bcrypt_repair = True

    known_correct_hashes = [
        #
        # custom - generated via django 1.6 hasher
        #
        ('',
            'bcrypt_sha256$$2a$06$/3OeRpbOf8/l6nPPRdZPp.nRiyYqPobEZGdNRBWihQhiFDh1ws1tu'),
        (UPASS_LETMEIN,
            'bcrypt_sha256$$2a$08$NDjSAIcas.EcoxCRiArvT.MkNiPYVhrsrnJsRkLueZOoV1bsQqlmC'),
        (UPASS_TABLE,
            'bcrypt_sha256$$2a$06$kCXUnRFQptGg491siDKNTu8RxjBGSjALHRuvhPYNFsa4Ea5d9M48u'),

        # test >72 chars is hashed correctly -- under bcrypt these hash the same.
        (repeat_string("abc123",72),
            'bcrypt_sha256$$2a$06$Tg/oYyZTyAf.Nb3qSgN61OySmyXA8FoY4PjGizjE1QSDfuL5MXNni'),
        (repeat_string("abc123",72)+"qwr",
            'bcrypt_sha256$$2a$06$Tg/oYyZTyAf.Nb3qSgN61Ocy0BEz1RK6xslSNi8PlaLX2pe7x/KQG'),
        (repeat_string("abc123",72)+"xyz",
            'bcrypt_sha256$$2a$06$Tg/oYyZTyAf.Nb3qSgN61OvY2zoRVUa2Pugv2ExVOUT2YmhvxUFUa'),
    ]

    known_malformed_hashers = [
        # data in django salt field
        'bcrypt_sha256$xyz$2a$06$/3OeRpbOf8/l6nPPRdZPp.nRiyYqPobEZGdNRBWihQhiFDh1ws1tu',
    ]

    def test_30_HasManyIdents(self):
        raise self.skipTest("multiple idents not supported")

    def test_30_HasOneIdent(self):
        # forbidding ident keyword, django doesn't support configuring this
        handler = self.handler
        handler(use_defaults=True)
        self.assertRaises(TypeError, handler, ident="$2a$", use_defaults=True)

    # NOTE: the following have been cloned from _bcrypt_test()

    def populate_settings(self, kwds):
        # speed up test w/ lower rounds
        kwds.setdefault("rounds", 4)
        super(django_bcrypt_sha256_test, self).populate_settings(kwds)

    def fuzz_setting_rounds(self):
        # decrease default rounds for fuzz testing to speed up volume.
        return randintgauss(5, 8, 6, 1)

    def fuzz_setting_ident(self):
        # omit multi-ident tests, only $2a$ counts for this class
        return None

django_bcrypt_sha256_test = skipUnless(hash.bcrypt.has_backend(),
                                       "no bcrypt backends available")(django_bcrypt_sha256_test)

#=============================================================================
# eof
#=============================================================================
