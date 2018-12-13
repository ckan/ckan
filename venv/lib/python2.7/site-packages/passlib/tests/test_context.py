"""tests for passlib.context"""
#=============================================================================
# imports
#=============================================================================
# core
from __future__ import with_statement
from passlib.utils.compat import PY3
if PY3:
    from configparser import NoSectionError
else:
    from ConfigParser import NoSectionError
import hashlib
import logging; log = logging.getLogger(__name__)
import re
import os
import time
import warnings
import sys
# site
# pkg
from passlib import hash
from passlib.context import CryptContext, LazyCryptContext
from passlib.exc import PasslibConfigWarning
from passlib.utils import tick, to_bytes, to_unicode
from passlib.utils.compat import irange, u, unicode, str_to_uascii, PY2
import passlib.utils.handlers as uh
from passlib.tests.utils import TestCase, catch_warnings, set_file, TICK_RESOLUTION, quicksleep
from passlib.registry import (register_crypt_handler_path,
                        _has_crypt_handler as has_crypt_handler,
                        _unload_handler_name as unload_handler_name,
                        get_crypt_handler,
                        )
# local
#=============================================================================
# support
#=============================================================================
here = os.path.abspath(os.path.dirname(__file__))

def merge_dicts(first, *args, **kwds):
    target = first.copy()
    for arg in args:
        target.update(arg)
    if kwds:
        target.update(kwds)
    return target

