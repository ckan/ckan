"""passlib.ext.django.utils - helper functions used by this plugin"""
#=============================================================================
# imports
#=============================================================================
# core
import logging; log = logging.getLogger(__name__)
from weakref import WeakKeyDictionary
from warnings import warn
# site
try:
    from django import VERSION as DJANGO_VERSION
    log.debug("found django %r installation", DJANGO_VERSION)
except ImportError:
    log.debug("django installation not found")
    DJANGO_VERSION = ()
# pkg
from passlib.context import CryptContext
from passlib.exc import PasslibRuntimeWarning
from passlib.registry import get_crypt_handler, list_crypt_handlers
from passlib.utils import classproperty
from passlib.utils.compat import bytes, get_method_function, iteritems
# local
__all__ = [
    "get_preset_config",
    "get_passlib_hasher",
]

#=============================================================================
# default policies
#=============================================================================

# map preset names -> passlib.app attrs
_preset_map = {
    "django-1.0": "django10_context",
    "django-1.4": "django14_context",
    "django-1.6": "django16_context",
    "django-latest": "django_context",
}

def get_preset_config(name):
    """Returns configuration string for one of the preset strings
    supported by the ``PASSLIB_CONFIG`` setting.
    Currently supported presets:

    * ``"passlib-default"`` - default config used by this release of passlib.
    * ``"django-default"`` - config matching currently installed django version.
    * ``"django-latest"`` - config matching newest django version (currently same as ``"django-1.6"``).
    * ``"django-1.0"`` - config used by stock Django 1.0 - 1.3 installs
    * ``"django-1.4"`` - config used by stock Django 1.4 installs
    * ``"django-1.6"`` - config used by stock Django 1.6 installs
    """
    # TODO: add preset which includes HASHERS + PREFERRED_HASHERS,
    #       after having imported any custom hashers. e.g. "django-current"
    if name == "django-default":
        if not DJANGO_VERSION:
            raise ValueError("can't resolve django-default preset, "
                             "django not installed")
        if DJANGO_VERSION < (1,4):
            name = "django-1.0"
        elif DJANGO_VERSION < (1,6):
            name = "django-1.4"
        else:
            name = "django-1.6"
    if name == "passlib-default":
        return PASSLIB_DEFAULT
    try:
        attr = _preset_map[name]
    except KeyError:
        raise ValueError("unknown preset config name: %r" % name)
    import passlib.apps
    return getattr(passlib.apps, attr).to_string()

# default context used by passlib 1.6
PASSLIB_DEFAULT = """
[passlib]

; list of schemes supported by configuration
; currently all django 1.6, 1.4, and 1.0 hashes,
; and three common modular crypt format hashes.
schemes =
    django_pbkdf2_sha256, django_pbkdf2_sha1, django_bcrypt, django_bcrypt_sha256,
    django_salted_sha1, django_salted_md5, django_des_crypt, hex_md5,
    sha512_crypt, bcrypt, phpass

; default scheme to use for new hashes
default = django_pbkdf2_sha256

; hashes using these schemes will automatically be re-hashed
; when the user logs in (currently all django 1.0 hashes)
deprecated =
    django_pbkdf2_sha1, django_salted_sha1, django_salted_md5,
    django_des_crypt, hex_md5

; sets some common options, including minimum rounds for two primary hashes.
; if a hash has less than this number of rounds, it will be re-hashed.
all__vary_rounds = 0.05
sha512_crypt__min_rounds = 80000
django_pbkdf2_sha256__min_rounds = 10000

; set somewhat stronger iteration counts for ``User.is_staff``
staff__sha512_crypt__default_rounds = 100000
staff__django_pbkdf2_sha256__default_rounds = 12500

; and even stronger ones for ``User.is_superuser``
superuser__sha512_crypt__default_rounds = 120000
superuser__django_pbkdf2_sha256__default_rounds = 15000
"""

#=============================================================================
# translating passlib names <-> hasher names
#=============================================================================

# prefix used to shoehorn passlib's handler names into django hasher namespace;
# allows get_hasher() to be meaningfully called even if passlib handler
# is the one being used.
PASSLIB_HASHER_PREFIX = "passlib_"

# prefix all the django-specific hash formats are stored under w/in passlib;
# all of these hashes should expose their hasher name via ``.django_name``.
DJANGO_PASSLIB_PREFIX = "django_"

