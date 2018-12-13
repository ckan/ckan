"""helpers for passlib unittests"""
#=============================================================================
# imports
#=============================================================================
from __future__ import with_statement
# core
import logging; log = logging.getLogger(__name__)
import re
import os
import sys
import tempfile
import time
from passlib.exc import PasslibHashWarning
from passlib.utils.compat import PY27, PY_MIN_32, PY3, JYTHON
import warnings
from warnings import warn
# site
# pkg
from passlib.exc import MissingBackendError
import passlib.registry as registry
from passlib.tests.backports import TestCase as _TestCase, catch_warnings, skip, skipIf, skipUnless
from passlib.utils import has_rounds_info, has_salt_info, rounds_cost_values, \
                          classproperty, rng, getrandstr, is_ascii_safe, to_native_str, \
                          repeat_string, tick
from passlib.utils.compat import b, bytes, iteritems, irange, callable, \
                                 base_string_types, exc_err, u, unicode, PY2
import passlib.utils.handlers as uh
# local
__all__ = [
    # util funcs
    'TEST_MODE',
    'set_file', 'get_file',

    # unit testing
    'TestCase',
    'HandlerCase',
]

#=============================================================================
# environment detection
#=============================================================================
# figure out if we're running under GAE;
# some tests (e.g. FS writing) should be skipped.
# XXX: is there better way to do this?
try:
    import google.appengine
except ImportError:
    GAE = False
else:
    GAE = True

def ensure_mtime_changed(path):
    """ensure file's mtime has changed"""
    # NOTE: this is hack to deal w/ filesystems whose mtime resolution is >= 1s,
    #       when a test needs to be sure the mtime changed after writing to the file.
    last = os.path.getmtime(path)
    while os.path.getmtime(path) == last:
        time.sleep(0.1)
        os.utime(path, None)

def _get_timer_resolution(timer):
    def sample():
        start = cur = timer()
        while start == cur:
            cur = timer()
        return cur-start
    return min(sample() for _ in range(3))
TICK_RESOLUTION = _get_timer_resolution(tick)

#=============================================================================
# test mode
#=============================================================================
_TEST_MODES = ["quick", "default", "full"]
_test_mode = _TEST_MODES.index(os.environ.get("PASSLIB_TEST_MODE",
                                              "default").strip().lower())

def TEST_MODE(min=None, max=None):
    """check if test for specified mode should be enabled.

    ``"quick"``
        run the bare minimum tests to ensure functionality.
        variable-cost hashes are tested at their lowest setting.
        hash algorithms are only tested against the backend that will
        be used on the current host. no fuzz testing is done.

    ``"default"``
        same as ``"quick"``, except: hash algorithms are tested
        at default levels, and a brief round of fuzz testing is done
        for each hash.

    ``"full"``
        extra regression and internal tests are enabled, hash algorithms are tested
        against all available backends, unavailable ones are mocked whre possible,
        additional time is devoted to fuzz testing.
    """
    if min and _test_mode < _TEST_MODES.index(min):
        return False
    if max and _test_mode > _TEST_MODES.index(max):
        return False
    return True

#=============================================================================
# hash object inspection
#=============================================================================
def has_crypt_support(handler):
    """check if host's crypt() supports this natively"""
    if hasattr(handler, "orig_prefix"):
        # ignore wrapper classes
        return False
    return 'os_crypt' in getattr(handler, "backends", ()) and handler.has_backend("os_crypt")

def has_relaxed_setting(handler):
    """check if handler supports 'relaxed' kwd"""
    # FIXME: I've been lazy, should probably just add 'relaxed' kwd
    # to all handlers that derive from GenericHandler

    # ignore wrapper classes for now.. though could introspec.
    if hasattr(handler, "orig_prefix"):
        return False

    return 'relaxed' in handler.setting_kwds or issubclass(handler,
                                                           uh.GenericHandler)

def has_active_backend(handler):
    """return active backend for handler, if any"""
    if not hasattr(handler, "get_backend"):
        return "builtin"
    try:
        return handler.get_backend()
    except MissingBackendError:
        return None

def is_default_backend(handler, backend):
    """check if backend is the default for source"""
    try:
        orig = handler.get_backend()
    except MissingBackendError:
        return False
    try:
        return handler.set_backend("default") == backend
    finally:
        handler.set_backend(orig)

class temporary_backend(object):
    """
    temporarily set handler to specific backend
    """

    _orig = None

    def __init__(self, handler, backend=None):
        self.handler = handler
        self.backend = backend

    def __enter__(self):
        orig = self._orig = self.handler.get_backend()
        if self.backend:
            self.handler.set_backend(self.backend)
        return orig

    def __exit__(self, *exc_info):
        self.handler.set_backend(self._orig)

#=============================================================================
# misc helpers
#=============================================================================
def set_file(path, content):
    """set file to specified bytes"""
    if isinstance(content, unicode):
        content = content.encode("utf-8")
    with open(path, "wb") as fh:
        fh.write(content)

def get_file(path):
    """read file as bytes"""
    with open(path, "rb") as fh:
        return fh.read()

def tonn(source):
    """convert native string to non-native string"""
    if not isinstance(source, str):
        return source
    elif PY3:
        return source.encode("utf-8")
    else:
        try:
            return source.decode("utf-8")
        except UnicodeDecodeError:
            return source.decode("latin-1")

def limit(value, lower, upper):
    if value < lower:
        return lower
    elif value > upper:
        return upper
    return value

def randintgauss(lower, upper, mu, sigma):
    """hack used by fuzz testing"""
    return int(limit(rng.normalvariate(mu, sigma), lower, upper))

def quicksleep(delay):
    """because time.sleep() doesn't even have 10ms accuracy on some OSes"""
    start = tick()
    while tick()-start < delay:
        pass

#=============================================================================
# custom test harness
#=============================================================================

def patchAttr(test, obj, attr, value):
    """monkeypatch object value, restoring original on cleanup"""
    try:
        orig = getattr(obj, attr)
    except AttributeError:
        def cleanup():
            try:
                delattr(obj, attr)
            except AttributeError:
                pass
        test.addCleanup(cleanup)
    else:
        test.addCleanup(setattr, obj, attr, orig)
    setattr(obj, attr, value)

