"""passlib.handlers.misc - misc generic handlers
"""
#=============================================================================
# imports
#=============================================================================
# core
import sys
import logging; log = logging.getLogger(__name__)
from warnings import warn
# site
# pkg
from passlib.utils import to_native_str, consteq
from passlib.utils.compat import bytes, unicode, u, b, base_string_types
import passlib.utils.handlers as uh
# local
__all__ = [
    "unix_disabled",
    "unix_fallback",
    "plaintext",
]

#=============================================================================
# handler
#=============================================================================
class unix_fallback(uh.StaticHandler):
    """This class provides the fallback behavior for unix shadow files, and follows the :ref:`password-hash-api`.

    This class does not implement a hash, but instead provides fallback
    behavior as found in /etc/shadow on most unix variants.
    If used, should be the last scheme in the context.

    * this class will positive identify all hash strings.
    * for security, newly encrypted passwords will hash to ``!``.
    * it rejects all passwords if the hash is NOT an empty string (``!`` or ``*`` are frequently used).
    * by default it rejects all passwords if the hash is an empty string,
      but if ``enable_wildcard=True`` is passed to verify(),
      all passwords will be allowed through if the hash is an empty string.

    .. deprecated:: 1.6
        This has been deprecated due to its "wildcard" feature,
        and will be removed in Passlib 1.8. Use :class:`unix_disabled` instead.
    """
    name = "unix_fallback"
    context_kwds = ("enable_wildcard",)

    @classmethod
    def identify(cls, hash):
        if isinstance(hash, base_string_types):
            return True
        else:
            raise uh.exc.ExpectedStringError(hash, "hash")

    def __init__(self, enable_wildcard=False, **kwds):
        warn("'unix_fallback' is deprecated, "
             "and will be removed in Passlib 1.8; "
             "please use 'unix_disabled' instead.",
             DeprecationWarning)
        super(unix_fallback, self).__init__(**kwds)
        self.enable_wildcard = enable_wildcard

    @classmethod
    def genhash(cls, secret, config):
        # override default to preserve checksum
        if config is None:
            return cls.encrypt(secret)
        else:
            uh.validate_secret(secret)
            self = cls.from_string(config)
            self.checksum = self._calc_checksum(secret)
            return self.to_string()

    def _calc_checksum(self, secret):
        if self.checksum:
            # NOTE: hash will generally be "!", but we want to preserve
            # it in case it's something else, like "*".
            return self.checksum
        else:
            return u("!")

    @classmethod
    def verify(cls, secret, hash, enable_wildcard=False):
        uh.validate_secret(secret)
        if not isinstance(hash, base_string_types):
            raise uh.exc.ExpectedStringError(hash, "hash")
        elif hash:
            return False
        else:
            return enable_wildcard

_MARKER_CHARS = u("*!")
_MARKER_BYTES = b("*!")