# non-django-specific hashes which also expose ``.django_name``.
_other_django_hashes = ["hex_md5"]

def passlib_to_hasher_name(passlib_name):
    """convert passlib handler name -> hasher name"""
    handler = get_crypt_handler(passlib_name)
    if hasattr(handler, "django_name"):
        return handler.django_name
    return PASSLIB_HASHER_PREFIX + passlib_name

def hasher_to_passlib_name(hasher_name):
    """convert hasher name -> passlib handler name"""
    if hasher_name.startswith(PASSLIB_HASHER_PREFIX):
        return hasher_name[len(PASSLIB_HASHER_PREFIX):]
    if hasher_name == "unsalted_sha1":
        # django 1.4.6+ uses a separate hasher for "sha1$$digest" hashes,
        # but passlib just reuses the "sha1$salt$digest" handler.
        hasher_name = "sha1"
    for name in list_crypt_handlers():
        if name.startswith(DJANGO_PASSLIB_PREFIX) or name in _other_django_hashes:
            handler = get_crypt_handler(name)
            if getattr(handler, "django_name", None) == hasher_name:
                return name
    # XXX: this should only happen for custom hashers that have been registered.
    #      _HasherHandler (below) is work in progress that would fix this.
    raise ValueError("can't translate hasher name to passlib name: %r" %
                     hasher_name)

#=============================================================================
# wrapping passlib handlers as django hashers
#=============================================================================
_GEN_SALT_SIGNAL = "--!!!generate-new-salt!!!--"

class _HasherWrapper(object):
    """helper for wrapping passlib handlers in Hasher-compatible class."""

    # filled in by subclass, drives the other methods.
    passlib_handler = None
    iterations = None

    @classproperty
    def algorithm(cls):
        assert not hasattr(cls.passlib_handler, "django_name")
        return PASSLIB_HASHER_PREFIX + cls.passlib_handler.name

    def salt(self):
        # NOTE: passlib's handler.encrypt() should generate new salt each time,
        #       so this just returns a special constant which tells
        #       encode() (below) not to pass a salt keyword along.
        return _GEN_SALT_SIGNAL

    def verify(self, password, encoded):
        return self.passlib_handler.verify(password, encoded)

    def encode(self, password, salt=None, iterations=None):
        kwds = {}
        if salt is not None and salt != _GEN_SALT_SIGNAL:
            kwds['salt'] = salt
        if iterations is not None:
            kwds['rounds'] = iterations
        elif self.iterations is not None:
            kwds['rounds'] = self.iterations
        return self.passlib_handler.encrypt(password, **kwds)

    _translate_kwds = dict(checksum="hash", rounds="iterations")

    def safe_summary(self, encoded):
        from django.contrib.auth.hashers import mask_hash
        from django.utils.translation import ugettext_noop as _
        from django.utils.datastructures import SortedDict
        handler = self.passlib_handler
        items = [
            # since this is user-facing, we're reporting passlib's name,
            # without the distracting PASSLIB_HASHER_PREFIX prepended.
            (_('algorithm'), handler.name),
        ]
        if hasattr(handler, "parsehash"):
            kwds = handler.parsehash(encoded, sanitize=mask_hash)
            for key, value in iteritems(kwds):
                key = self._translate_kwds.get(key, key)
                items.append((_(key), value))
        return SortedDict(items)

    # added in django 1.6
    def must_update(self, encoded):
        # TODO: would like to do something useful here,
        #       but would require access to password context,
        #       which would mean a serious recoding of this ext.
        return False

# cache of hasher wrappers generated by get_passlib_hasher()
_hasher_cache = WeakKeyDictionary()