#=============================================================================
#
#=============================================================================
class CryptContextTest(TestCase):
    descriptionPrefix = "CryptContext"

    # TODO: these unittests could really use a good cleanup
    # and reorganizing, to ensure they're getting everything.

    #===================================================================
    # sample configurations used in tests
    #===================================================================

    #---------------------------------------------------------------
    # sample 1 - typical configuration
    #---------------------------------------------------------------
    sample_1_schemes = ["des_crypt", "md5_crypt", "bsdi_crypt", "sha512_crypt"]
    sample_1_handlers = [get_crypt_handler(name) for name in sample_1_schemes]

    sample_1_dict = dict(
        schemes = sample_1_schemes,
        default = "md5_crypt",
        all__vary_rounds = 0.1,
        bsdi_crypt__max_rounds = 30000,
        bsdi_crypt__default_rounds = 25000,
        sha512_crypt__max_rounds = 50000,
        sha512_crypt__min_rounds = 40000,
    )

    sample_1_resolved_dict = merge_dicts(sample_1_dict,
                                         schemes = sample_1_handlers)

    sample_1_unnormalized = u("""\
[passlib]
schemes = des_crypt, md5_crypt, bsdi_crypt, sha512_crypt
default = md5_crypt
; this is using %...
all__vary_rounds = 10%%
; this is using 'rounds' instead of 'default_rounds'
bsdi_crypt__rounds = 25000
bsdi_crypt__max_rounds = 30000
sha512_crypt__max_rounds = 50000
sha512_crypt__min_rounds = 40000
""")

    sample_1_unicode = u("""\
[passlib]
schemes = des_crypt, md5_crypt, bsdi_crypt, sha512_crypt
default = md5_crypt
all__vary_rounds = 0.1
bsdi_crypt__default_rounds = 25000
bsdi_crypt__max_rounds = 30000
sha512_crypt__max_rounds = 50000
sha512_crypt__min_rounds = 40000

""")

    #---------------------------------------------------------------
    # sample 1 external files
    #---------------------------------------------------------------

    # sample 1 string with '\n' linesep
    sample_1_path = os.path.join(here, "sample1.cfg")

    # sample 1 with '\r\n' linesep
    sample_1b_unicode = sample_1_unicode.replace(u("\n"), u("\r\n"))
    sample_1b_path = os.path.join(here, "sample1b.cfg")

    # sample 1 using UTF-16 and alt section
    sample_1c_bytes = sample_1_unicode.replace(u("[passlib]"),
                                               u("[mypolicy]")).encode("utf-16")
    sample_1c_path = os.path.join(here, "sample1c.cfg")

    # enable to regenerate sample files
    if False:
        set_file(sample_1_path, sample_1_unicode)
        set_file(sample_1b_path, sample_1b_unicode)
        set_file(sample_1c_path, sample_1c_bytes)

    #---------------------------------------------------------------
    # sample 2 & 12 - options patch
    #---------------------------------------------------------------
    sample_2_dict = dict(
        # using this to test full replacement of existing options
        bsdi_crypt__min_rounds = 29000,
        bsdi_crypt__max_rounds = 35000,
        bsdi_crypt__default_rounds = 31000,
        # using this to test partial replacement of existing options
        sha512_crypt__min_rounds=45000,
    )

    sample_2_unicode = """\
[passlib]
bsdi_crypt__min_rounds = 29000
bsdi_crypt__max_rounds = 35000
bsdi_crypt__default_rounds = 31000
sha512_crypt__min_rounds = 45000
"""

    # sample 2 overlayed on top of sample 1
    sample_12_dict = merge_dicts(sample_1_dict, sample_2_dict)

    #---------------------------------------------------------------
    # sample 3 & 123 - just changing default from sample 1
    #---------------------------------------------------------------
    sample_3_dict = dict(
        default="sha512_crypt",
    )

    # sample 3 overlayed on 2 overlayed on 1
    sample_123_dict = merge_dicts(sample_12_dict, sample_3_dict)

    #---------------------------------------------------------------
    # sample 4 - used by api tests
    #---------------------------------------------------------------
    sample_4_dict = dict(
        schemes = [ "des_crypt", "md5_crypt", "phpass", "bsdi_crypt",
                   "sha256_crypt"],
        deprecated = [ "des_crypt", ],
        default = "sha256_crypt",
        bsdi_crypt__max_rounds = 30,
        bsdi_crypt__default_rounds = 25,
        bsdi_crypt__vary_rounds = 0,
        sha256_crypt__max_rounds = 3000,
        sha256_crypt__min_rounds = 2000,
        sha256_crypt__default_rounds = 3000,
        phpass__ident = "H",
        phpass__default_rounds = 7,
    )

    #===================================================================
    # constructors
    #===================================================================
    def test_01_constructor(self):
        """test class constructor"""

        # test blank constructor works correctly
        ctx = CryptContext()
        self.assertEqual(ctx.to_dict(), {})

        # test sample 1 with scheme=names
        ctx = CryptContext(**self.sample_1_dict)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 1 with scheme=handlers
        ctx = CryptContext(**self.sample_1_resolved_dict)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 2: options w/o schemes
        ctx = CryptContext(**self.sample_2_dict)
        self.assertEqual(ctx.to_dict(), self.sample_2_dict)

        # test sample 3: default only
        ctx = CryptContext(**self.sample_3_dict)
        self.assertEqual(ctx.to_dict(), self.sample_3_dict)

        # test unicode scheme names (issue 54)
        ctx = CryptContext(schemes=[u("sha256_crypt")])
        self.assertEqual(ctx.schemes(), ("sha256_crypt",))

    def test_02_from_string(self):
        """test from_string() constructor"""
        # test sample 1 unicode
        ctx = CryptContext.from_string(self.sample_1_unicode)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 1 with unnormalized inputs
        ctx = CryptContext.from_string(self.sample_1_unnormalized)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 1 utf-8
        ctx = CryptContext.from_string(self.sample_1_unicode.encode("utf-8"))
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 1 w/ '\r\n' linesep
        ctx = CryptContext.from_string(self.sample_1b_unicode)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 1 using UTF-16 and alt section
        ctx = CryptContext.from_string(self.sample_1c_bytes, section="mypolicy",
                                     encoding="utf-16")
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test wrong type
        self.assertRaises(TypeError, CryptContext.from_string, None)

        # test missing section
        self.assertRaises(NoSectionError, CryptContext.from_string,
                          self.sample_1_unicode, section="fakesection")

    def test_03_from_path(self):
        """test from_path() constructor"""
        # make sure sample files exist
        if not os.path.exists(self.sample_1_path):
            raise RuntimeError("can't find data file: %r" % self.sample_1_path)

        # test sample 1
        ctx = CryptContext.from_path(self.sample_1_path)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 1 w/ '\r\n' linesep
        ctx = CryptContext.from_path(self.sample_1b_path)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test sample 1 encoding using UTF-16 and alt section
        ctx = CryptContext.from_path(self.sample_1c_path, section="mypolicy",
                                     encoding="utf-16")
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test missing file
        self.assertRaises(EnvironmentError, CryptContext.from_path,
                          os.path.join(here, "sample1xxx.cfg"))

        # test missing section
        self.assertRaises(NoSectionError, CryptContext.from_path,
                          self.sample_1_path, section="fakesection")

    def test_04_copy(self):
        """test copy() method"""
        cc1 = CryptContext(**self.sample_1_dict)

        # overlay sample 2 onto copy
        cc2 = cc1.copy(**self.sample_2_dict)
        self.assertEqual(cc1.to_dict(), self.sample_1_dict)
        self.assertEqual(cc2.to_dict(), self.sample_12_dict)

        # check that repeating overlay makes no change
        cc2b = cc2.copy(**self.sample_2_dict)
        self.assertEqual(cc1.to_dict(), self.sample_1_dict)
        self.assertEqual(cc2b.to_dict(), self.sample_12_dict)

        # overlay sample 3 on copy
        cc3 = cc2.copy(**self.sample_3_dict)
        self.assertEqual(cc3.to_dict(), self.sample_123_dict)

        # test empty copy creates separate copy
        cc4 = cc1.copy()
        self.assertIsNot(cc4, cc1)
        self.assertEqual(cc1.to_dict(), self.sample_1_dict)
        self.assertEqual(cc4.to_dict(), self.sample_1_dict)

        # ... and that modifying copy doesn't affect original
        cc4.update(**self.sample_2_dict)
        self.assertEqual(cc1.to_dict(), self.sample_1_dict)
        self.assertEqual(cc4.to_dict(), self.sample_12_dict)

    def test_09_repr(self):
        """test repr()"""
        cc1 = CryptContext(**self.sample_1_dict)
        self.assertRegex(repr(cc1), "^<CryptContext at 0x[0-9a-f]+>$")

    #===================================================================
    # modifiers
    #===================================================================
    def test_10_load(self):
        """test load() / load_path() method"""
        # NOTE: load() is the workhorse that handles all policy parsing,
        # compilation, and validation. most of its features are tested
        # elsewhere, since all the constructors and modifiers are just
        # wrappers for it.

        # source_type 'auto'
        ctx = CryptContext()

            # detect dict
        ctx.load(self.sample_1_dict)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

            # detect unicode string
        ctx.load(self.sample_1_unicode)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

            # detect bytes string
        ctx.load(self.sample_1_unicode.encode("utf-8"))
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

            # anything else - TypeError
        self.assertRaises(TypeError, ctx.load, None)

        # NOTE: load_path() tested by from_path()
        # NOTE: additional string tests done by from_string()

        # update flag - tested by update() method tests
        # encoding keyword - tested by from_string() & from_path()
        # section keyword - tested by from_string() & from_path()

        # test load empty
        ctx = CryptContext(**self.sample_1_dict)
        ctx.load({}, update=True)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # multiple loads should clear the state
        ctx = CryptContext()
        ctx.load(self.sample_1_dict)
        ctx.load(self.sample_2_dict)
        self.assertEqual(ctx.to_dict(), self.sample_2_dict)

    def test_11_load_rollback(self):
        """test load() errors restore old state"""
        # create initial context
        cc = CryptContext(["des_crypt", "sha256_crypt"],
            sha256_crypt__default_rounds=5000,
            all__vary_rounds=0.1,
            )
        result = cc.to_string()

        # do an update operation that should fail during parsing
        # XXX: not sure what the right error type is here.
        self.assertRaises(TypeError, cc.update, too__many__key__parts=True)
        self.assertEqual(cc.to_string(), result)

        # do an update operation that should fail during extraction
        # FIXME: this isn't failing even in broken case, need to figure out
        # way to ensure some keys come after this one.
        self.assertRaises(KeyError, cc.update, fake_context_option=True)
        self.assertEqual(cc.to_string(), result)

        # do an update operation that should fail during compilation
        self.assertRaises(ValueError, cc.update, sha256_crypt__min_rounds=10000)
        self.assertEqual(cc.to_string(), result)

    def test_12_update(self):
        """test update() method"""

        # empty overlay
        ctx = CryptContext(**self.sample_1_dict)
        ctx.update()
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)

        # test basic overlay
        ctx = CryptContext(**self.sample_1_dict)
        ctx.update(**self.sample_2_dict)
        self.assertEqual(ctx.to_dict(), self.sample_12_dict)

        # ... and again
        ctx.update(**self.sample_3_dict)
        self.assertEqual(ctx.to_dict(), self.sample_123_dict)

        # overlay w/ dict arg
        ctx = CryptContext(**self.sample_1_dict)
        ctx.update(self.sample_2_dict)
        self.assertEqual(ctx.to_dict(), self.sample_12_dict)

        # overlay w/ string
        ctx = CryptContext(**self.sample_1_dict)
        ctx.update(self.sample_2_unicode)
        self.assertEqual(ctx.to_dict(), self.sample_12_dict)

        # too many args
        self.assertRaises(TypeError, ctx.update, {}, {})
        self.assertRaises(TypeError, ctx.update, {}, schemes=['des_crypt'])

        # wrong arg type
        self.assertRaises(TypeError, ctx.update, None)

    #===================================================================
    # option parsing
    #===================================================================
    def test_20_options(self):
        """test basic option parsing"""
        def parse(**kwds):
            return CryptContext(**kwds).to_dict()

        #
        # common option parsing tests
        #

        # test keys with blank fields are rejected
            # blank option
        self.assertRaises(TypeError, CryptContext, __=0.1)
        self.assertRaises(TypeError, CryptContext, default__scheme__='x')

            # blank scheme
        self.assertRaises(TypeError, CryptContext, __option='x')
        self.assertRaises(TypeError, CryptContext, default____option='x')

            # blank category
        self.assertRaises(TypeError, CryptContext, __scheme__option='x')

        # test keys with too many field are rejected
        self.assertRaises(TypeError, CryptContext,
                          category__scheme__option__invalid = 30000)

        # keys with mixed separators should be handled correctly.
        # (testing actual data, not to_dict(), since re-render hid original bug)
        self.assertRaises(KeyError, parse,
                          **{"admin.context__schemes":"md5_crypt"})
        ctx = CryptContext(**{"schemes":"md5_crypt,des_crypt",
                              "admin.context__default":"des_crypt"})
        self.assertEqual(ctx.default_scheme("admin"), "des_crypt")

        #
        # context option -specific tests
        #

        # test context option key parsing
        result = dict(default="md5_crypt")
        self.assertEqual(parse(default="md5_crypt"), result)
        self.assertEqual(parse(context__default="md5_crypt"), result)
        self.assertEqual(parse(default__context__default="md5_crypt"), result)
        self.assertEqual(parse(**{"context.default":"md5_crypt"}), result)
        self.assertEqual(parse(**{"default.context.default":"md5_crypt"}), result)

        # test context option key parsing w/ category
        result = dict(admin__context__default="md5_crypt")
        self.assertEqual(parse(admin__context__default="md5_crypt"), result)
        self.assertEqual(parse(**{"admin.context.default":"md5_crypt"}), result)

        #
        # hash option -specific tests
        #

        # test hash option key parsing
        result = dict(all__vary_rounds=0.1)
        self.assertEqual(parse(all__vary_rounds=0.1), result)
        self.assertEqual(parse(default__all__vary_rounds=0.1), result)
        self.assertEqual(parse(**{"all.vary_rounds":0.1}), result)
        self.assertEqual(parse(**{"default.all.vary_rounds":0.1}), result)

        # test hash option key parsing w/ category
        result = dict(admin__all__vary_rounds=0.1)
        self.assertEqual(parse(admin__all__vary_rounds=0.1), result)
        self.assertEqual(parse(**{"admin.all.vary_rounds":0.1}), result)

        # settings not allowed if not in hash.settings_kwds
        ctx = CryptContext(["phpass", "md5_crypt"], phpass__ident="P")
        self.assertRaises(KeyError, ctx.copy, md5_crypt__ident="P")

        # hash options 'salt' and 'rounds' not allowed
        self.assertRaises(KeyError, CryptContext, schemes=["des_crypt"],
                                                  des_crypt__salt="xx")
        self.assertRaises(KeyError, CryptContext, schemes=["des_crypt"],
                                                  all__salt="xx")

    def test_21_schemes(self):
        """test 'schemes' context option parsing"""

        # schemes can be empty
        cc = CryptContext(schemes=None)
        self.assertEqual(cc.schemes(), ())

        # schemes can be list of names
        cc = CryptContext(schemes=["des_crypt", "md5_crypt"])
        self.assertEqual(cc.schemes(), ("des_crypt", "md5_crypt"))

        # schemes can be comma-sep string
        cc = CryptContext(schemes=" des_crypt, md5_crypt, ")
        self.assertEqual(cc.schemes(), ("des_crypt", "md5_crypt"))

        # schemes can be list of handlers
        cc = CryptContext(schemes=[hash.des_crypt, hash.md5_crypt])
        self.assertEqual(cc.schemes(), ("des_crypt", "md5_crypt"))

        # scheme must be name or handler
        self.assertRaises(TypeError, CryptContext, schemes=[uh.StaticHandler])

        # handlers must have a name
        class nameless(uh.StaticHandler):
            name = None
        self.assertRaises(ValueError, CryptContext, schemes=[nameless])

        # names must be unique
        class dummy_1(uh.StaticHandler):
            name = 'dummy_1'
        self.assertRaises(KeyError, CryptContext, schemes=[dummy_1, dummy_1])

        # schemes not allowed per-category
        self.assertRaises(KeyError, CryptContext,
                          admin__context__schemes=["md5_crypt"])

    def test_22_deprecated(self):
        """test 'deprecated' context option parsing"""
        def getdep(ctx, category=None):
            return [name for name in ctx.schemes()
                    if ctx._is_deprecated_scheme(name, category)]

        # no schemes - all deprecated values allowed
        cc = CryptContext(deprecated=["md5_crypt"])
        cc.update(schemes=["md5_crypt", "des_crypt"])
        self.assertEqual(getdep(cc),["md5_crypt"])

        # deprecated values allowed if subset of schemes
        cc = CryptContext(deprecated=["md5_crypt"], schemes=["md5_crypt", "des_crypt"])
        self.assertEqual(getdep(cc), ["md5_crypt"])

        # can be handler
        # XXX: allow handlers in deprecated list? not for now.
        self.assertRaises(TypeError, CryptContext, deprecated=[hash.md5_crypt],
                          schemes=["md5_crypt", "des_crypt"])