class unix_disabled(uh.PasswordHash):
    """This class provides disabled password behavior for unix shadow files,
    and follows the :ref:`password-hash-api`.

    This class does not implement a hash, but instead matches the "disabled account"
    strings found in ``/etc/shadow`` on most Unix variants. "encrypting" a password
    will simply return the disabled account marker. It will reject all passwords,
    no matter the hash string. The :meth:`~passlib.ifc.PasswordHash.encrypt`
    method supports one optional keyword:

    :type marker: str
    :param marker:
        Optional marker string which overrides the platform default
        used to indicate a disabled account.

        If not specified, this will default to ``"*"`` on BSD systems,
        and use the Linux default ``"!"`` for all other platforms.
        (:attr:`!unix_disabled.default_marker` will contain the default value)

    .. versionadded:: 1.6
        This class was added as a replacement for the now-deprecated
        :class:`unix_fallback` class, which had some undesirable features.
    """
    name = "unix_disabled"
    setting_kwds = ("marker",)
    context_kwds = ()

    if 'bsd' in sys.platform: # pragma: no cover -- runtime detection
        default_marker = u("*")
    else:
        # use the linux default for other systems
        # (glibc also supports adding old hash after the marker
        # so it can be restored later).
        default_marker = u("!")

    @classmethod
    def identify(cls, hash):
        # NOTE: technically, anything in the /etc/shadow password field
        #       which isn't valid crypt() output counts as "disabled".
        #       but that's rather ambiguous, and it's hard to predict what
        #       valid output is for unknown crypt() implementations.
        #       so to be on the safe side, we only match things *known*
        #       to be disabled field indicators, and will add others
        #       as they are found. things beginning w/ "$" should *never* match.
        #
        # things currently matched:
        #       * linux uses "!"
        #       * bsd uses "*"
        #       * linux may use "!" + hash to disable but preserve original hash
        #       * linux counts empty string as "any password"
        if isinstance(hash, unicode):
            start = _MARKER_CHARS
        elif isinstance(hash, bytes):
            start = _MARKER_BYTES
        else:
            raise uh.exc.ExpectedStringError(hash, "hash")
        return not hash or hash[0] in start

    @classmethod
    def encrypt(cls, secret, marker=None):
        return cls.genhash(secret, None, marker)

    @classmethod
    def verify(cls, secret, hash):
        uh.validate_secret(secret)
        if not cls.identify(hash): # handles typecheck
            raise uh.exc.InvalidHashError(cls)
        return False

    @classmethod
    def genconfig(cls):
        return None

    @classmethod
    def genhash(cls, secret, config, marker=None):
        uh.validate_secret(secret)
        if config is not None and not cls.identify(config): # handles typecheck
            raise uh.exc.InvalidHashError(cls)
        if config:
            # we want to preserve the existing str,
            # since it might contain a disabled password hash ("!" + hash)
            return to_native_str(config, param="config")
        # if None or empty string, replace with marker
        if marker:
            if not cls.identify(marker):
                raise ValueError("invalid marker: %r" % marker)
        else:
            marker = cls.default_marker
            assert marker and cls.identify(marker)
        return to_native_str(marker, param="marker")

class plaintext(uh.PasswordHash):
    """This class stores passwords in plaintext, and follows the :ref:`password-hash-api`.

    The :meth:`~passlib.ifc.PasswordHash.encrypt`, :meth:`~passlib.ifc.PasswordHash.genhash`, and :meth:`~passlib.ifc.PasswordHash.verify` methods all require the
    following additional contextual keyword:

    :type encoding: str
    :param encoding:
        This controls the character encoding to use (defaults to ``utf-8``).

        This encoding will be used to encode :class:`!unicode` passwords
        under Python 2, and decode :class:`!bytes` hashes under Python 3.

    .. versionchanged:: 1.6
        The ``encoding`` keyword was added.
    """
    # NOTE: this is subclassed by ldap_plaintext

    name = "plaintext"
    setting_kwds = ()
    context_kwds = ("encoding",)
    default_encoding = "utf-8"

    @classmethod
    def identify(cls, hash):
        if isinstance(hash, base_string_types):
            return True
        else:
            raise uh.exc.ExpectedStringError(hash, "hash")

    @classmethod
    def encrypt(cls, secret, encoding=None):
        uh.validate_secret(secret)
        if not encoding:
            encoding = cls.default_encoding
        return to_native_str(secret, encoding, "secret")

    @classmethod
    def verify(cls, secret, hash, encoding=None):
        if not encoding:
            encoding = cls.default_encoding
        hash = to_native_str(hash, encoding, "hash")
        if not cls.identify(hash):
            raise uh.exc.InvalidHashError(cls)
        return consteq(cls.encrypt(secret, encoding), hash)

    @classmethod
    def genconfig(cls):
        return None

    @classmethod
    def genhash(cls, secret, hash, encoding=None):
        if hash is not None and not cls.identify(hash):
            raise uh.exc.InvalidHashError(cls)
        return cls.encrypt(secret, encoding)

#=============================================================================
# eof
#=============================================================================