def get_passlib_hasher(handler, algorithm=None):
    """create *Hasher*-compatible wrapper for specified passlib hash.

    This takes in the name of a passlib hash (or the handler object itself),
    and returns a wrapper instance which should be compatible with
    Django 1.4's Hashers framework.

    If the named hash corresponds to one of Django's builtin hashers,
    an instance of the real hasher class will be returned.

    Note that the format of the handler won't be altered,
    so will probably not be compatible with Django's algorithm format,
    so the monkeypatch provided by this plugin must have been applied.

    .. note::
        This function requires Django 1.4 or later.
    """
    if DJANGO_VERSION < (1,4):
        raise RuntimeError("get_passlib_hasher() requires Django >= 1.4")
    if isinstance(handler, str):
        handler = get_crypt_handler(handler)
    if hasattr(handler, "django_name"):
        # return native hasher instance
        # XXX: should add this to _hasher_cache[]
        name = handler.django_name
        if name == "sha1" and algorithm == "unsalted_sha1":
            # django 1.4.6+ uses a separate hasher for "sha1$$digest" hashes,
            # but passlib just reuses the "sha1$salt$digest" handler.
            # we want to resolve to correct django hasher.
            name = algorithm
        return _get_hasher(name)
    if handler.name == "django_disabled":
        raise ValueError("can't wrap unusable-password handler")
    try:
        return _hasher_cache[handler]
    except KeyError:
        name = "Passlib_%s_PasswordHasher" % handler.name.title()
        cls = type(name, (_HasherWrapper,), dict(passlib_handler=handler))
        hasher = _hasher_cache[handler] = cls()
        return hasher

def _get_hasher(algorithm):
    """wrapper to call django.contrib.auth.hashers:get_hasher()"""
    import sys
    module = sys.modules.get("passlib.ext.django.models")
    if module is None:
        # we haven't patched django, so just import directly
        from django.contrib.auth.hashers import get_hasher
    else:
        # we've patched django, so have to use patch manager to retrieve
        # original get_hasher() function...
        get_hasher = module._manager.getorig("django.contrib.auth.hashers:get_hasher")
    return get_hasher(algorithm)

#=============================================================================
# adapting django hashers -> passlib handlers
#=============================================================================
# TODO: this code probably halfway works, mainly just needs
#       a routine to read HASHERS and PREFERRED_HASHER.

##from passlib.registry import register_crypt_handler
##from passlib.utils import classproperty, to_native_str, to_unicode
##from passlib.utils.compat import unicode
##
##
##class _HasherHandler(object):
##    "helper for wrapping Hasher instances as passlib handlers"
##    # FIXME: this generic wrapper doesn't handle custom settings
##    # FIXME: genconfig / genhash not supported.
##
##    def __init__(self, hasher):
##        self.django_hasher = hasher
##        if hasattr(hasher, "iterations"):
##            # assume encode() accepts an "iterations" parameter.
##            # fake min/max rounds
##            self.min_rounds = 1
##            self.max_rounds = 0xFFFFffff
##            self.default_rounds = self.django_hasher.iterations
##            self.setting_kwds += ("rounds",)
##
##    # hasher instance - filled in by constructor
##    django_hasher = None
##
##    setting_kwds = ("salt",)
##    context_kwds = ()
##
##    @property
##    def name(self):
##        # XXX: need to make sure this wont' collide w/ builtin django hashes.
##        #      maybe by renaming this to django compatible aliases?
##        return DJANGO_PASSLIB_PREFIX + self.django_name
##
##    @property
##    def django_name(self):
##        # expose this so hasher_to_passlib_name() extracts original name
##        return self.django_hasher.algorithm
##
##    @property
##    def ident(self):
##        # this should always be correct, as django relies on ident prefix.
##        return unicode(self.django_name + "$")
##
##    @property
##    def identify(self, hash):
##        # this should always work, as django relies on ident prefix.
##        return to_unicode(hash, "latin-1", "hash").startswith(self.ident)
##
##    @property
##    def genconfig(self):
##        # XXX: not sure how to support this.
##        return None
##
##    @property
##    def genhash(self, secret, config):
##        if config is not None:
##            # XXX: not sure how to support this.
##            raise NotImplementedError("genhash() for hashers not implemented")
##        return self.encrypt(secret)
##
##    @property
##    def encrypt(self, secret, salt=None, **kwds):
##        # NOTE: from how make_password() is coded, all hashers
##        #       should have salt param. but only some will have
##        #       'iterations' parameter.
##        opts = {}
##        if 'rounds' in self.setting_kwds and 'rounds' in kwds:
##            opts['iterations'] = kwds.pop("rounds")
##        if kwds:
##            raise TypeError("unexpected keyword arguments: %r" % list(kwds))
##        if isinstance(secret, unicode):
##            secret = secret.encode("utf-8")
##        if salt is None:
##            salt = self.django_hasher.salt()
##        return to_native_str(self.django_hasher(secret, salt, **opts))
##
##    @property
##    def verify(self, secret, hash):
##        hash = to_native_str(hash, "utf-8", "hash")
##        if isinstance(secret, unicode):
##            secret = secret.encode("utf-8")
##        return self.django_hasher.verify(secret, hash)
##
##def register_hasher(hasher):
##    handler = _HasherHandler(hasher)
##    register_crypt_handler(handler)
##    return handler

