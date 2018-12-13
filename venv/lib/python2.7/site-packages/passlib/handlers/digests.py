"""passlib.handlers.digests - plain hash digests
"""
#=============================================================================
# imports
#=============================================================================
# core
import hashlib
import logging; log = logging.getLogger(__name__)
from warnings import warn
# site
# pkg
from passlib.utils import to_native_str, to_bytes, render_bytes, consteq
from passlib.utils.compat import bascii_to_str, bytes, unicode, str_to_uascii
import passlib.utils.handlers as uh
from passlib.utils.md4 import md4
# local
__all__ = [
    "create_hex_hash",
    "hex_md4",
    "hex_md5",
    "hex_sha1",
    "hex_sha256",
    "hex_sha512",
]

#=============================================================================
# helpers for hexadecimal hashes
#=============================================================================
class HexDigestHash(uh.StaticHandler):
    """this provides a template for supporting passwords stored as plain hexadecimal hashes"""
    #===================================================================
    # class attrs
    #===================================================================
    _hash_func = None # hash function to use - filled in by create_hex_hash()
    checksum_size = None # filled in by create_hex_hash()
    checksum_chars = uh.HEX_CHARS

    #===================================================================
    # methods
    #===================================================================
    @classmethod
    def _norm_hash(cls, hash):
        return hash.lower()

    def _calc_checksum(self, secret):
        if isinstance(secret, unicode):
            secret = secret.encode("utf-8")
        return str_to_uascii(self._hash_func(secret).hexdigest())

    #===================================================================
    # eoc
    #===================================================================

def create_hex_hash(hash, digest_name, module=__name__):
    # NOTE: could set digest_name=hash.name for cpython, but not for some other platforms.
    h = hash()
    name = "hex_" + digest_name
    return type(name, (HexDigestHash,), dict(
        name=name,
        __module__=module, # so ABCMeta won't clobber it
        _hash_func=staticmethod(hash), # sometimes it's a function, sometimes not. so wrap it.
        checksum_size=h.digest_size*2,
        __doc__="""This class implements a plain hexadecimal %s hash, and follows the :ref:`password-hash-api`.

It supports no optional or contextual keywords.
""" % (digest_name,)
    ))

#=============================================================================
# predefined handlers
#=============================================================================
hex_md4     = create_hex_hash(md4,              "md4")
hex_md5     = create_hex_hash(hashlib.md5,      "md5")
hex_md5.django_name = "unsalted_md5"
hex_sha1    = create_hex_hash(hashlib.sha1,     "sha1")
hex_sha256  = create_hex_hash(hashlib.sha256,   "sha256")
hex_sha512  = create_hex_hash(hashlib.sha512,   "sha512")

#=============================================================================
# htdigest
#=============================================================================
class htdigest(uh.PasswordHash):
    """htdigest hash function.

    .. todo::
        document this hash
    """
    name = "htdigest"
    setting_kwds = ()
    context_kwds = ("user", "realm", "encoding")
    default_encoding = "utf-8"

    @classmethod
    def encrypt(cls, secret, user, realm, encoding=None):
        # NOTE: this was deliberately written so that raw bytes are passed through
        # unchanged, the encoding kwd is only used to handle unicode values.
        if not encoding:
            encoding = cls.default_encoding
        uh.validate_secret(secret)
        if isinstance(secret, unicode):
            secret = secret.encode(encoding)
        user = to_bytes(user, encoding, "user")
        realm = to_bytes(realm, encoding, "realm")
        data = render_bytes("%s:%s:%s", user, realm, secret)
        return hashlib.md5(data).hexdigest()

    @classmethod
    def _norm_hash(cls, hash):
        """normalize hash to native string, and validate it"""
        hash = to_native_str(hash, param="hash")
        if len(hash) != 32:
            raise uh.exc.MalformedHashError(cls, "wrong size")
        for char in hash:
            if char not in uh.LC_HEX_CHARS:
                raise uh.exc.MalformedHashError(cls, "invalid chars in hash")
        return hash

    @classmethod
    def verify(cls, secret, hash, user, realm, encoding="utf-8"):
        hash = cls._norm_hash(hash)
        other = cls.encrypt(secret, user, realm, encoding)
        return consteq(hash, other)

    @classmethod
    def identify(cls, hash):
        try:
            cls._norm_hash(hash)
        except ValueError:
            return False
        return True

    @classmethod
    def genconfig(cls):
        return None

    @classmethod
    def genhash(cls, secret, config, user, realm, encoding="utf-8"):
        if config is not None:
            cls._norm_hash(config)
        return cls.encrypt(secret, user, realm, encoding)

#=============================================================================
# eof
#=============================================================================