##        cc = CryptContext(deprecated=[hash.md5_crypt], schemes=["md5_crypt", "des_crypt"])
##        self.assertEqual(getdep(cc), ["md5_crypt"])

        # comma sep list
        cc = CryptContext(deprecated="md5_crypt,des_crypt", schemes=["md5_crypt", "des_crypt", "sha256_crypt"])
        self.assertEqual(getdep(cc), ["md5_crypt", "des_crypt"])

        # values outside of schemes not allowed
        self.assertRaises(KeyError, CryptContext, schemes=['des_crypt'],
                                                  deprecated=['md5_crypt'])

        # deprecating ALL schemes should cause ValueError
        self.assertRaises(ValueError, CryptContext,
                          schemes=['des_crypt'],
                          deprecated=['des_crypt'])
        self.assertRaises(ValueError, CryptContext,
                          schemes=['des_crypt', 'md5_crypt'],
                          admin__context__deprecated=['des_crypt', 'md5_crypt'])

        # deprecating explicit default scheme should cause ValueError

            # ... default listed as deprecated
        self.assertRaises(ValueError, CryptContext,
                          schemes=['des_crypt', 'md5_crypt'],
                          default="md5_crypt",
                          deprecated="md5_crypt")

            # ... global default deprecated per-category
        self.assertRaises(ValueError, CryptContext,
                          schemes=['des_crypt', 'md5_crypt'],
                          default="md5_crypt",
                          admin__context__deprecated="md5_crypt")

            # ... category default deprecated globally
        self.assertRaises(ValueError, CryptContext,
                          schemes=['des_crypt', 'md5_crypt'],
                          admin__context__default="md5_crypt",
                          deprecated="md5_crypt")

            # ... category default deprecated in category
        self.assertRaises(ValueError, CryptContext,
                          schemes=['des_crypt', 'md5_crypt'],
                          admin__context__default="md5_crypt",
                          admin__context__deprecated="md5_crypt")

        # category deplist should shadow default deplist
        CryptContext(
                          schemes=['des_crypt', 'md5_crypt'],
                          deprecated="md5_crypt",
                          admin__context__default="md5_crypt",
                          admin__context__deprecated=[])

        # wrong type
        self.assertRaises(TypeError, CryptContext, deprecated=123)

        # deprecated per-category
        cc = CryptContext(deprecated=["md5_crypt"],
                          schemes=["md5_crypt", "des_crypt"],
                          admin__context__deprecated=["des_crypt"],
                          )
        self.assertEqual(getdep(cc), ["md5_crypt"])
        self.assertEqual(getdep(cc, "user"), ["md5_crypt"])
        self.assertEqual(getdep(cc, "admin"), ["des_crypt"])

        # blank per-category deprecated list, shadowing default list
        cc = CryptContext(deprecated=["md5_crypt"],
                          schemes=["md5_crypt", "des_crypt"],
                          admin__context__deprecated=[],
                          )
        self.assertEqual(getdep(cc), ["md5_crypt"])
        self.assertEqual(getdep(cc, "user"), ["md5_crypt"])
        self.assertEqual(getdep(cc, "admin"), [])

    def test_23_default(self):
        """test 'default' context option parsing"""

        # anything allowed if no schemes
        self.assertEqual(CryptContext(default="md5_crypt").to_dict(),
                         dict(default="md5_crypt"))

        # default allowed if in scheme list
        ctx = CryptContext(default="md5_crypt", schemes=["des_crypt", "md5_crypt"])
        self.assertEqual(ctx.default_scheme(), "md5_crypt")

        # default can be handler
        # XXX: sure we want to allow this ? maybe deprecate in future.
        ctx = CryptContext(default=hash.md5_crypt, schemes=["des_crypt", "md5_crypt"])
        self.assertEqual(ctx.default_scheme(), "md5_crypt")

        # implicit default should be first non-deprecated scheme
        ctx = CryptContext(schemes=["des_crypt", "md5_crypt"])
        self.assertEqual(ctx.default_scheme(), "des_crypt")
        ctx.update(deprecated="des_crypt")
        self.assertEqual(ctx.default_scheme(), "md5_crypt")

        # error if not in scheme list
        self.assertRaises(KeyError, CryptContext, schemes=['des_crypt'],
                                                  default='md5_crypt')

        # wrong type
        self.assertRaises(TypeError, CryptContext, default=1)

        # per-category
        ctx = CryptContext(default="des_crypt",
                           schemes=["des_crypt", "md5_crypt"],
                           admin__context__default="md5_crypt")
        self.assertEqual(ctx.default_scheme(), "des_crypt")
        self.assertEqual(ctx.default_scheme("user"), "des_crypt")
        self.assertEqual(ctx.default_scheme("admin"), "md5_crypt")

    def test_24_vary_rounds(self):
        """test 'vary_rounds' hash option parsing"""
        def parse(v):
            return CryptContext(all__vary_rounds=v).to_dict()['all__vary_rounds']

        # floats should be preserved
        self.assertEqual(parse(0.1), 0.1)
        self.assertEqual(parse('0.1'), 0.1)

        # 'xx%' should be converted to float
        self.assertEqual(parse('10%'), 0.1)

        # ints should be preserved
        self.assertEqual(parse(1000), 1000)
        self.assertEqual(parse('1000'), 1000)

    #===================================================================
    # inspection & serialization
    #===================================================================
    def test_30_schemes(self):
        """test schemes() method"""
        # NOTE: also checked under test_21

        # test empty
        ctx = CryptContext()
        self.assertEqual(ctx.schemes(), ())
        self.assertEqual(ctx.schemes(resolve=True), ())

        # test sample 1
        ctx = CryptContext(**self.sample_1_dict)
        self.assertEqual(ctx.schemes(), tuple(self.sample_1_schemes))
        self.assertEqual(ctx.schemes(resolve=True), tuple(self.sample_1_handlers))

        # test sample 2
        ctx = CryptContext(**self.sample_2_dict)
        self.assertEqual(ctx.schemes(), ())

    def test_31_default_scheme(self):
        """test default_scheme() method"""
        # NOTE: also checked under test_23

        # test empty
        ctx = CryptContext()
        self.assertRaises(KeyError, ctx.default_scheme)

        # test sample 1
        ctx = CryptContext(**self.sample_1_dict)
        self.assertEqual(ctx.default_scheme(), "md5_crypt")
        self.assertEqual(ctx.default_scheme(resolve=True), hash.md5_crypt)

        # test sample 2
        ctx = CryptContext(**self.sample_2_dict)
        self.assertRaises(KeyError, ctx.default_scheme)

        # test defaults to first in scheme
        ctx = CryptContext(schemes=self.sample_1_schemes)
        self.assertEqual(ctx.default_scheme(), "des_crypt")

        # categories tested under test_23

    def test_32_handler(self):
        """test handler() method"""

        # default for empty
        ctx = CryptContext()
        self.assertRaises(KeyError, ctx.handler)
        self.assertRaises(KeyError, ctx.handler, "md5_crypt")

        # default for sample 1
        ctx = CryptContext(**self.sample_1_dict)
        self.assertEqual(ctx.handler(), hash.md5_crypt)

        # by name
        self.assertEqual(ctx.handler("des_crypt"), hash.des_crypt)

        # name not in schemes
        self.assertRaises(KeyError, ctx.handler, "mysql323")

        # check handler() honors category default
        ctx = CryptContext("sha256_crypt,md5_crypt", admin__context__default="md5_crypt")
        self.assertEqual(ctx.handler(), hash.sha256_crypt)
        self.assertEqual(ctx.handler(category="staff"), hash.sha256_crypt)
        self.assertEqual(ctx.handler(category="admin"), hash.md5_crypt)

        # test unicode category strings are accepted under py2
        if PY2:
            self.assertEqual(ctx.handler(category=u("staff")), hash.sha256_crypt)
            self.assertEqual(ctx.handler(category=u("admin")), hash.md5_crypt)

    def test_33_options(self):
        """test internal _get_record_options() method"""
        def options(ctx, scheme, category=None):
            return ctx._config._get_record_options_with_flag(scheme, category)[0]

        # this checks that (3 schemes, 3 categories) inherit options correctly.
        # the 'user' category is not present in the options.
        cc4 = CryptContext(
            schemes = [ "sha512_crypt", "des_crypt", "bsdi_crypt"],
            deprecated = ["sha512_crypt", "des_crypt"],
            all__vary_rounds = 0.1,
            bsdi_crypt__vary_rounds=0.2,
            sha512_crypt__max_rounds = 20000,
            admin__context__deprecated = [ "des_crypt", "bsdi_crypt" ],
            admin__all__vary_rounds = 0.05,
            admin__bsdi_crypt__vary_rounds=0.3,
            admin__sha512_crypt__max_rounds = 40000,
        )
        self.assertEqual(cc4._config.categories, ("admin",))

        #
        # sha512_crypt
        #
        self.assertEqual(options(cc4, "sha512_crypt"), dict(
            deprecated=True,
            vary_rounds=0.1, # inherited from all__
            max_rounds=20000,
        ))

        self.assertEqual(options(cc4, "sha512_crypt", "user"), dict(
            deprecated=True, # unconfigured category inherits from default
            vary_rounds=0.1,
            max_rounds=20000,
        ))

        self.assertEqual(options(cc4, "sha512_crypt", "admin"), dict(
            # NOT deprecated - context option overridden per-category
            vary_rounds=0.05, # global overridden per-cateogry
            max_rounds=40000, # overridden per-category
        ))

        #
        # des_crypt
        #
        self.assertEqual(options(cc4, "des_crypt"), dict(
            deprecated=True,
            vary_rounds=0.1,
        ))

        self.assertEqual(options(cc4, "des_crypt", "user"), dict(
            deprecated=True, # unconfigured category inherits from default
            vary_rounds=0.1,
        ))

        self.assertEqual(options(cc4, "des_crypt", "admin"), dict(
            deprecated=True, # unchanged though overidden
            vary_rounds=0.05, # global overridden per-cateogry
        ))

        #
        # bsdi_crypt
        #
        self.assertEqual(options(cc4, "bsdi_crypt"), dict(
            vary_rounds=0.2, # overridden from all__vary_rounds
        ))

        self.assertEqual(options(cc4, "bsdi_crypt", "user"), dict(
            vary_rounds=0.2, # unconfigured category inherits from default
        ))

        self.assertEqual(options(cc4, "bsdi_crypt", "admin"), dict(
            vary_rounds=0.3,
            deprecated=True, # deprecation set per-category
        ))

    def test_34_to_dict(self):
        """test to_dict() method"""
        # NOTE: this is tested all throughout this test case.
        ctx = CryptContext(**self.sample_1_dict)
        self.assertEqual(ctx.to_dict(), self.sample_1_dict)
        self.assertEqual(ctx.to_dict(resolve=True), self.sample_1_resolved_dict)

    def test_35_to_string(self):
        """test to_string() method"""

        # create ctx and serialize
        ctx = CryptContext(**self.sample_1_dict)
        dump = ctx.to_string()

        # check ctx->string returns canonical format.
        # NOTE: ConfigParser for PY26 and earlier didn't use OrderedDict,
        # so to_string() won't get order correct.
        # so we skip this test.
        import sys
        if sys.version_info >= (2,7):
            self.assertEqual(dump, self.sample_1_unicode)

        # check ctx->string->ctx->dict returns original
        ctx2 = CryptContext.from_string(dump)
        self.assertEqual(ctx2.to_dict(), self.sample_1_dict)

        # test section kwd is honored
        other = ctx.to_string(section="password-security")
        self.assertEqual(other, dump.replace("[passlib]","[password-security]"))

        # test unmanaged handler warning
        from passlib.tests.test_utils_handlers import UnsaltedHash
        ctx3 = CryptContext([UnsaltedHash, "md5_crypt"])
        dump = ctx3.to_string()
        self.assertRegex(dump, r"# NOTE: the 'unsalted_test_hash' handler\(s\)"
                               r" are not registered with Passlib")

    #===================================================================
    # password hash api
    #===================================================================
    nonstring_vectors =  [
        (None, {}),
        (None, {"scheme": "des_crypt"}),
        (1, {}),
        ((), {}),
        ]

    def test_40_basic(self):
        """test basic encrypt/identify/verify functionality"""
        handlers = [hash.md5_crypt, hash.des_crypt, hash.bsdi_crypt]
        cc = CryptContext(handlers, bsdi_crypt__default_rounds=5)

        # run through handlers
        for crypt in handlers:
            h = cc.encrypt("test", scheme=crypt.name)
            self.assertEqual(cc.identify(h), crypt.name)
            self.assertEqual(cc.identify(h, resolve=True), crypt)
            self.assertTrue(cc.verify('test', h))
            self.assertFalse(cc.verify('notest', h))

        # test default
        h = cc.encrypt("test")
        self.assertEqual(cc.identify(h), "md5_crypt")

        # test genhash
        h = cc.genhash('secret', cc.genconfig())
        self.assertEqual(cc.identify(h), 'md5_crypt')

        h = cc.genhash('secret', cc.genconfig(), scheme='md5_crypt')
        self.assertEqual(cc.identify(h), 'md5_crypt')

        self.assertRaises(ValueError, cc.genhash, 'secret', cc.genconfig(), scheme="des_crypt")

    def test_41_genconfig(self):
        """test genconfig() method"""
        cc = CryptContext(schemes=["md5_crypt", "phpass"],
                          phpass__ident="H",
                          phpass__default_rounds=7,
                          admin__phpass__ident="P",
                         )

        # uses default scheme
        self.assertTrue(cc.genconfig().startswith("$1$"))

        # override scheme
        self.assertTrue(cc.genconfig(scheme="phpass").startswith("$H$5"))

        # category override
        self.assertTrue(cc.genconfig(scheme="phpass", category="admin").startswith("$P$5"))
        self.assertTrue(cc.genconfig(scheme="phpass", category="staff").startswith("$H$5"))

        # override scheme & custom settings
        self.assertEqual(
            cc.genconfig(scheme="phpass", salt='.'*8, rounds=8, ident='P'),
            '$P$6........',
            )

        #--------------------------------------------------------------
        # border cases
        #--------------------------------------------------------------

        # test unicode category strings are accepted under py2
        # this tests basic _get_record() used by encrypt/genhash/verify.
        # we have to omit scheme=xxx so codepath is tested fully
        if PY2:
            c2 = cc.copy(default="phpass")
            self.assertTrue(c2.genconfig(category=u("admin")).startswith("$P$5"))
            self.assertTrue(c2.genconfig(category=u("staff")).startswith("$H$5"))

        # throws error without schemes
        self.assertRaises(KeyError, CryptContext().genconfig)
        self.assertRaises(KeyError, CryptContext().genconfig, scheme='md5_crypt')

        # bad scheme values
        self.assertRaises(KeyError, cc.genconfig, scheme="fake") # XXX: should this be ValueError?
        self.assertRaises(TypeError, cc.genconfig, scheme=1, category='staff')
        self.assertRaises(TypeError, cc.genconfig, scheme=1)

        # bad category values
        self.assertRaises(TypeError, cc.genconfig, category=1)


    def test_42_genhash(self):
        """test genhash() method"""

        #--------------------------------------------------------------
        # border cases
        #--------------------------------------------------------------

        # rejects non-string secrets
        cc = CryptContext(["des_crypt"])
        hash = cc.encrypt('stub')
        for secret, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.genhash, secret, hash, **kwds)

        # rejects non-string hashes
        cc = CryptContext(["des_crypt"])
        for hash, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.genhash, 'secret', hash, **kwds)

        # .. but should accept None if default scheme lacks config string
        cc = CryptContext(["mysql323"])
        self.assertIsInstance(cc.genhash("stub", None), str)

        # throws error without schemes
        self.assertRaises(KeyError, CryptContext().genhash, 'secret', 'hash')

        # bad scheme values
        self.assertRaises(KeyError, cc.genhash, 'secret', hash, scheme="fake") # XXX: should this be ValueError?
        self.assertRaises(TypeError, cc.genhash, 'secret', hash, scheme=1)

        # bad category values
        self.assertRaises(TypeError, cc.genconfig, 'secret', hash, category=1)


    def test_43_encrypt(self):
        """test encrypt() method"""
        cc = CryptContext(**self.sample_4_dict)

        # hash specific settings
        self.assertEqual(
            cc.encrypt("password", scheme="phpass", salt='.'*8),
            '$H$5........De04R5Egz0aq8Tf.1eVhY/',
            )
        self.assertEqual(
            cc.encrypt("password", scheme="phpass", salt='.'*8, ident="P"),
            '$P$5........De04R5Egz0aq8Tf.1eVhY/',
            )

        # NOTE: more thorough job of rounds limits done below.

        # min rounds
        with self.assertWarningList(PasslibConfigWarning):
            self.assertEqual(
                cc.encrypt("password", rounds=1999, salt="nacl"),
                '$5$rounds=2000$nacl$9/lTZ5nrfPuz8vphznnmHuDGFuvjSNvOEDsGmGfsS97',
                )

        with self.assertWarningList([]):
            self.assertEqual(
                cc.encrypt("password", rounds=2001, salt="nacl"),
                '$5$rounds=2001$nacl$8PdeoPL4aXQnJ0woHhqgIw/efyfCKC2WHneOpnvF.31'
                )

        # NOTE: max rounds, etc tested in genconfig()

        # make default > max throws error if attempted
        self.assertRaises(ValueError, cc.copy,
                          sha256_crypt__default_rounds=4000)

        #--------------------------------------------------------------
        # border cases
        #--------------------------------------------------------------

        # rejects non-string secrets
        cc = CryptContext(["des_crypt"])
        for secret, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.encrypt, secret, **kwds)

        # throws error without schemes
        self.assertRaises(KeyError, CryptContext().encrypt, 'secret')

        # bad scheme values
        self.assertRaises(KeyError, cc.encrypt, 'secret', scheme="fake") # XXX: should this be ValueError?
        self.assertRaises(TypeError, cc.encrypt, 'secret', scheme=1)

        # bad category values
        self.assertRaises(TypeError, cc.encrypt, 'secret', category=1)


    def test_44_identify(self):
        """test identify() border cases"""
        handlers = ["md5_crypt", "des_crypt", "bsdi_crypt"]
        cc = CryptContext(handlers, bsdi_crypt__default_rounds=5)

        # check unknown hash
        self.assertEqual(cc.identify('$9$232323123$1287319827'), None)
        self.assertRaises(ValueError, cc.identify, '$9$232323123$1287319827', required=True)

        #--------------------------------------------------------------
        # border cases
        #--------------------------------------------------------------

        # rejects non-string hashes
        cc = CryptContext(["des_crypt"])
        for hash, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.identify, hash, **kwds)

        # throws error without schemes
        cc = CryptContext()
        self.assertIs(cc.identify('hash'), None)
        self.assertRaises(KeyError, cc.identify, 'hash', required=True)

        # bad category values
        self.assertRaises(TypeError, cc.identify, None, category=1)

    def test_45_verify(self):
        """test verify() scheme kwd"""
        handlers = ["md5_crypt", "des_crypt", "bsdi_crypt"]
        cc = CryptContext(handlers, bsdi_crypt__default_rounds=5)

        h = hash.md5_crypt.encrypt("test")

        # check base verify
        self.assertTrue(cc.verify("test", h))
        self.assertTrue(not cc.verify("notest", h))

        # check verify using right alg
        self.assertTrue(cc.verify('test', h, scheme='md5_crypt'))
        self.assertTrue(not cc.verify('notest', h, scheme='md5_crypt'))

        # check verify using wrong alg
        self.assertRaises(ValueError, cc.verify, 'test', h, scheme='bsdi_crypt')

        #--------------------------------------------------------------
        # border cases
        #--------------------------------------------------------------

        # unknown hash should throw error
        self.assertRaises(ValueError, cc.verify, 'stub', '$6$232323123$1287319827')

        # rejects non-string secrets
        cc = CryptContext(["des_crypt"])
        h = refhash = cc.encrypt('stub')
        for secret, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.verify, secret, h, **kwds)

        # rejects non-string hashes
        cc = CryptContext(["des_crypt"])
        for h, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.verify, 'secret', h, **kwds)

        # throws error without schemes
        self.assertRaises(KeyError, CryptContext().verify, 'secret', 'hash')

        # bad scheme values
        self.assertRaises(KeyError, cc.verify, 'secret', refhash, scheme="fake") # XXX: should this be ValueError?
        self.assertRaises(TypeError, cc.verify, 'secret', refhash, scheme=1)

        # bad category values
        self.assertRaises(TypeError, cc.verify, 'secret', refhash, category=1)

    def test_46_needs_update(self):
        """test needs_update() method"""
        cc = CryptContext(**self.sample_4_dict)

        # check deprecated scheme
        self.assertTrue(cc.needs_update('9XXD4trGYeGJA'))
        self.assertFalse(cc.needs_update('$1$J8HC2RCr$HcmM.7NxB2weSvlw2FgzU0'))

        # check min rounds
        self.assertTrue(cc.needs_update('$5$rounds=1999$jD81UCoo.zI.UETs$Y7qSTQ6mTiU9qZB4fRr43wRgQq4V.5AAf7F97Pzxey/'))
        self.assertFalse(cc.needs_update('$5$rounds=2000$228SSRje04cnNCaQ$YGV4RYu.5sNiBvorQDlO0WWQjyJVGKBcJXz3OtyQ2u8'))

        # check max rounds
        self.assertFalse(cc.needs_update('$5$rounds=3000$fS9iazEwTKi7QPW4$VasgBC8FqlOvD7x2HhABaMXCTh9jwHclPA9j5YQdns.'))
        self.assertTrue(cc.needs_update('$5$rounds=3001$QlFHHifXvpFX4PLs$/0ekt7lSs/lOikSerQ0M/1porEHxYq7W/2hdFpxA3fA'))

        #--------------------------------------------------------------
        # test _bind_needs_update() framework
        #--------------------------------------------------------------
        bind_state = []
        check_state = []
        class dummy(uh.StaticHandler):
            name = 'dummy'
            _hash_prefix = '@'

            @classmethod
            def _bind_needs_update(cls, **settings):
                bind_state.append(settings)
                return cls._needs_update

            @classmethod
            def _needs_update(cls, hash, secret):
                check_state.append((hash,secret))
                return secret == "nu"

            def _calc_checksum(self, secret):
                from hashlib import md5
                if isinstance(secret, unicode):
                    secret = secret.encode("utf-8")
                return str_to_uascii(md5(secret).hexdigest())

        # creating context should call bind function w/ settings
        ctx = CryptContext([dummy])
        self.assertEqual(bind_state, [{}])

        # calling needs_update should query callback
        hash = refhash = dummy.encrypt("test")
        self.assertFalse(ctx.needs_update(hash))
        self.assertEqual(check_state, [(hash,None)])
        del check_state[:]

        # now with a password
        self.assertFalse(ctx.needs_update(hash, secret='bob'))
        self.assertEqual(check_state, [(hash,'bob')])
        del check_state[:]

        # now when it returns True
        self.assertTrue(ctx.needs_update(hash, secret='nu'))
        self.assertEqual(check_state, [(hash,'nu')])
        del check_state[:]

        #--------------------------------------------------------------
        # border cases
        #--------------------------------------------------------------

        # rejects non-string hashes
        cc = CryptContext(["des_crypt"])
        for hash, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.needs_update, hash, **kwds)

        # throws error without schemes
        self.assertRaises(KeyError, CryptContext().needs_update, 'hash')

        # bad scheme values
        self.assertRaises(KeyError, cc.needs_update, refhash, scheme="fake") # XXX: should this be ValueError?
        self.assertRaises(TypeError, cc.needs_update, refhash, scheme=1)

        # bad category values
        self.assertRaises(TypeError, cc.needs_update, refhash, category=1)

    def test_47_verify_and_update(self):
        """test verify_and_update()"""
        cc = CryptContext(**self.sample_4_dict)

        # create some hashes
        h1 = cc.encrypt("password", scheme="des_crypt")
        h2 = cc.encrypt("password", scheme="sha256_crypt")

        # check bad password, deprecated hash
        ok, new_hash = cc.verify_and_update("wrongpass", h1)
        self.assertFalse(ok)
        self.assertIs(new_hash, None)

        # check bad password, good hash
        ok, new_hash = cc.verify_and_update("wrongpass", h2)
        self.assertFalse(ok)
        self.assertIs(new_hash, None)

        # check right password, deprecated hash
        ok, new_hash = cc.verify_and_update("password", h1)
        self.assertTrue(ok)
        self.assertTrue(cc.identify(new_hash), "sha256_crypt")

        # check right password, good hash
        ok, new_hash = cc.verify_and_update("password", h2)
        self.assertTrue(ok)
        self.assertIs(new_hash, None)

        #--------------------------------------------------------------
        # border cases
        #--------------------------------------------------------------

        # rejects non-string secrets
        cc = CryptContext(["des_crypt"])
        hash = refhash = cc.encrypt('stub')
        for secret, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.verify_and_update, secret, hash, **kwds)

        # rejects non-string hashes
        cc = CryptContext(["des_crypt"])
        for hash, kwds in self.nonstring_vectors:
            self.assertRaises(TypeError, cc.verify_and_update, 'secret', hash, **kwds)

        # throws error without schemes
        self.assertRaises(KeyError, CryptContext().verify_and_update, 'secret', 'hash')

        # bad scheme values
        self.assertRaises(KeyError, cc.verify_and_update, 'secret', refhash, scheme="fake") # XXX: should this be ValueError?
        self.assertRaises(TypeError, cc.verify_and_update, 'secret', refhash, scheme=1)

        # bad category values
        self.assertRaises(TypeError, cc.verify_and_update, 'secret', refhash, category=1)

    #===================================================================
    # rounds options
    #===================================================================
    # NOTE: the follow tests check how _CryptRecord handles
    # the min/max/default/vary_rounds options, via the output of
    # genconfig(). it's assumed encrypt() takes the same codepath.

    def test_50_rounds_limits(self):
        """test rounds limits"""
        cc = CryptContext(schemes=["sha256_crypt"],
                          all__min_rounds=2000,
                          all__max_rounds=3000,
                          all__default_rounds=2500,
                          )

        #--------------------------------------------------
        # min_rounds
        #--------------------------------------------------

        # set below handler minimum
        with self.assertWarningList([PasslibConfigWarning]*2):
            c2 = cc.copy(all__min_rounds=500, all__max_rounds=None,
                            all__default_rounds=500)
        self.assertEqual(c2.genconfig(salt="nacl"), "$5$rounds=1000$nacl$")

        # below policy minimum
        with self.assertWarningList(PasslibConfigWarning):
            self.assertEqual(
                cc.genconfig(rounds=1999, salt="nacl"),
                '$5$rounds=2000$nacl$',
                )

        # equal to policy minimum
        self.assertEqual(
            cc.genconfig(rounds=2000, salt="nacl"),
            '$5$rounds=2000$nacl$',
            )

        # above policy minimum
        self.assertEqual(
            cc.genconfig(rounds=2001, salt="nacl"),
            '$5$rounds=2001$nacl$'
            )

        #--------------------------------------------------
        # max rounds
        #--------------------------------------------------

        # set above handler max
        with self.assertWarningList([PasslibConfigWarning]*2):
            c2 = cc.copy(all__max_rounds=int(1e9)+500, all__min_rounds=None,
                            all__default_rounds=int(1e9)+500)

        self.assertEqual(c2.genconfig(salt="nacl"),
                         "$5$rounds=999999999$nacl$")

        # above policy max
        with self.assertWarningList(PasslibConfigWarning):
            self.assertEqual(
                cc.genconfig(rounds=3001, salt="nacl"),
                '$5$rounds=3000$nacl$'
                )

        # equal policy max
        self.assertEqual(
            cc.genconfig(rounds=3000, salt="nacl"),
            '$5$rounds=3000$nacl$'
            )

        # below policy max
        self.assertEqual(
            cc.genconfig(rounds=2999, salt="nacl"),
            '$5$rounds=2999$nacl$',
            )

        #--------------------------------------------------
        # default_rounds
        #--------------------------------------------------

        # explicit default rounds
        self.assertEqual(cc.genconfig(salt="nacl"), '$5$rounds=2500$nacl$')

        # fallback default rounds - use handler's
        df = hash.sha256_crypt.default_rounds
        c2 = cc.copy(all__default_rounds=None, all__max_rounds=df<<1)
        self.assertEqual(c2.genconfig(salt="nacl"),
                         '$5$rounds=%d$nacl$' % df)

        # fallback default rounds - use handler's, but clipped to max rounds
        c2 = cc.copy(all__default_rounds=None, all__max_rounds=3000)
        self.assertEqual(c2.genconfig(salt="nacl"), '$5$rounds=3000$nacl$')

        # TODO: test default falls back to mx / mn if handler has no default.

        # default rounds - out of bounds
        self.assertRaises(ValueError, cc.copy, all__default_rounds=1999)
        cc.copy(all__default_rounds=2000)
        cc.copy(all__default_rounds=3000)
        self.assertRaises(ValueError, cc.copy, all__default_rounds=3001)

        #--------------------------------------------------
        # border cases
        #--------------------------------------------------

        # invalid min/max bounds
        c2 = CryptContext(schemes=["sha256_crypt"])
        self.assertRaises(ValueError, c2.copy, all__min_rounds=-1)
        self.assertRaises(ValueError, c2.copy, all__max_rounds=-1)
        self.assertRaises(ValueError, c2.copy, all__min_rounds=2000,
                          all__max_rounds=1999)

        # test bad values
        self.assertRaises(ValueError, CryptContext, all__min_rounds='x')
        self.assertRaises(ValueError, CryptContext, all__max_rounds='x')
        self.assertRaises(ValueError, CryptContext, all__vary_rounds='x')
        self.assertRaises(ValueError, CryptContext, all__default_rounds='x')

        # test bad types rejected
        bad = NotImplemented
        self.assertRaises(TypeError, CryptContext, "sha256_crypt", all__min_rounds=bad)
        self.assertRaises(TypeError, CryptContext, "sha256_crypt", all__max_rounds=bad)
        self.assertRaises(TypeError, CryptContext, "sha256_crypt", all__vary_rounds=bad)
        self.assertRaises(TypeError, CryptContext, "sha256_crypt", all__default_rounds=bad)

    def test_51_linear_vary_rounds(self):
        """test linear vary rounds"""
        cc = CryptContext(schemes=["sha256_crypt"],
                          all__min_rounds=1995,
                          all__max_rounds=2005,
                          all__default_rounds=2000,
                          )

        # test negative
        self.assertRaises(ValueError, cc.copy, all__vary_rounds=-1)
        self.assertRaises(ValueError, cc.copy, all__vary_rounds="-1%")
        self.assertRaises(ValueError, cc.copy, all__vary_rounds="101%")

        # test static
        c2 = cc.copy(all__vary_rounds=0)
        self.assert_rounds_range(c2, "sha256_crypt", 2000, 2000)

        c2 = cc.copy(all__vary_rounds="0%")
        self.assert_rounds_range(c2, "sha256_crypt", 2000, 2000)

        # test absolute
        c2 = cc.copy(all__vary_rounds=1)
        self.assert_rounds_range(c2, "sha256_crypt", 1999, 2001)
        c2 = cc.copy(all__vary_rounds=100)
        self.assert_rounds_range(c2, "sha256_crypt", 1995, 2005)

        # test relative
        c2 = cc.copy(all__vary_rounds="0.1%")
        self.assert_rounds_range(c2, "sha256_crypt", 1998, 2002)
        c2 = cc.copy(all__vary_rounds="100%")
        self.assert_rounds_range(c2, "sha256_crypt", 1995, 2005)

    def test_52_log2_vary_rounds(self):
        """test log2 vary rounds"""
        cc = CryptContext(schemes=["bcrypt"],
                          all__min_rounds=15,
                          all__max_rounds=25,
                          all__default_rounds=20,
                          )

        # test negative
        self.assertRaises(ValueError, cc.copy, all__vary_rounds=-1)
        self.assertRaises(ValueError, cc.copy, all__vary_rounds="-1%")
        self.assertRaises(ValueError, cc.copy, all__vary_rounds="101%")

        # test static
        c2 = cc.copy(all__vary_rounds=0)
        self.assert_rounds_range(c2, "bcrypt", 20, 20)

        c2 = cc.copy(all__vary_rounds="0%")
        self.assert_rounds_range(c2, "bcrypt", 20, 20)

        # test absolute
        c2 = cc.copy(all__vary_rounds=1)
        self.assert_rounds_range(c2, "bcrypt", 19, 21)
        c2 = cc.copy(all__vary_rounds=100)
        self.assert_rounds_range(c2, "bcrypt", 15, 25)

        # test relative - should shift over at 50% mark
        c2 = cc.copy(all__vary_rounds="1%")
        self.assert_rounds_range(c2, "bcrypt", 20, 20)

        c2 = cc.copy(all__vary_rounds="49%")
        self.assert_rounds_range(c2, "bcrypt", 20, 20)

        c2 = cc.copy(all__vary_rounds="50%")
        self.assert_rounds_range(c2, "bcrypt", 19, 20)

        c2 = cc.copy(all__vary_rounds="100%")
        self.assert_rounds_range(c2, "bcrypt", 15, 21)

    def assert_rounds_range(self, context, scheme, lower, upper):
        """helper to check vary_rounds covers specified range"""
        # NOTE: this runs enough times the min and max *should* be hit,
        # though there's a faint chance it will randomly fail.
        handler = context.handler(scheme)
        salt = handler.default_salt_chars[0:1] * handler.max_salt_size
        seen = set()
        for i in irange(300):
            h = context.genconfig(scheme, salt=salt)
            r = handler.from_string(h).rounds
            seen.add(r)
        self.assertEqual(min(seen), lower, "vary_rounds had wrong lower limit:")
        self.assertEqual(max(seen), upper, "vary_rounds had wrong upper limit:")

    #===================================================================
    # feature tests
    #===================================================================
    def test_60_min_verify_time(self):
        """test verify() honors min_verify_time"""
        delta = .05
        if TICK_RESOLUTION >= delta/10:
            raise self.skipTest("timer not accurate enough")
        min_delay = 2*delta
        min_verify_time = 5*delta
        max_delay = 8*delta

        class TimedHash(uh.StaticHandler):
            """psuedo hash that takes specified amount of time"""
            name = "timed_hash"
            delay = 0

            @classmethod
            def identify(cls, hash):
                return True

            def _calc_checksum(self, secret):
                quicksleep(self.delay)
                return to_unicode(secret + 'x')

        # check mvt issues a warning, and then filter for remainder of test
        with self.assertWarningList(["'min_verify_time' is deprecated"]*2):
            cc = CryptContext([TimedHash], min_verify_time=min_verify_time,
                admin__context__min_verify_time=min_verify_time*2)
        warnings.filterwarnings("ignore", "'min_verify_time' is deprecated")

        def timecall(func, *args, **kwds):
            start = tick()
            result = func(*args, **kwds)
            return tick()-start, result

        # verify genhash delay works
        TimedHash.delay = min_delay
        elapsed, result = timecall(TimedHash.genhash, 'stub', None)
        self.assertEqual(result, 'stubx')
        self.assertAlmostEqual(elapsed, min_delay, delta=delta)

        # ensure min verify time is honored

            # correct password
        elapsed, result = timecall(cc.verify, "stub", "stubx")
        self.assertTrue(result)
        self.assertAlmostEqual(elapsed, min_delay, delta=delta)

            # incorrect password
        elapsed, result = timecall(cc.verify, "blob", "stubx")
        self.assertFalse(result)
        self.assertAlmostEqual(elapsed, min_verify_time, delta=delta)

            # incorrect password w/ special category setting
        elapsed, result = timecall(cc.verify, "blob", "stubx", category="admin")
        self.assertFalse(result)
        self.assertAlmostEqual(elapsed, min_verify_time*2, delta=delta)

        # ensure taking longer emits a warning.
        TimedHash.delay = max_delay
        with self.assertWarningList(".*verify exceeded min_verify_time"):
            elapsed, result = timecall(cc.verify, "blob", "stubx")
        self.assertFalse(result)
        self.assertAlmostEqual(elapsed, max_delay, delta=delta)

        # reject values < 0
        self.assertRaises(ValueError, CryptContext, min_verify_time=-1)

    def test_61_autodeprecate(self):
        """test deprecated='auto' is handled correctly"""

        def getstate(ctx, category=None):
            return [ctx._is_deprecated_scheme(scheme, category) for scheme in ctx.schemes()]

        # correctly reports default
        ctx = CryptContext("sha256_crypt,md5_crypt,des_crypt", deprecated="auto")
        self.assertEqual(getstate(ctx,    None), [False, True, True])
        self.assertEqual(getstate(ctx, "admin"), [False, True, True])

        # correctly reports changed default
        ctx.update(default="md5_crypt")
        self.assertEqual(getstate(ctx,    None), [True, False, True])
        self.assertEqual(getstate(ctx, "admin"), [True, False, True])

        # category default is handled correctly
        ctx.update(admin__context__default="des_crypt")
        self.assertEqual(getstate(ctx,    None), [True, False, True])
        self.assertEqual(getstate(ctx, "admin"), [True, True, False])

        # handles 1 scheme
        ctx = CryptContext(["sha256_crypt"], deprecated="auto")
        self.assertEqual(getstate(ctx,    None), [False])
        self.assertEqual(getstate(ctx, "admin"), [False])

        # disallow auto & other deprecated schemes at same time.
        self.assertRaises(ValueError, CryptContext, "sha256_crypt,md5_crypt",
                          deprecated="auto,md5_crypt")
        self.assertRaises(ValueError, CryptContext, "sha256_crypt,md5_crypt",
                          deprecated="md5_crypt,auto")

    #===================================================================
    # handler deprecation detectors
    #===================================================================
    def test_62_bcrypt_update(self):
        """test verify_and_update / needs_update corrects bcrypt padding"""
        # see issue 25.
        bcrypt = hash.bcrypt

        PASS1 = "test"
        BAD1 = "$2a$04$yjDgE74RJkeqC0/1NheSScrvKeu9IbKDpcQf/Ox3qsrRS/Kw42qIS"
        GOOD1 = "$2a$04$yjDgE74RJkeqC0/1NheSSOrvKeu9IbKDpcQf/Ox3qsrRS/Kw42qIS"
        ctx = CryptContext(["bcrypt"], bcrypt__rounds=4)

        self.assertTrue(ctx.needs_update(BAD1))
        self.assertFalse(ctx.needs_update(GOOD1))

        if bcrypt.has_backend():
            self.assertEqual(ctx.verify_and_update(PASS1,GOOD1), (True,None))
            with self.assertWarningList(["incorrect.*padding bits"]*2):
                self.assertEqual(ctx.verify_and_update("x",BAD1), (False,None))
                ok, new_hash = ctx.verify_and_update(PASS1, BAD1)
            self.assertTrue(ok)
            self.assertTrue(new_hash and new_hash != BAD1)

    def test_63_bsdi_crypt_update(self):
        """test verify_and_update / needs_update corrects bsdi even rounds"""
        even_hash = '_Y/../cG0zkJa6LY6k4c'
        odd_hash = '_Z/..TgFg0/ptQtpAgws'
        secret = 'test'
        ctx = CryptContext(['bsdi_crypt'], bsdi_crypt__min_rounds=5)

        self.assertTrue(ctx.needs_update(even_hash))
        self.assertFalse(ctx.needs_update(odd_hash))

        self.assertEqual(ctx.verify_and_update(secret, odd_hash), (True,None))
        self.assertEqual(ctx.verify_and_update("x", even_hash), (False,None))
        ok, new_hash = ctx.verify_and_update(secret, even_hash)
        self.assertTrue(ok)
        self.assertTrue(new_hash and new_hash != even_hash)

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# LazyCryptContext
#=============================================================================
class dummy_2(uh.StaticHandler):
    name = "dummy_2"