#=============================================================================
# monkeypatch helpers
#=============================================================================
# private singleton indicating lack-of-value
_UNSET = object()

class _PatchManager(object):
    """helper to manage monkeypatches and run sanity checks"""

    # NOTE: this could easily use a dict interface,
    #       but keeping it distinct to make clear that it's not a dict,
    #       since it has important side-effects.

    #===================================================================
    # init and support
    #===================================================================
    def __init__(self, log=None):
        # map of key -> (original value, patched value)
        # original value may be _UNSET
        self.log = log or logging.getLogger(__name__ + "._PatchManager")
        self._state = {}

    # bool value tests if any patches are currently applied.
    __bool__ = __nonzero__ = lambda self: bool(self._state)

    def _import_path(self, path):
        """retrieve obj and final attribute name from resource path"""
        name, attr = path.split(":")
        obj = __import__(name, fromlist=[attr], level=0)
        while '.' in attr:
           head, attr = attr.split(".", 1)
           obj = getattr(obj, head)
        return obj, attr

    @staticmethod
    def _is_same_value(left, right):
        """check if two values are the same (stripping method wrappers, etc)"""
        return get_method_function(left) == get_method_function(right)

    #===================================================================
    # reading
    #===================================================================
    def _get_path(self, key, default=_UNSET):
        obj, attr = self._import_path(key)
        return getattr(obj, attr, default)

    def get(self, path, default=None):
        """return current value for path"""
        return self._get_path(path, default)

    def getorig(self, path, default=None):
        """return original (unpatched) value for path"""
        try:
            value, _= self._state[path]
        except KeyError:
            value = self._get_path(path)
        return default if value is _UNSET else value

    def check_all(self, strict=False):
        """run sanity check on all keys, issue warning if out of sync"""
        same = self._is_same_value
        for path, (orig, expected) in iteritems(self._state):
            if same(self._get_path(path), expected):
                continue
            msg = "another library has patched resource: %r" % path
            if strict:
                raise RuntimeError(msg)
            else:
                warn(msg, PasslibRuntimeWarning)

    #===================================================================
    # patching
    #===================================================================
    def _set_path(self, path, value):
        obj, attr = self._import_path(path)
        if value is _UNSET:
            if hasattr(obj, attr):
                delattr(obj, attr)
        else:
            setattr(obj, attr, value)

    def patch(self, path, value):
        """monkeypatch object+attr at <path> to have <value>, stores original"""
        assert value != _UNSET
        current = self._get_path(path)
        try:
            orig, expected = self._state[path]
        except KeyError:
            self.log.debug("patching resource: %r", path)
            orig = current
        else:
            self.log.debug("modifying resource: %r", path)
            if not self._is_same_value(current, expected):
                warn("overridding resource another library has patched: %r"
                     % path, PasslibRuntimeWarning)
        self._set_path(path, value)
        self._state[path] = (orig, value)

    ##def patch_many(self, **kwds):
    ##    "override specified resources with new values"
    ##    for path, value in iteritems(kwds):
    ##        self.patch(path, value)

    def monkeypatch(self, parent, name=None, enable=True):
        """function decorator which patches function of same name in <parent>"""
        def builder(func):
            if enable:
                sep = "." if ":" in parent else ":"
                path = parent + sep + (name or func.__name__)
                self.patch(path, func)
            return func
        return builder

    #===================================================================
    # unpatching
    #===================================================================
    def unpatch(self, path, unpatch_conflicts=True):
        try:
            orig, expected = self._state[path]
        except KeyError:
            return
        current = self._get_path(path)
        self.log.debug("unpatching resource: %r", path)
        if not self._is_same_value(current, expected):
            if unpatch_conflicts:
                warn("reverting resource another library has patched: %r"
                     % path, PasslibRuntimeWarning)
            else:
                warn("not reverting resource another library has patched: %r"
                     % path, PasslibRuntimeWarning)
                del self._state[path]
                return
        self._set_path(path, orig)
        del self._state[path]

    def unpatch_all(self, **kwds):
        for key in list(self._state):
            self.unpatch(key, **kwds)

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# eof
#=============================================================================