class TestCase(_TestCase):
    """passlib-specific test case class

    this class adds a number of features to the standard TestCase...
    * common prefix for all test descriptions
    * resets warnings filter & registry for every test
    * tweaks to message formatting
    * __msg__ kwd added to assertRaises()
    * suite of methods for matching against warnings
    """
    #===================================================================
    # add various custom features
    #===================================================================

    #---------------------------------------------------------------
    # make it easy for test cases to add common prefix to shortDescription
    #---------------------------------------------------------------

    # string prepended to all tests in TestCase
    descriptionPrefix = None

    def shortDescription(self):
        """wrap shortDescription() method to prepend descriptionPrefix"""
        desc = super(TestCase, self).shortDescription()
        prefix = self.descriptionPrefix
        if prefix:
            desc = "%s: %s" % (prefix, desc or str(self))
        return desc

    #---------------------------------------------------------------
    # hack things so nose and ut2 both skip subclasses who have
    # "__unittest_skip=True" set, or whose names start with "_"
    #---------------------------------------------------------------
    @classproperty
    def __unittest_skip__(cls):
        # NOTE: this attr is technically a unittest2 internal detail.
        name = cls.__name__
        return name.startswith("_") or \
               getattr(cls, "_%s__unittest_skip" % name, False)

        # make this mirror nose's '__test__' attr
        return not getattr(cls, "__test__", True)

    @classproperty
    def __test__(cls):
        # make nose just proxy __unittest_skip__
        return not cls.__unittest_skip__

    # flag to skip *this* class
    __unittest_skip = True

    #---------------------------------------------------------------
    # reset warning filters & registry before each test
    #---------------------------------------------------------------

    # flag to reset all warning filters & ignore state
    resetWarningState = True

    def setUp(self):
        super(TestCase, self).setUp()
        self.setUpWarnings()

    def setUpWarnings(self):
        """helper to init warning filters before subclass setUp()"""
        if self.resetWarningState:
            ctx = reset_warnings()
            ctx.__enter__()
            self.addCleanup(ctx.__exit__)

    #---------------------------------------------------------------
    # tweak message formatting so longMessage mode is only enabled
    # if msg ends with ":", and turn on longMessage by default.
    #---------------------------------------------------------------
    longMessage = True

    def _formatMessage(self, msg, std):
        if self.longMessage and msg and msg.rstrip().endswith(":"):
            return '%s %s' % (msg.rstrip(), std)
        else:
            return msg or std

    #---------------------------------------------------------------
    # override assertRaises() to support '__msg__' keyword
    #---------------------------------------------------------------
    def assertRaises(self, _exc_type, _callable=None, *args, **kwds):
        msg = kwds.pop("__msg__", None)
        if _callable is None:
            # FIXME: this ignores 'msg'
            return super(TestCase, self).assertRaises(_exc_type, None,
                                                      *args, **kwds)
        try:
            result = _callable(*args, **kwds)
        except _exc_type:
            return
        std = "function returned %r, expected it to raise %r" % (result,
                                                                 _exc_type)
        raise self.failureException(self._formatMessage(msg, std))

    #---------------------------------------------------------------
    # forbid a bunch of deprecated aliases so I stop using them
    #---------------------------------------------------------------
    def assertEquals(self, *a, **k):
        raise AssertionError("this alias is deprecated by unittest2")
    assertNotEquals = assertRegexMatches = assertEquals

    #===================================================================
    # custom methods for matching warnings
    #===================================================================
    def assertWarning(self, warning,
                             message_re=None, message=None,
                             category=None,
                             filename_re=None, filename=None,
                             lineno=None,
                             msg=None,
                             ):
        """check if warning matches specified parameters.
        'warning' is the instance of Warning to match against;
        can also be instance of WarningMessage (as returned by catch_warnings).
        """
        # check input type
        if hasattr(warning, "category"):
            # resolve WarningMessage -> Warning, but preserve original
            wmsg = warning
            warning = warning.message
        else:
            # no original WarningMessage, passed raw Warning
            wmsg = None

        # tests that can use a warning instance or WarningMessage object
        if message:
            self.assertEqual(str(warning), message, msg)
        if message_re:
            self.assertRegex(str(warning), message_re, msg)
        if category:
            self.assertIsInstance(warning, category, msg)

        # tests that require a WarningMessage object
        if filename or filename_re:
            if not wmsg:
                raise TypeError("matching on filename requires a "
                                "WarningMessage instance")
            real = wmsg.filename
            if real.endswith(".pyc") or real.endswith(".pyo"):
                # FIXME: should use a stdlib call to resolve this back
                #        to module's original filename.
                real = real[:-1]
            if filename:
                self.assertEqual(real, filename, msg)
            if filename_re:
                self.assertRegex(real, filename_re, msg)
        if lineno:
            if not wmsg:
                raise TypeError("matching on lineno requires a "
                                "WarningMessage instance")
            self.assertEqual(wmsg.lineno, lineno, msg)

    class _AssertWarningList(catch_warnings):
        """context manager for assertWarningList()"""
        def __init__(self, case, **kwds):
            self.case = case
            self.kwds = kwds
            self.__super = super(TestCase._AssertWarningList, self)
            self.__super.__init__(record=True)

        def __enter__(self):
            self.log = self.__super.__enter__()

        def __exit__(self, *exc_info):
            self.__super.__exit__(*exc_info)
            if not exc_info:
                self.case.assertWarningList(self.log, **self.kwds)

    def assertWarningList(self, wlist=None, desc=None, msg=None):
        """check that warning list (e.g. from catch_warnings) matches pattern"""
        if desc is None:
            assert wlist is not None
            return self._AssertWarningList(self, desc=wlist, msg=msg)
        # TODO: make this display better diff of *which* warnings did not match
        assert desc is not None
        if not isinstance(desc, (list,tuple)):
            desc = [desc]
        for idx, entry in enumerate(desc):
            if isinstance(entry, str):
                entry = dict(message_re=entry)
            elif isinstance(entry, type) and issubclass(entry, Warning):
                entry = dict(category=entry)
            elif not isinstance(entry, dict):
                raise TypeError("entry must be str, warning, or dict")
            try:
                data = wlist[idx]
            except IndexError:
                break
            self.assertWarning(data, msg=msg, **entry)
        else:
            if len(wlist) == len(desc):
                return
        std = "expected %d warnings, found %d: wlist=%s desc=%r" % \
                (len(desc), len(wlist), self._formatWarningList(wlist), desc)
        raise self.failureException(self._formatMessage(msg, std))

    def consumeWarningList(self, wlist, desc=None, *args, **kwds):
        """[deprecated] assertWarningList() variant that clears list afterwards"""
        if desc is None:
            desc = []
        self.assertWarningList(wlist, desc, *args, **kwds)
        del wlist[:]

    def _formatWarning(self, entry):
        tail = ""
        if hasattr(entry, "message"):
            # WarningMessage instance.
            tail = " filename=%r lineno=%r" % (entry.filename, entry.lineno)
            if entry.line:
                tail += " line=%r" % (entry.line,)
            entry = entry.message
        cls = type(entry)
        return "<%s.%s message=%r%s>" % (cls.__module__, cls.__name__,
                                           str(entry), tail)

    def _formatWarningList(self, wlist):
        return "[%s]" % ", ".join(self._formatWarning(entry) for entry in wlist)

    #===================================================================
    # capability tests
    #===================================================================
    def require_stringprep(self):
        """helper to skip test if stringprep is missing"""
        from passlib.utils import stringprep
        if not stringprep:
            from passlib.utils import _stringprep_missing_reason
            raise self.skipTest("not available - stringprep module is " +
                                _stringprep_missing_reason)

    def require_TEST_MODE(self, level):
        """skip test for all PASSLIB_TEST_MODE values below <level>"""
        if not TEST_MODE(level):
            raise self.skipTest("requires >= %r test mode" % level)

    def require_writeable_filesystem(self):
        """skip test if writeable FS not available"""
        if GAE:
            return self.skipTest("GAE doesn't offer read/write filesystem access")

    #===================================================================
    # other
    #===================================================================
    _mktemp_queue = None

    def mktemp(self, *args, **kwds):
        """create temp file that's cleaned up at end of test"""
        self.require_writeable_filesystem()
        fd, path = tempfile.mkstemp(*args, **kwds)
        os.close(fd)
        queue = self._mktemp_queue
        if queue is None:
            queue = self._mktemp_queue = []
            def cleaner():
                for path in queue:
                    if os.path.exists(path):
                        os.remove(path)
                del queue[:]
            self.addCleanup(cleaner)
        queue.append(path)
        return path

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# other unittest helpers
#=============================================================================
RESERVED_BACKEND_NAMES = ["any", "default"]