class LazyCryptContextTest(TestCase):
    descriptionPrefix = "LazyCryptContext"

    def setUp(self):
        # make sure this isn't registered before OR after
        unload_handler_name("dummy_2")
        self.addCleanup(unload_handler_name, "dummy_2")

    def test_kwd_constructor(self):
        """test plain kwds"""
        self.assertFalse(has_crypt_handler("dummy_2"))
        register_crypt_handler_path("dummy_2", "passlib.tests.test_context")

        cc = LazyCryptContext(iter(["dummy_2", "des_crypt"]), deprecated=["des_crypt"])

        self.assertFalse(has_crypt_handler("dummy_2", True))

        self.assertEqual(cc.schemes(), ("dummy_2", "des_crypt"))
        self.assertTrue(cc._is_deprecated_scheme("des_crypt"))

        self.assertTrue(has_crypt_handler("dummy_2", True))

    def test_callable_constructor(self):
        self.assertFalse(has_crypt_handler("dummy_2"))
        register_crypt_handler_path("dummy_2", "passlib.tests.test_context")

        def onload(flag=False):
            self.assertTrue(flag)
            return dict(schemes=iter(["dummy_2", "des_crypt"]), deprecated=["des_crypt"])

        cc = LazyCryptContext(onload=onload, flag=True)

        self.assertFalse(has_crypt_handler("dummy_2", True))

        self.assertEqual(cc.schemes(), ("dummy_2", "des_crypt"))
        self.assertTrue(cc._is_deprecated_scheme("des_crypt"))

        self.assertTrue(has_crypt_handler("dummy_2", True))

#=============================================================================
# eof
#=============================================================================