class HandlerCase(TestCase):
    """base class for testing password hash handlers (esp passlib.utils.handlers subclasses)

    In order to use this to test a handler,
    create a subclass will all the appropriate attributes
    filled as listed in the example below,
    and run the subclass via unittest.

    .. todo::

        Document all of the options HandlerCase offers.

    .. note::

        This is subclass of :class:`unittest.TestCase`
        (or :class:`unittest2.TestCase` if available).
    """
    #===================================================================
    # class attrs - should be filled in by subclass
    #===================================================================

    #---------------------------------------------------------------
    # handler setup
    #---------------------------------------------------------------

    # handler class to test [required]
    handler = None

    # if set, run tests against specified backend
    backend = None

    #---------------------------------------------------------------
    # test vectors
    #---------------------------------------------------------------

    # list of (secret, hash) tuples which are known to be correct
    known_correct_hashes = []

    # list of (config, secret, hash) tuples are known to be correct
    known_correct_configs = []

    # list of (alt_hash, secret, hash) tuples, where alt_hash is a hash
    # using an alternate representation that should be recognized and verify
    # correctly, but should be corrected to match hash when passed through
    # genhash()
    known_alternate_hashes = []

    # hashes so malformed they aren't even identified properly
    known_unidentified_hashes = []

    # hashes which are identifiabled but malformed - they should identify()
    # as True, but cause an error when passed to genhash/verify.
    known_malformed_hashes = []

    # list of (handler name, hash) pairs for other algorithm's hashes that
    # handler shouldn't identify as belonging to it this list should generally
    # be sufficient (if handler name in list, that entry will be skipped)
    known_other_hashes = [
        ('des_crypt', '6f8c114b58f2c'),
        ('md5_crypt', '$1$dOHYPKoP$tnxS1T8Q6VVn3kpV8cN6o.'),
        ('sha512_crypt', "$6$rounds=123456$asaltof16chars..$BtCwjqMJGx5hrJhZywW"
         "vt0RLE8uZ4oPwcelCjmw2kSYu.Ec6ycULevoBK25fs2xXgMNrCzIMVcgEJAstJeonj1"),
    ]

    # passwords used to test basic encrypt behavior - generally
    # don't need to be overidden.
    stock_passwords = [
        u("test"),
        u("\u20AC\u00A5$"),
        b('\xe2\x82\xac\xc2\xa5$')
    ]

    #---------------------------------------------------------------
    # option flags
    #---------------------------------------------------------------

    # maximum number of chars which hash will include in digest.
    # ``None`` (the default) indicates the hash uses ALL of the password.
    secret_size = None

    # whether hash is case insensitive
    # True, False, or special value "verify-only" (which indicates
    # hash contains case-sensitive portion, but verifies is case-insensitive)
    secret_case_insensitive = False

    # flag if scheme accepts ALL hash strings (e.g. plaintext)
    accepts_all_hashes = False

    # flag indicating "disabled account" handler (e.g. unix_disabled)
    is_disabled_handler = False

    # flag/hack to filter PasslibHashWarning issued by test_72_configs()
    filter_config_warnings = False

    # forbid certain characters in passwords
    @classproperty
    def forbidden_characters(cls):
        # anything that supports crypt() interface should forbid null chars,
        # since crypt() uses null-terminated strings.
        if 'os_crypt' in getattr(cls.handler, "backends", ()):
            return b("\x00")
        return None

    #===================================================================
    # internal class attrs
    #===================================================================
    __unittest_skip = True

    @property
    def descriptionPrefix(self):
        handler = self.handler
        name = handler.name
        if hasattr(handler, "get_backend"):
            name += " (%s backend)" % (handler.get_backend(),)
        return name

    #===================================================================
    # internal instance attrs
    #===================================================================
    # indicates safe_crypt() has been patched to use another backend of handler.
    using_patched_crypt = False

    #===================================================================
    # support methods
    #===================================================================

    #---------------------------------------------------------------
    # configuration helpers
    #---------------------------------------------------------------
    @property
    def supports_config_string(self):
        return self.do_genconfig() is not None

    @classmethod
    def iter_known_hashes(cls):
        """iterate through known (secret, hash) pairs"""
        for secret, hash in cls.known_correct_hashes:
            yield secret, hash
        for config, secret, hash in cls.known_correct_configs:
            yield secret, hash
        for alt, secret, hash in cls.known_alternate_hashes:
            yield secret, hash

    def get_sample_hash(self):
        """test random sample secret/hash pair"""
        known = list(self.iter_known_hashes())
        return rng.choice(known)

    #---------------------------------------------------------------
    # test helpers
    #---------------------------------------------------------------
    def check_verify(self, secret, hash, msg=None, negate=False):
        """helper to check verify() outcome, honoring is_disabled_handler"""
        result = self.do_verify(secret, hash)
        self.assertTrue(result is True or result is False,
                        "verify() returned non-boolean value: %r" % (result,))
        if self.is_disabled_handler or negate:
            if not result:
                return
            if not msg:
                msg = ("verify incorrectly returned True: secret=%r, hash=%r" %
                       (secret, hash))
            raise self.failureException(msg)
        else:
            if result:
                return
            if not msg:
                msg = "verify failed: secret=%r, hash=%r" % (secret, hash)
            raise self.failureException(msg)

    def check_returned_native_str(self, result, func_name):
        self.assertIsInstance(result, str,
            "%s() failed to return native string: %r" % (func_name, result,))

    #---------------------------------------------------------------
    # PasswordHash helpers - wraps all calls to PasswordHash api,
    # so that subclasses can fill in defaults and account for other specialized behavior
    #---------------------------------------------------------------
    def populate_settings(self, kwds):
        """subclassable method to populate default settings"""
        # use lower rounds settings for certain test modes
        handler = self.handler
        if 'rounds' in handler.setting_kwds and 'rounds' not in kwds:
            mn = handler.min_rounds
            df = handler.default_rounds
            if TEST_MODE(max="quick"):
                # use minimum rounds for quick mode
                kwds['rounds'] = max(3, mn)
            else:
                # use default/16 otherwise
                factor = 3
                if getattr(handler, "rounds_cost", None) == "log2":
                    df -= factor
                else:
                    df //= (1<<factor)
                kwds['rounds'] = max(3, mn, df)

    def populate_context(self, secret, kwds):
        """subclassable method allowing 'secret' to be encode context kwds"""
        return secret

    def do_encrypt(self, secret, **kwds):
        """call handler's encrypt method with specified options"""
        secret = self.populate_context(secret, kwds)
        self.populate_settings(kwds)
        return self.handler.encrypt(secret, **kwds)

    def do_verify(self, secret, hash, **kwds):
        """call handler's verify method"""
        secret = self.populate_context(secret, kwds)
        return self.handler.verify(secret, hash, **kwds)

    def do_identify(self, hash):
        """call handler's identify method"""
        return self.handler.identify(hash)

    def do_genconfig(self, **kwds):
        """call handler's genconfig method with specified options"""
        self.populate_settings(kwds)
        return self.handler.genconfig(**kwds)

    def do_genhash(self, secret, config, **kwds):
        """call handler's genhash method with specified options"""
        secret = self.populate_context(secret, kwds)
        return self.handler.genhash(secret, config, **kwds)

    #---------------------------------------------------------------
    # automatically generate subclasses for testing specific backends,
    # and other backend helpers
    #---------------------------------------------------------------
    @classmethod
    def _enable_backend_case(cls, backend):
        """helper for create_backend_cases(); returns reason to skip backend, or None"""
        handler = cls.handler
        if not is_default_backend(handler, backend) and not TEST_MODE("full"):
            return "only default backend is being tested"
        if handler.has_backend(backend):
            return None
        if handler.name == "bcrypt" and backend == "builtin" and TEST_MODE("full"):
            # this will be auto-enabled under TEST_MODE 'full'.
            return None
        from passlib.utils import has_crypt
        if backend == "os_crypt" and has_crypt:
            if TEST_MODE("full") and cls.find_crypt_replacement():
                # in this case, HandlerCase will monkeypatch os_crypt
                # to use another backend, just so we can test os_crypt fully.
                return None
            else:
                return "hash not supported by os crypt()"
        return "backend not available"

    @classmethod
    def create_backend_cases(cls, backends, module=None):
        handler = cls.handler
        name = handler.name
        assert hasattr(handler, "backends"), "handler must support uh.HasManyBackends protocol"
        for backend in backends:
            assert backend in handler.backends, "unknown backend: %r" % (backend,)
            bases = (cls,)
            if backend == "os_crypt":
                bases += (OsCryptMixin,)
            subcls = type(
                "%s_%s_test" % (name, backend),
                bases,
                dict(
                    descriptionPrefix = "%s (%s backend)" % (name, backend),
                    backend = backend,
                    __module__= module or cls.__module__,
                )
            )
            skip_reason = cls._enable_backend_case(backend)
            if skip_reason:
                subcls = skip(skip_reason)(subcls)
            yield subcls

    @classmethod
    def find_crypt_replacement(cls, fallback=False):
        """find other backend which can be used to mock the os_crypt backend"""
        handler = cls.handler
        assert "os_crypt" in handler.backends, "expected os_crypt to be present"
        if fallback:
            # NOTE: using list() because tuples lack .index under py25 (issue 58)
            idx = list(handler.backends).index("os_crypt") + 1
        else:
            idx = 0
        for name in handler.backends[idx:]:
            if name != "os_crypt" and handler.has_backend(name):
                return name
        return None

    #===================================================================
    # setup
    #===================================================================
    def setUp(self):
        super(HandlerCase, self).setUp()

        # if needed, select specific backend for duration of test
        handler = self.handler
        backend = self.backend
        if backend:
            if not hasattr(handler, "set_backend"):
                raise RuntimeError("handler doesn't support multiple backends")
            self.addCleanup(handler.set_backend, handler.get_backend())
            handler.set_backend(backend)

    #===================================================================
    # basic tests
    #===================================================================
    def test_01_required_attributes(self):
        """validate required attributes"""
        handler = self.handler
        def ga(name):
            return getattr(handler, name, None)

        #
        # name should be a str, and valid
        #
        name = ga("name")
        self.assertTrue(name, "name not defined:")
        self.assertIsInstance(name, str, "name must be native str")
        self.assertTrue(name.lower() == name, "name not lower-case:")
        self.assertTrue(re.match("^[a-z0-9_]+$", name),
                        "name must be alphanum + underscore: %r" % (name,))

        #
        # setting_kwds should be specified
        #
        settings = ga("setting_kwds")
        self.assertTrue(settings is not None, "setting_kwds must be defined:")
        self.assertIsInstance(settings, tuple, "setting_kwds must be a tuple:")

        #
        # context_kwds should be specified
        #
        context = ga("context_kwds")
        self.assertTrue(context is not None, "context_kwds must be defined:")
        self.assertIsInstance(context, tuple, "context_kwds must be a tuple:")

        # XXX: any more checks needed?

    def test_02_config_workflow(self):
        """test basic config-string workflow

        this tests that genconfig() returns the expected types,
        and that identify() and genhash() handle the result correctly.
        """
        #
        # genconfig() should return native string,
        # or ``None`` if handler does not use a configuration string
        # (mostly used by static hashes)
        #
        config = self.do_genconfig()
        if self.supports_config_string:
            self.check_returned_native_str(config, "genconfig")
        else:
            self.assertIs(config, None)

        #
        # genhash() should always accept genconfig()'s output,
        # whether str OR None.
        #
        result = self.do_genhash('stub', config)
        self.check_returned_native_str(result, "genhash")

        #
        # verify() should never accept config strings
        #
        if self.supports_config_string:
            self.assertRaises(ValueError, self.do_verify, 'stub', config,
                __msg__="verify() failed to reject genconfig() output: %r" %
                (config,))
        else:
            self.assertRaises(TypeError, self.do_verify, 'stub', config)

        #
        # identify() should positively identify config strings if not None.
        #
        if self.supports_config_string:
            self.assertTrue(self.do_identify(config),
                "identify() failed to identify genconfig() output: %r" %
                (config,))
        else:
            self.assertRaises(TypeError, self.do_identify, config)

    def test_03_hash_workflow(self):
        """test basic hash-string workflow.

        this tests that encrypt()'s hashes are accepted
        by verify() and identify(), and regenerated correctly by genhash().
        the test is run against a couple of different stock passwords.
        """
        wrong_secret = 'stub'
        for secret in self.stock_passwords:

            #
            # encrypt() should generate native str hash
            #
            result = self.do_encrypt(secret)
            self.check_returned_native_str(result, "encrypt")

            #
            # verify() should work only against secret
            #
            self.check_verify(secret, result)
            self.check_verify(wrong_secret, result, negate=True)

            #
            # genhash() should reproduce original hash
            #
            other = self.do_genhash(secret, result)
            self.check_returned_native_str(other, "genhash")
            self.assertEqual(other, result, "genhash() failed to reproduce "
                             "hash: secret=%r hash=%r: result=%r" %
                             (secret, result, other))

            #
            # genhash() should NOT reproduce original hash for wrong password
            #
            other = self.do_genhash(wrong_secret, result)
            self.check_returned_native_str(other, "genhash")
            if self.is_disabled_handler:
                self.assertEqual(other, result, "genhash() failed to reproduce "
                                 "disabled-hash: secret=%r hash=%r other_secret=%r: result=%r" %
                                 (secret, result, wrong_secret, other))
            else:
                self.assertNotEqual(other, result, "genhash() duplicated "
                                 "hash: secret=%r hash=%r wrong_secret=%r: result=%r" %
                                 (secret, result, wrong_secret, other))

            #
            # identify() should positively identify hash
            #
            self.assertTrue(self.do_identify(result))

    def test_04_hash_types(self):
        """test hashes can be unicode or bytes"""
        # this runs through workflow similar to 03, but wraps
        # everything using tonn() so we test unicode under py2,
        # and bytes under py3.

        # encrypt using non-native secret
        result = self.do_encrypt(tonn('stub'))
        self.check_returned_native_str(result, "encrypt")

        # verify using non-native hash
        self.check_verify('stub', tonn(result))

        # verify using non-native hash AND secret
        self.check_verify(tonn('stub'), tonn(result))

        # genhash using non-native hash
        other = self.do_genhash('stub', tonn(result))
        self.check_returned_native_str(other, "genhash")
        self.assertEqual(other, result)

        # genhash using non-native hash AND secret
        other = self.do_genhash(tonn('stub'), tonn(result))
        self.check_returned_native_str(other, "genhash")
        self.assertEqual(other, result)

        # identify using non-native hash
        self.assertTrue(self.do_identify(tonn(result)))

    def test_05_backends(self):
        """test multi-backend support"""
        handler = self.handler
        if not hasattr(handler, "set_backend"):
            raise self.skipTest("handler only has one backend")
        with temporary_backend(handler):
            for backend in handler.backends:

                #
                # validate backend name
                #
                self.assertIsInstance(backend, str)
                self.assertNotIn(backend, RESERVED_BACKEND_NAMES,
                                 "invalid backend name: %r" % (backend,))

                #
                # ensure has_backend() returns bool value
                #
                ret = handler.has_backend(backend)
                if ret is True:
                    # verify backend can be loaded
                    handler.set_backend(backend)
                    self.assertEqual(handler.get_backend(), backend)

                elif ret is False:
                    # verify backend CAN'T be loaded
                    self.assertRaises(MissingBackendError, handler.set_backend,
                                      backend)

                else:
                    # didn't return boolean object. commonly fails due to
                    # use of 'classmethod' decorator instead of 'classproperty'
                    raise TypeError("has_backend(%r) returned invalid "
                                    "value: %r" % (backend, ret))

    #===================================================================
    # salts
    #===================================================================
    def require_salt(self):
        if 'salt' not in self.handler.setting_kwds:
            raise self.skipTest("handler doesn't have salt")

    def require_salt_info(self):
        self.require_salt()
        if not has_salt_info(self.handler):
            raise self.skipTest("handler doesn't provide salt info")

    def test_10_optional_salt_attributes(self):
        """validate optional salt attributes"""
        self.require_salt_info()
        AssertionError = self.failureException
        cls = self.handler

        # check max_salt_size
        mx_set = (cls.max_salt_size is not None)
        if mx_set and cls.max_salt_size < 1:
            raise AssertionError("max_salt_chars must be >= 1")

        # check min_salt_size
        if cls.min_salt_size < 0:
            raise AssertionError("min_salt_chars must be >= 0")
        if mx_set and cls.min_salt_size > cls.max_salt_size:
            raise AssertionError("min_salt_chars must be <= max_salt_chars")

        # check default_salt_size
        if cls.default_salt_size < cls.min_salt_size:
            raise AssertionError("default_salt_size must be >= min_salt_size")
        if mx_set and cls.default_salt_size > cls.max_salt_size:
            raise AssertionError("default_salt_size must be <= max_salt_size")

        # check for 'salt_size' keyword
        if 'salt_size' not in cls.setting_kwds and \
                (not mx_set or cls.min_salt_size < cls.max_salt_size):
            # NOTE: only bothering to issue warning if default_salt_size
            # isn't maxed out
            if (not mx_set or cls.default_salt_size < cls.max_salt_size):
                warn("%s: hash handler supports range of salt sizes, "
                     "but doesn't offer 'salt_size' setting" % (cls.name,))

        # check salt_chars & default_salt_chars
        if cls.salt_chars:
            if not cls.default_salt_chars:
                raise AssertionError("default_salt_chars must not be empty")
            if any(c not in cls.salt_chars for c in cls.default_salt_chars):
                raise AssertionError("default_salt_chars must be subset of salt_chars: %r not in salt_chars" % (c,))
        else:
            if not cls.default_salt_chars:
                raise AssertionError("default_salt_chars MUST be specified if salt_chars is empty")

    @property
    def salt_bits(self):
        """calculate number of salt bits in hash"""
        # XXX: replace this with bitsize() method?
        handler = self.handler
        assert has_salt_info(handler), "need explicit bit-size for " + handler.name
        from math import log
        # FIXME: this may be off for case-insensitive hashes, but that accounts
        # for ~1 bit difference, which is good enough for test_11()
        return int(handler.default_salt_size *
                   log(len(handler.default_salt_chars), 2))

    def test_11_unique_salt(self):
        """test encrypt() / genconfig() creates new salt each time"""
        self.require_salt()
        # odds of picking 'n' identical salts at random is '(.5**salt_bits)**n'.
        # we want to pick the smallest N needed s.t. odds are <1/1000, just
        # to eliminate false-positives. which works out to n>7-salt_bits.
        # n=1 is sufficient for most hashes, but a few border cases (e.g.
        # cisco_type7) have < 7 bits of salt, requiring more.
        samples = max(1,7-self.salt_bits)
        def sampler(func):
            value1 = func()
            for i in irange(samples):
                value2 = func()
                if value1 != value2:
                    return
            raise self.failureException("failed to find different salt after "
                                        "%d samples" % (samples,))
        if self.do_genconfig() is not None: # cisco_type7 has salt & no config
            sampler(self.do_genconfig)
        sampler(lambda : self.do_encrypt("stub"))

    def test_12_min_salt_size(self):
        """test encrypt() / genconfig() honors min_salt_size"""
        self.require_salt_info()

        handler = self.handler
        salt_char = handler.salt_chars[0:1]
        min_size = handler.min_salt_size

        #
        # check min is accepted
        #
        s1 = salt_char * min_size
        self.do_genconfig(salt=s1)

        self.do_encrypt('stub', salt_size=min_size)

        #
        # check min-1 is rejected
        #
        if min_size > 0:
            self.assertRaises(ValueError, self.do_genconfig,
                              salt=s1[:-1])

        self.assertRaises(ValueError, self.do_encrypt, 'stub',
                          salt_size=min_size-1)

    def test_13_max_salt_size(self):
        """test encrypt() / genconfig() honors max_salt_size"""
        self.require_salt_info()

        handler = self.handler
        max_size = handler.max_salt_size
        salt_char = handler.salt_chars[0:1]

        if max_size is None:
            #
            # if it's not set, salt should never be truncated; so test it
            # with an unreasonably large salt.
            #
            s1 = salt_char * 1024
            c1 = self.do_genconfig(salt=s1)
            c2 = self.do_genconfig(salt=s1 + salt_char)
            self.assertNotEqual(c1, c2)

            self.do_encrypt('stub', salt_size=1024)

        else:
            #
            # check max size is accepted
            #
            s1 = salt_char * max_size
            c1 = self.do_genconfig(salt=s1)

            self.do_encrypt('stub', salt_size=max_size)

            #
            # check max size + 1 is rejected
            #
            s2 = s1 + salt_char
            self.assertRaises(ValueError, self.do_genconfig, salt=s2)

            self.assertRaises(ValueError, self.do_encrypt, 'stub',
                              salt_size=max_size+1)

            #
            # should accept too-large salt in relaxed mode
            #
            if has_relaxed_setting(handler):
                with catch_warnings(record=True): # issues passlibhandlerwarning
                    c2 = self.do_genconfig(salt=s2, relaxed=True)
                self.assertEqual(c2, c1)

            #
            # if min_salt supports it, check smaller than mx is NOT truncated
            #
            if handler.min_salt_size < max_size:
                c3 = self.do_genconfig(salt=s1[:-1])
                self.assertNotEqual(c3, c1)

    # whether salt should be passed through bcrypt repair function
    fuzz_salts_need_bcrypt_repair = False

    def prepare_salt(self, salt):
        """prepare generated salt"""
        if self.fuzz_salts_need_bcrypt_repair:
            from passlib.utils import bcrypt64
            salt = bcrypt64.repair_unused(salt)
        return salt

    def test_14_salt_chars(self):
        """test genconfig() honors salt_chars"""
        self.require_salt_info()

        handler = self.handler
        mx = handler.max_salt_size
        mn = handler.min_salt_size
        cs = handler.salt_chars
        raw = isinstance(cs, bytes)

        # make sure all listed chars are accepted
        chunk = mx or 32
        for i in irange(0,len(cs),chunk):
            salt = cs[i:i+chunk]
            if len(salt) < mn:
                salt = (salt*(mn//len(salt)+1))[:chunk]
            salt = self.prepare_salt(salt)
            self.do_genconfig(salt=salt)

        # check some invalid salt chars, make sure they're rejected
        source = u('\x00\xff')
        if raw:
            source = source.encode("latin-1")
        chunk = max(mn, 1)
        for c in source:
            if c not in cs:
                self.assertRaises(ValueError, self.do_genconfig, salt=c*chunk,
                                  __msg__="invalid salt char %r:" % (c,))

    @property
    def salt_type(self):
        """hack to determine salt keyword's datatype"""
        # NOTE: cisco_type7 uses 'int'
        if getattr(self.handler, "_salt_is_bytes", False):
            return bytes
        else:
            return unicode

    def test_15_salt_type(self):
        """test non-string salt values"""
        self.require_salt()
        salt_type = self.salt_type

        # should always throw error for random class.
        class fake(object):
            pass
        self.assertRaises(TypeError, self.do_encrypt, 'stub', salt=fake())

        # unicode should be accepted only if salt_type is unicode.
        if salt_type is not unicode:
            self.assertRaises(TypeError, self.do_encrypt, 'stub', salt=u('x'))

        # bytes should be accepted only if salt_type is bytes,
        # OR if salt type is unicode and running PY2 - to allow native strings.
        if not (salt_type is bytes or (PY2 and salt_type is unicode)):
            self.assertRaises(TypeError, self.do_encrypt, 'stub', salt=b('x'))

    #===================================================================
    # rounds
    #===================================================================
    def require_rounds_info(self):
        if not has_rounds_info(self.handler):
            raise self.skipTest("handler lacks rounds attributes")

    def test_20_optional_rounds_attributes(self):
        """validate optional rounds attributes"""
        self.require_rounds_info()

        cls = self.handler
        AssertionError = self.failureException

        # check max_rounds
        if cls.max_rounds is None:
            raise AssertionError("max_rounds not specified")
        if cls.max_rounds < 1:
            raise AssertionError("max_rounds must be >= 1")

        # check min_rounds
        if cls.min_rounds < 0:
            raise AssertionError("min_rounds must be >= 0")
        if cls.min_rounds > cls.max_rounds:
            raise AssertionError("min_rounds must be <= max_rounds")

        # check default_rounds
        if cls.default_rounds is not None:
            if cls.default_rounds < cls.min_rounds:
                raise AssertionError("default_rounds must be >= min_rounds")
            if cls.default_rounds > cls.max_rounds:
                raise AssertionError("default_rounds must be <= max_rounds")

        # check rounds_cost
        if cls.rounds_cost not in rounds_cost_values:
            raise AssertionError("unknown rounds cost constant: %r" % (cls.rounds_cost,))

    def test_21_rounds_limits(self):
        """test encrypt() / genconfig() honors rounds limits"""
        self.require_rounds_info()
        handler = self.handler
        min_rounds = handler.min_rounds

        # check min is accepted
        self.do_genconfig(rounds=min_rounds)
        self.do_encrypt('stub', rounds=min_rounds)

        # check min-1 is rejected
        self.assertRaises(ValueError, self.do_genconfig, rounds=min_rounds-1)
        self.assertRaises(ValueError, self.do_encrypt, 'stub',
                          rounds=min_rounds-1)

        # TODO: check relaxed mode clips min-1

        # handle max rounds
        max_rounds = handler.max_rounds
        if max_rounds is None:
            # check large value is accepted
            self.do_genconfig(rounds=(1<<31)-1)
        else:
            # check max is accepted
            self.do_genconfig(rounds=max_rounds)

            # check max+1 is rejected
            self.assertRaises(ValueError, self.do_genconfig,
                              rounds=max_rounds+1)
            self.assertRaises(ValueError, self.do_encrypt, 'stub',
                              rounds=max_rounds+1)

            # TODO: check relaxed mode clips max+1

    #===================================================================
    # idents
    #===================================================================
    def test_30_HasManyIdents(self):
        """validate HasManyIdents configuration"""
        cls = self.handler
        if not isinstance(cls, type) or not issubclass(cls, uh.HasManyIdents):
            raise self.skipTest("handler doesn't derive from HasManyIdents")

        # check settings
        self.assertTrue('ident' in cls.setting_kwds)

        # check ident_values list
        for value in cls.ident_values:
            self.assertIsInstance(value, unicode,
                                  "cls.ident_values must be unicode:")
        self.assertTrue(len(cls.ident_values)>1,
                        "cls.ident_values must have 2+ elements:")

        # check default_ident value
        self.assertIsInstance(cls.default_ident, unicode,
                              "cls.default_ident must be unicode:")
        self.assertTrue(cls.default_ident in cls.ident_values,
                        "cls.default_ident must specify member of cls.ident_values")

        # check optional aliases list
        if cls.ident_aliases:
            for alias, ident in iteritems(cls.ident_aliases):
                self.assertIsInstance(alias, unicode,
                                      "cls.ident_aliases keys must be unicode:") # XXX: allow ints?
                self.assertIsInstance(ident, unicode,
                                      "cls.ident_aliases values must be unicode:")
                self.assertTrue(ident in cls.ident_values,
                                "cls.ident_aliases must map to cls.ident_values members: %r" % (ident,))

        # check constructor validates ident correctly.
        handler = cls
        hash = self.get_sample_hash()[1]
        kwds = handler.parsehash(hash)
        del kwds['ident']

        # ... accepts good ident
        handler(ident=cls.default_ident, **kwds)

        # ... requires ident w/o defaults
        self.assertRaises(TypeError, handler, **kwds)

        # ... supplies default ident
        handler(use_defaults=True, **kwds)

        # ... rejects bad ident
        self.assertRaises(ValueError, handler, ident='xXx', **kwds)

    # TODO: check various supported idents

    #===================================================================
    # passwords
    #===================================================================
    def test_60_secret_size(self):
        """test password size limits"""
        sc = self.secret_size
        base = "too many secrets" # 16 chars
        alt = 'x' # char that's not in base string
        if sc is not None:
            # hash only counts the first <sc> characters; eg: bcrypt, des-crypt

            # create & hash string that's exactly sc+1 chars
            secret = repeat_string(base, sc+1)
            hash = self.do_encrypt(secret)

            # check sc value isn't too large by verifying that sc-1'th char
            # affects hash
            secret2 = secret[:-2] + alt + secret[-1]
            self.assertFalse(self.do_verify(secret2, hash),
                            "secret_size value is too large")

            # check sc value isn't too small by verifying adding sc'th char
            # *doesn't* affect hash
            secret3 = secret[:-1] + alt
            self.assertTrue(self.do_verify(secret3, hash),
                            "secret_size value is too small")

        else:
            # hash counts all characters; e.g. md5-crypt

            # NOTE: this doesn't do an exhaustive search to verify algorithm
            # doesn't have some cutoff point, it just tries
            # 1024-character string, and alters the last char.
            # as long as algorithm doesn't clip secret at point <1024,
            # the new secret shouldn't verify.
            secret = base * 64
            hash = self.do_encrypt(secret)
            secret2 = secret[:-1] + alt
            self.assertFalse(self.do_verify(secret2, hash),
                             "full password not used in digest")

    def test_61_secret_case_sensitive(self):
        """test password case sensitivity"""
        hash_insensitive = self.secret_case_insensitive is True
        verify_insensitive = self.secret_case_insensitive in [True,
                                                              "verify-only"]

        lower = 'test'
        upper = 'TEST'
        h1 = self.do_encrypt(lower)
        if verify_insensitive and not self.is_disabled_handler:
            self.assertTrue(self.do_verify(upper, h1),
                            "verify() should not be case sensitive")
        else:
            self.assertFalse(self.do_verify(upper, h1),
                             "verify() should be case sensitive")

        h2 = self.do_genhash(upper, h1)
        if hash_insensitive or self.is_disabled_handler:
            self.assertEqual(h2, h1,
                             "genhash() should not be case sensitive")
        else:
            self.assertNotEqual(h2, h1,
                                "genhash() should be case sensitive")

    def test_62_secret_border(self):
        """test non-string passwords are rejected"""
        hash = self.get_sample_hash()[1]

        # secret=None
        self.assertRaises(TypeError, self.do_encrypt, None)
        self.assertRaises(TypeError, self.do_genhash, None, hash)
        self.assertRaises(TypeError, self.do_verify, None, hash)

        # secret=int (picked as example of entirely wrong class)
        self.assertRaises(TypeError, self.do_encrypt, 1)
        self.assertRaises(TypeError, self.do_genhash, 1, hash)
        self.assertRaises(TypeError, self.do_verify, 1, hash)

    def test_63_large_secret(self):
        """test MAX_PASSWORD_SIZE is enforced"""
        from passlib.exc import PasswordSizeError
        from passlib.utils import MAX_PASSWORD_SIZE
        secret = '.' * (1+MAX_PASSWORD_SIZE)
        hash = self.get_sample_hash()[1]
        self.assertRaises(PasswordSizeError, self.do_genhash, secret, hash)
        self.assertRaises(PasswordSizeError, self.do_encrypt, secret)
        self.assertRaises(PasswordSizeError, self.do_verify, secret, hash)

    def test_64_forbidden_chars(self):
        """test forbidden characters not allowed in password"""
        chars = self.forbidden_characters
        if not chars:
            raise self.skipTest("none listed")
        base = u('stub')
        if isinstance(chars, bytes):
            from passlib.utils.compat import iter_byte_chars
            chars = iter_byte_chars(chars)
            base = base.encode("ascii")
        for c in chars:
            self.assertRaises(ValueError, self.do_encrypt, base + c + base)

    #===================================================================
    # check identify(), verify(), genhash() against test vectors
    #===================================================================
    def is_secret_8bit(self, secret):
        secret = self.populate_context(secret, {})
        return not is_ascii_safe(secret)

    def expect_os_crypt_failure(self, secret):
        """
        check if we're expecting potential verify failure due to crypt.crypt() encoding limitation
        """
        if PY3 and self.backend == "os_crypt" and isinstance(secret, bytes):
            try:
                secret.decode("utf-8")
            except UnicodeDecodeError:
                return True
        return False

    def test_70_hashes(self):
        """test known hashes"""

        # sanity check
        self.assertTrue(self.known_correct_hashes or self.known_correct_configs,
                        "test must set at least one of 'known_correct_hashes' "
                        "or 'known_correct_configs'")

        # run through known secret/hash pairs
        saw8bit = False
        for secret, hash in self.iter_known_hashes():
            if self.is_secret_8bit(secret):
                saw8bit = True

            # hash should be positively identified by handler
            self.assertTrue(self.do_identify(hash),
                "identify() failed to identify hash: %r" % (hash,))

            # check if what we're about to do is expected to fail due to crypt.crypt() limitation.
            expect_os_crypt_failure = self.expect_os_crypt_failure(secret)
            try:

                # secret should verify successfully against hash
                self.check_verify(secret, hash, "verify() of known hash failed: "
                                  "secret=%r, hash=%r" % (secret, hash))

                # genhash() should reproduce same hash
                result = self.do_genhash(secret, hash)
                self.assertIsInstance(result, str,
                    "genhash() failed to return native string: %r" % (result,))
                self.assertEqual(result, hash,  "genhash() failed to reproduce "
                    "known hash: secret=%r, hash=%r: result=%r" %
                    (secret, hash, result))

            except MissingBackendError:
                if not expect_os_crypt_failure:
                    raise

        # would really like all handlers to have at least one 8-bit test vector
        if not saw8bit:
            warn("%s: no 8-bit secrets tested" % self.__class__)

    def test_71_alternates(self):
        """test known alternate hashes"""
        if not self.known_alternate_hashes:
            raise self.skipTest("no alternate hashes provided")
        for alt, secret, hash in self.known_alternate_hashes:

            # hash should be positively identified by handler
            self.assertTrue(self.do_identify(hash),
                "identify() failed to identify alternate hash: %r" %
                (hash,))

            # secret should verify successfully against hash
            self.check_verify(secret, alt, "verify() of known alternate hash "
                              "failed: secret=%r, hash=%r" % (secret, alt))

            # genhash() should reproduce canonical hash
            result = self.do_genhash(secret, alt)
            self.assertIsInstance(result, str,
                "genhash() failed to return native string: %r" % (result,))
            self.assertEqual(result, hash,  "genhash() failed to normalize "
                "known alternate hash: secret=%r, alt=%r, hash=%r: "
                "result=%r" % (secret, alt, hash, result))

    def test_72_configs(self):
        """test known config strings"""
        # special-case handlers without settings
        if not self.handler.setting_kwds:
            self.assertFalse(self.known_correct_configs,
                            "handler should not have config strings")
            raise self.skipTest("hash has no settings")

        if not self.known_correct_configs:
            # XXX: make this a requirement?
            raise self.skipTest("no config strings provided")

        # make sure config strings work (hashes in list tested in test_70)
        if self.filter_config_warnings:
            warnings.filterwarnings("ignore", category=PasslibHashWarning)
        for config, secret, hash in self.known_correct_configs:

            # config should be positively identified by handler
            self.assertTrue(self.do_identify(config),
                "identify() failed to identify known config string: %r" %
                (config,))

            # verify() should throw error for config strings.
            self.assertRaises(ValueError, self.do_verify, secret, config,
                __msg__="verify() failed to reject config string: %r" %
                (config,))

            # genhash() should reproduce hash from config.
            result = self.do_genhash(secret, config)
            self.assertIsInstance(result, str,
                "genhash() failed to return native string: %r" % (result,))
            self.assertEqual(result, hash,  "genhash() failed to reproduce "
                "known hash from config: secret=%r, config=%r, hash=%r: "
                "result=%r" % (secret, config, hash, result))

    def test_73_unidentified(self):
        """test known unidentifiably-mangled strings"""
        if not self.known_unidentified_hashes:
            raise self.skipTest("no unidentified hashes provided")
        for hash in self.known_unidentified_hashes:

            # identify() should reject these
            self.assertFalse(self.do_identify(hash),
                "identify() incorrectly identified known unidentifiable "
                "hash: %r" % (hash,))

            # verify() should throw error
            self.assertRaises(ValueError, self.do_verify, 'stub', hash,
                __msg__= "verify() failed to throw error for unidentifiable "
                "hash: %r" % (hash,))

            # genhash() should throw error
            self.assertRaises(ValueError, self.do_genhash, 'stub', hash,
                __msg__= "genhash() failed to throw error for unidentifiable "
                "hash: %r" % (hash,))

    def test_74_malformed(self):
        """test known identifiable-but-malformed strings"""
        if not self.known_malformed_hashes:
            raise self.skipTest("no malformed hashes provided")
        for hash in self.known_malformed_hashes:

            # identify() should accept these
            self.assertTrue(self.do_identify(hash),
                "identify() failed to identify known malformed "
                "hash: %r" % (hash,))

            # verify() should throw error
            self.assertRaises(ValueError, self.do_verify, 'stub', hash,
                __msg__= "verify() failed to throw error for malformed "
                "hash: %r" % (hash,))

            # genhash() should throw error
            self.assertRaises(ValueError, self.do_genhash, 'stub', hash,
                __msg__= "genhash() failed to throw error for malformed "
                "hash: %r" % (hash,))

    def test_75_foreign(self):
        """test known foreign hashes"""
        if self.accepts_all_hashes:
            raise self.skipTest("not applicable")
        if not self.known_other_hashes:
            raise self.skipTest("no foreign hashes provided")
        for name, hash in self.known_other_hashes:
            # NOTE: most tests use default list of foreign hashes,
            # so they may include ones belonging to that hash...
            # hence the 'own' logic.

            if name == self.handler.name:
                # identify should accept these
                self.assertTrue(self.do_identify(hash),
                    "identify() failed to identify known hash: %r" % (hash,))

                # verify & genhash should NOT throw error
                self.do_verify('stub', hash)
                result = self.do_genhash('stub', hash)
                self.assertIsInstance(result, str,
                    "genhash() failed to return native string: %r" % (result,))

            else:
                # identify should reject these
                self.assertFalse(self.do_identify(hash),
                    "identify() incorrectly identified hash belonging to "
                    "%s: %r" % (name, hash))

                # verify should throw error
                self.assertRaises(ValueError, self.do_verify, 'stub', hash,
                    __msg__= "verify() failed to throw error for hash "
                    "belonging to %s: %r" % (name, hash,))

                # genhash() should throw error
                self.assertRaises(ValueError, self.do_genhash, 'stub', hash,
                    __msg__= "genhash() failed to throw error for hash "
                    "belonging to %s: %r" % (name, hash))

    def test_76_hash_border(self):
        """test non-string hashes are rejected"""
        #
        # test hash=None is rejected (except if config=None)
        #
        self.assertRaises(TypeError, self.do_identify, None)
        self.assertRaises(TypeError, self.do_verify, 'stub', None)
        if self.supports_config_string:
            self.assertRaises(TypeError, self.do_genhash, 'stub', None)
        else:
            result = self.do_genhash('stub', None)
            self.check_returned_native_str(result, "genhash")

        #
        # test hash=int is rejected (picked as example of entirely wrong type)
        #
        self.assertRaises(TypeError, self.do_identify, 1)
        self.assertRaises(TypeError, self.do_verify, 'stub', 1)
        self.assertRaises(TypeError, self.do_genhash, 'stub', 1)

        #
        # test hash='' is rejected for all but the plaintext hashes
        #
        for hash in [u(''), b('')]:
            if self.accepts_all_hashes:
                # then it accepts empty string as well.
                self.assertTrue(self.do_identify(hash))
                self.do_verify('stub', hash)
                result = self.do_genhash('stub', hash)
                self.check_returned_native_str(result, "genhash")
            else:
                # otherwise it should reject them
                self.assertFalse(self.do_identify(hash),
                    "identify() incorrectly identified empty hash")
                self.assertRaises(ValueError, self.do_verify, 'stub', hash,
                    __msg__="verify() failed to reject empty hash")
                self.assertRaises(ValueError, self.do_genhash, 'stub', hash,
                    __msg__="genhash() failed to reject empty hash")

        #
        # test identify doesn't throw decoding errors on 8-bit input
        #
        self.do_identify('\xe2\x82\xac\xc2\xa5$') # utf-8
        self.do_identify('abc\x91\x00') # non-utf8

    #===================================================================
    # fuzz testing
    #===================================================================
    def test_77_fuzz_input(self):
        """test random passwords and options

        This test attempts to perform some basic fuzz testing of the hash,
        based on whatever information can be found about it.
        It does as much as it can within a fixed amount of time
        (defaults to 1 second, but can be overridden via $PASSLIB_TEST_FUZZ_TIME).
        It tests the following:

        * randomly generated passwords including extended unicode chars
        * randomly selected rounds values (if rounds supported)
        * randomly selected salt sizes (if salts supported)
        * randomly selected identifiers (if multiple found)
        * runs output of selected backend against other available backends
          (if any) to detect errors occurring between different backends.
        * runs output against other "external" verifiers such as OS crypt()
        """
        if self.is_disabled_handler:
            raise self.skipTest("not applicable")

        # gather info
        from passlib.utils import tick
        handler = self.handler
        disabled = self.is_disabled_handler
        max_time = self.max_fuzz_time
        if max_time <= 0:
            raise self.skipTest("disabled by test mode")
        verifiers = self.get_fuzz_verifiers()
        def vname(v):
            return (v.__doc__ or v.__name__).splitlines()[0]

        # do as many tests as possible for max_time seconds
        stop = tick() + max_time
        count = 0
        while tick() <= stop:
            # generate random password & options
            secret, other, kwds = self.get_fuzz_settings()
            ctx = dict((k,kwds[k]) for k in handler.context_kwds if k in kwds)

            # create new hash
            hash = self.do_encrypt(secret, **kwds)
            ##log.debug("fuzz test: hash=%r secret=%r other=%r",
            ##          hash, secret, other)

            # run through all verifiers we found.
            for verify in verifiers:
                name = vname(verify)
                result = verify(secret, hash, **ctx)
                if result == "skip": # let verifiers signal lack of support
                    continue
                assert result is True or result is False
                if not result:
                    raise self.failureException("failed to verify against %s: "
                                                "secret=%r config=%r hash=%r" %
                                                (name, secret, kwds, hash))
                # occasionally check that some other secrets WON'T verify
                # against this hash.
                if rng.random() < .1:
                    result = verify(other, hash, **ctx)
                    if result and result != "skip":
                        raise self.failureException("was able to verify wrong "
                            "password using %s: wrong_secret=%r real_secret=%r "
                            "config=%r hash=%r" % (name, other, secret, kwds, hash))
            count +=1

        log.debug("fuzz test: %r checked %d passwords against %d verifiers (%s)",
                  self.descriptionPrefix,  count, len(verifiers),
                  ", ".join(vname(v) for v in verifiers))

    #---------------------------------------------------------------
    # fuzz constants & helpers
    #---------------------------------------------------------------

    # alphabet for randomly generated passwords
    fuzz_password_alphabet = u('qwertyASDF1234<>.@*#! \u00E1\u0259\u0411\u2113')

    # encoding when testing bytes
    fuzz_password_encoding = "utf-8"

    @property
    def max_fuzz_time(self):
        """amount of time to spend on fuzz testing"""
        value = float(os.environ.get("PASSLIB_TEST_FUZZ_TIME") or 0)
        if value:
            return value
        elif TEST_MODE(max="quick"):
            return 0
        elif TEST_MODE(max="default"):
            return 1
        else:
            return 5

    def os_supports_ident(self, ident):
        """whether native OS crypt() supports particular ident value"""
        return True

    #---------------------------------------------------------------
    # fuzz verifiers
    #---------------------------------------------------------------
    def get_fuzz_verifiers(self):
        """return list of password verifiers (including external libs)

        used by fuzz testing.
        verifiers should be callable with signature
        ``func(password: unicode, hash: ascii str) -> ok: bool``.
        """
        handler = self.handler
        verifiers = []

        # call all methods starting with prefix in order to create
        # any verifiers.
        prefix = "fuzz_verifier_"
        for name in dir(self):
            if name.startswith(prefix):
                func = getattr(self, name)()
                if func is not None:
                    verifiers.append(func)

        # create verifiers for any other available backends
        if hasattr(handler, "backends") and TEST_MODE("full"):
            def maker(backend):
                def func(secret, hash):
                    with temporary_backend(handler, backend):
                        return handler.verify(secret, hash)
                func.__name__ = "check_" + backend + "_backend"
                func.__doc__ = backend + "-backend"
                return func
            cur = handler.get_backend()
            for backend in handler.backends:
                if backend != cur and handler.has_backend(backend):
                    verifiers.append(maker(backend))

        return verifiers

    def fuzz_verifier_default(self):
        # test against self
        def check_default(secret, hash, **ctx):
            return self.do_verify(secret, hash, **ctx)
        if self.backend:
            check_default.__doc__ = self.backend + "-backend"
        else:
            check_default.__doc__ = "self"
        return check_default

    def fuzz_verifier_crypt(self):
        """test results against OS crypt()"""
        handler = self.handler
        if self.using_patched_crypt or not has_crypt_support(handler):
            return None
        from crypt import crypt
        def check_crypt(secret, hash):
            """stdlib-crypt"""
            if not self.os_supports_ident(hash):
                return "skip"
            secret = to_native_str(secret, self.fuzz_password_encoding)
            return crypt(secret, hash) == hash
        return check_crypt

    #---------------------------------------------------------------
    # fuzz settings generation
    #---------------------------------------------------------------
    def get_fuzz_settings(self):
        """generate random password and options for fuzz testing"""
        prefix = "fuzz_setting_"
        kwds = {}
        for name in dir(self):
            if name.startswith(prefix):
                value = getattr(self, name)()
                if value is not None:
                    kwds[name[len(prefix):]] = value
        secret, other = self.get_fuzz_password_pair()
        return secret, other, kwds

    def fuzz_setting_rounds(self):
        handler = self.handler
        if not has_rounds_info(handler):
            return None
        default = handler.default_rounds or handler.min_rounds
        lower = handler.min_rounds
        if handler.rounds_cost == "log2":
            upper = default
        else:
            upper = min(default*2, handler.max_rounds)
        return randintgauss(lower, upper, default, default*.5)

    def fuzz_setting_salt_size(self):
        handler = self.handler
        if not (has_salt_info(handler) and 'salt_size' in handler.setting_kwds):
            return None
        default = handler.default_salt_size
        lower = handler.min_salt_size
        upper = handler.max_salt_size or default*4
        return randintgauss(lower, upper, default, default*.5)

    def fuzz_setting_ident(self):
        handler = self.handler
        if 'ident' not in handler.setting_kwds or not hasattr(handler, "ident_values"):
            return None
        if rng.random() < .5:
            return None
        # resolve wrappers before reading values
        handler = getattr(handler, "wrapped", handler)
        ident = rng.choice(handler.ident_values)
        if self.backend == "os_crypt" and not self.using_patched_crypt and not self.os_supports_ident(ident):
            return None
        return ident

    #---------------------------------------------------------------
    # fuzz password generation
    #---------------------------------------------------------------
    def get_fuzz_password(self):
        """generate random passwords for fuzz testing"""
        # occasionally try an empty password
        if rng.random() < .0001:
            return u('')
        # otherwise alternate between large and small passwords.
        if rng.random() < .5:
            size = randintgauss(1, 50, 15, 15)
        else:
            size = randintgauss(50, 99, 70, 20)
        return getrandstr(rng, self.fuzz_password_alphabet, size)

    def accept_fuzz_pair(self, secret, other):
        """verify fuzz pair contains different passwords"""
        return secret != other

    def get_fuzz_password_pair(self):
        """generate random password, and non-matching alternate password"""
        secret = self.get_fuzz_password()
        while True:
            other = self.get_fuzz_password()
            if self.accept_fuzz_pair(secret, other):
                break
        if rng.randint(0,1):
            secret = secret.encode(self.fuzz_password_encoding)
        if rng.randint(0,1):
            other = other.encode(self.fuzz_password_encoding)
        return secret, other

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# HandlerCase mixins providing additional tests for certain hashes
#=============================================================================
class OsCryptMixin(HandlerCase):
    """helper used by create_backend_case() which adds additional features
    to test the os_crypt backend.

    * if crypt support is missing, inserts fake crypt support to simulate
      a working safe_crypt, to test passlib's codepath as fully as possible.

    * extra tests to verify non-conformant crypt implementations are handled
      correctly.

    * check that native crypt support is detected correctly for known platforms.
    """
    #===================================================================
    # option flags
    #===================================================================
    # platforms that are known to support / not support this hash natively.
    # list of (platform_regex, True|False|None) entries.
    platform_crypt_support = []

    #===================================================================
    # instance attrs
    #===================================================================
    __unittest_skip = True

    # force this backend
    backend = "os_crypt"

    # flag read by HandlerCase to detect if fake os crypt is enabled.
    using_patched_crypt = False

    #===================================================================
    # setup
    #===================================================================
    def setUp(self):
        assert self.backend == "os_crypt"
        if not self.handler.has_backend("os_crypt"):
            self.handler.get_backend() # hack to prevent recursion issue
            self._patch_safe_crypt()
        super(OsCryptMixin, self).setUp()

    # alternate handler to use for fake os_crypt,
    # e.g. bcrypt_sha256 uses bcrypt
    fallback_os_crypt_handler = None

    def _patch_safe_crypt(self):
        """if crypt() doesn't support current hash alg, this patches
        safe_crypt() so that it transparently uses another one of the handler's
        backends, so that we can go ahead and test as much of code path
        as possible.
        """
        handler = self.fallback_os_crypt_handler or self.handler
        # resolve wrappers, since we want to return crypt compatible hash.
        while hasattr(handler, "wrapped"):
            handler = handler.wrapped
        alt_backend = self.find_crypt_replacement()
        if not alt_backend:
            raise AssertionError("handler has no available backends!")

        # create subclass of handler, which we swap to an alternate backend.
        # NOTE: not switching original class's backend, since classes like bcrypt
        #       run some checks when backend is set, that can cause recursion error
        #       when orig backend is restored.
        alt_handler = type('%s_%s_wrapper' % (handler.name, alt_backend), (handler,), {})
        alt_handler._backend = None  # ensure full backend load into subclass
        alt_handler.set_backend(alt_backend)

        import passlib.utils as mod

        def crypt_stub(secret, hash):
            # with temporary_backend(alt_handler, alt_backend):
            hash = alt_handler.genhash(secret, hash)
            assert isinstance(hash, str)
            return hash

        self.addCleanup(setattr, mod, "_crypt", mod._crypt)
        mod._crypt = crypt_stub
        self.using_patched_crypt = True

    #===================================================================
    # custom tests
    #===================================================================
    def _use_mock_crypt(self):
        """patch safe_crypt() so it returns mock value"""
        import passlib.utils as mod
        if not self.using_patched_crypt:
            self.addCleanup(setattr, mod, "_crypt", mod._crypt)
        crypt_value = [None]
        mod._crypt = lambda secret, config: crypt_value[0]
        def setter(value):
            crypt_value[0] = value
        return setter

    def test_80_faulty_crypt(self):
        """test with faulty crypt()"""
        hash = self.get_sample_hash()[1]
        exc_types = (AssertionError,)
        setter = self._use_mock_crypt()

        def test(value):
            # set safe_crypt() to return specified value, and
            # make sure assertion error is raised by handler.
            setter(value)
            self.assertRaises(exc_types, self.do_genhash, "stub", hash)
            self.assertRaises(exc_types, self.do_encrypt, "stub")
            self.assertRaises(exc_types, self.do_verify, "stub", hash)

        test('$x' + hash[2:]) # detect wrong prefix
        test(hash[:-1]) # detect too short
        test(hash + 'x') # detect too long

    def test_81_crypt_fallback(self):
        """test per-call crypt() fallback"""
        # set safe_crypt to return None
        setter = self._use_mock_crypt()
        setter(None)
        if self.find_crypt_replacement(fallback=True):
            # handler should have a fallback to use
            h1 = self.do_encrypt("stub")
            h2 = self.do_genhash("stub", h1)
            self.assertEqual(h2, h1)
            self.assertTrue(self.do_verify("stub", h1))
        else:
            # handler should give up
            from passlib.exc import MissingBackendError
            hash = self.get_sample_hash()[1]
            self.assertRaises(MissingBackendError, self.do_encrypt, 'stub')
            self.assertRaises(MissingBackendError, self.do_genhash, 'stub', hash)
            self.assertRaises(MissingBackendError, self.do_verify, 'stub', hash)

    def test_82_crypt_support(self):
        """test platform-specific crypt() support detection"""
        # NOTE: this is mainly just a sanity check to ensure the runtime
        #       detection is functioning correctly on some known platforms,
        #       so that I can feel more confident it'll work right on unknown ones.
        if hasattr(self.handler, "orig_prefix"):
            raise self.skipTest("not applicable to wrappers")
        platform = sys.platform
        for pattern, state in self.platform_crypt_support:
            if re.match(pattern, platform):
                break
        else:
            raise self.skipTest("no data for %r platform" % platform)
        if state is None:
            # e.g. platform='freebsd8' ... sha256_crypt not added until 8.3
            raise self.skipTest("varied support on %r platform" % platform)
        elif state != self.using_patched_crypt:
            return
        elif state:
            self.fail("expected %r platform would have native support "
                      "for %r" % (platform, self.handler.name))
        else:
            self.fail("did not expect %r platform would have native support "
                      "for %r" % (platform, self.handler.name))

    #===================================================================
    # eoc
    #===================================================================

class UserHandlerMixin(HandlerCase):
    """helper for handlers w/ 'user' context kwd; mixin for HandlerCase

    this overrides the HandlerCase test harness methods
    so that a username is automatically inserted to encrypt/verify
    calls. as well, passing in a pair of strings as the password
    will be interpreted as (secret,user)
    """
    #===================================================================
    # option flags
    #===================================================================
    default_user = "user"
    requires_user = True
    user_case_insensitive = False

    #===================================================================
    # instance attrs
    #===================================================================
    __unittest_skip = True

    #===================================================================
    # custom tests
    #===================================================================
    def test_80_user(self):
        """test user context keyword"""
        handler = self.handler
        password = 'stub'
        hash = handler.encrypt(password, user=self.default_user)

        if self.requires_user:
            self.assertRaises(TypeError, handler.encrypt, password)
            self.assertRaises(TypeError, handler.genhash, password, hash)
            self.assertRaises(TypeError, handler.verify, password, hash)
        else:
            # e.g. cisco_pix works with or without one.
            handler.encrypt(password)
            handler.genhash(password, hash)
            handler.verify(password, hash)

    def test_81_user_case(self):
        """test user case sensitivity"""
        lower = self.default_user.lower()
        upper = lower.upper()
        hash = self.do_encrypt('stub', user=lower)
        if self.user_case_insensitive:
            self.assertTrue(self.do_verify('stub', hash, user=upper),
                            "user should not be case sensitive")
        else:
            self.assertFalse(self.do_verify('stub', hash, user=upper),
                             "user should be case sensitive")

    def test_82_user_salt(self):
        """test user used as salt"""
        config = self.do_genconfig()
        h1 = self.do_genhash('stub', config, user='admin')
        h2 = self.do_genhash('stub', config, user='admin')
        self.assertEqual(h2, h1)
        h3 = self.do_genhash('stub', config, user='root')
        self.assertNotEqual(h3, h1)

    # TODO: user size? kinda dicey, depends on algorithm.

    #===================================================================
    # override test helpers
    #===================================================================
    def populate_context(self, secret, kwds):
        """insert username into kwds"""
        if isinstance(secret, tuple):
            secret, user = secret
        elif not self.requires_user:
            return secret
        else:
            user = self.default_user
        if 'user' not in kwds:
            kwds['user'] = user
        return secret

    #===================================================================
    # modify fuzz testing
    #===================================================================
    fuzz_user_alphabet = u("asdQWE123")

    def fuzz_setting_user(self):
        if not self.requires_user and rng.random() < .1:
            return None
        return getrandstr(rng, self.fuzz_user_alphabet, rng.randint(2,10))

    #===================================================================
    # eoc
    #===================================================================

class EncodingHandlerMixin(HandlerCase):
    """helper for handlers w/ 'encoding' context kwd; mixin for HandlerCase

    this overrides the HandlerCase test harness methods
    so that an encoding can be inserted to encrypt/verify
    calls by passing in a pair of strings as the password
    will be interpreted as (secret,encoding)
    """
    #===================================================================
    # instance attrs
    #===================================================================
    __unittest_skip = True

    # restrict stock passwords & fuzz alphabet to latin-1,
    # so different encodings can be tested safely.
    stock_passwords = [
        u("test"),
        b("test"),
        u("\u00AC\u00BA"),
    ]

    fuzz_password_alphabet = u('qwerty1234<>.@*#! \u00AC')

    def populate_context(self, secret, kwds):
        """insert encoding into kwds"""
        if isinstance(secret, tuple):
            secret, encoding = secret
            kwds.setdefault('encoding', encoding)
        return secret
    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# warnings helpers
#=============================================================================
class reset_warnings(catch_warnings):
    """catch_warnings() wrapper which clears warning registry & filters"""
    def __init__(self, reset_filter="always", reset_registry=".*", **kwds):
        super(reset_warnings, self).__init__(**kwds)
        self._reset_filter = reset_filter
        self._reset_registry = re.compile(reset_registry) if reset_registry else None

    def __enter__(self):
        # let parent class archive filter state
        ret = super(reset_warnings, self).__enter__()

        # reset the filter to list everything
        if self._reset_filter:
            warnings.resetwarnings()
            warnings.simplefilter(self._reset_filter)

        # archive and clear the __warningregistry__ key for all modules
        # that match the 'reset' pattern.
        pattern = self._reset_registry
        if pattern:
            orig = self._orig_registry = {}
            for name, mod in sys.modules.items():
                if pattern.match(name):
                    reg = getattr(mod, "__warningregistry__", None)
                    if reg:
                        orig[name] = reg.copy()
                        reg.clear()
        return ret

    def __exit__(self, *exc_info):
        # restore warning registry for all modules
        pattern = self._reset_registry
        if pattern:
            # restore archived registry data
            orig = self._orig_registry
            for name, content in iteritems(orig):
                mod = sys.modules.get(name)
                if mod is None:
                    continue
                reg = getattr(mod, "__warningregistry__", None)
                if reg is None:
                    setattr(mod, "__warningregistry__", content)
                else:
                    reg.clear()
                    reg.update(content)
            # clear all registry entries that we didn't archive
            for name, mod in sys.modules.items():
                if pattern.match(name) and name not in orig:
                    reg = getattr(mod, "__warningregistry__", None)
                    if reg:
                        reg.clear()
        super(reset_warnings, self).__exit__(*exc_info)

#=============================================================================
# eof
#=============================================================================
