"""passlib.handlers.cisco - Cisco password hashes"""
#=============================================================================
# imports
#=============================================================================
# core
from binascii import hexlify, unhexlify
from hashlib import md5
import logging; log = logging.getLogger(__name__)
from warnings import warn
# site
# pkg
from passlib.utils import h64, right_pad_string, to_unicode
from passlib.utils.compat import b, bascii_to_str, bytes, unicode, u, join_byte_values, \
             join_byte_elems, byte_elem_value, iter_byte_values, uascii_to_str, str_to_uascii
import passlib.utils.handlers as uh
# local
__all__ = [
    "cisco_pix",
    "cisco_type7",
]

#=============================================================================
# cisco pix firewall hash
#=============================================================================
class cisco_pix(uh.HasUserContext, uh.StaticHandler):
    """This class implements the password hash used by Cisco PIX firewalls,
    and follows the :ref:`password-hash-api`.
    It does a single round of hashing, and relies on the username
    as the salt.

    The :meth:`~passlib.ifc.PasswordHash.encrypt`, :meth:`~passlib.ifc.PasswordHash.genhash`, and :meth:`~passlib.ifc.PasswordHash.verify` methods
    have the following extra keyword:

    :type user: str
    :param user:
        String containing name of user account this password is associated with.

        This is *required* in order to correctly hash passwords associated
        with a user account on the Cisco device, as it is used to salt
        the hash.

        Conversely, this *must* be omitted or set to ``""`` in order to correctly
        hash passwords which don't have an associated user account
        (such as the "enable" password).
    """
    #===================================================================
    # class attrs
    #===================================================================
    name = "cisco_pix"
    checksum_size = 16
    checksum_chars = uh.HASH64_CHARS

    #===================================================================
    # methods
    #===================================================================
    def _calc_checksum(self, secret):
        if isinstance(secret, unicode):
            # XXX: no idea what unicode policy is, but all examples are
            # 7-bit ascii compatible, so using UTF-8
            secret = secret.encode("utf-8")

        user = self.user
        if user:
            # not positive about this, but it looks like per-user
            # accounts use the first 4 chars of the username as the salt,
            # whereas global "enable" passwords don't have any salt at all.
            if isinstance(user, unicode):
                user = user.encode("utf-8")
            secret += user[:4]

        # null-pad or truncate to 16 bytes
        secret = right_pad_string(secret, 16)

        # md5 digest
        hash = md5(secret).digest()

        # drop every 4th byte
        hash = join_byte_elems(c for i,c in enumerate(hash) if i & 3 < 3)

        # encode using Hash64
        return h64.encode_bytes(hash).decode("ascii")

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# type 7
#=============================================================================
class cisco_type7(uh.GenericHandler):
    """This class implements the Type 7 password encoding used by Cisco IOS,
    and follows the :ref:`password-hash-api`.
    It has a simple 4-5 bit salt, but is nonetheless a reversible encoding
    instead of a real hash.

    The :meth:`~passlib.ifc.PasswordHash.encrypt` and :meth:`~passlib.ifc.PasswordHash.genhash` methods
    have the following optional keywords:

    :type salt: int
    :param salt:
        This may be an optional salt integer drawn from ``range(0,16)``.
        If omitted, one will be chosen at random.

    :type relaxed: bool
    :param relaxed:
        By default, providing an invalid value for one of the other
        keywords will result in a :exc:`ValueError`. If ``relaxed=True``,
        and the error can be corrected, a :exc:`~passlib.exc.PasslibHashWarning`
        will be issued instead. Correctable errors include
        ``salt`` values that are out of range.

    Note that while this class outputs digests in upper-case hexadecimal,
    it will accept lower-case as well.

    This class also provides the following additional method:

    .. automethod:: decode
    """
    #===================================================================
    # class attrs
    #===================================================================
    name = "cisco_type7"
    setting_kwds = ("salt",)
    checksum_chars = uh.UPPER_HEX_CHARS

    # NOTE: encoding could handle max_salt_value=99, but since key is only 52
    #       chars in size, not sure what appropriate behavior is for that edge case.
    min_salt_value = 0
    max_salt_value = 52

    #===================================================================
    # methods
    #===================================================================
    @classmethod
    def genconfig(cls):
        return None

    @classmethod
    def genhash(cls, secret, config):
        # special case to handle ``config=None`` in same style as StaticHandler
        if config is None:
            return cls.encrypt(secret)
        else:
            return super(cisco_type7, cls).genhash(secret, config)

    @classmethod
    def from_string(cls, hash):
        hash = to_unicode(hash, "ascii", "hash")
        if len(hash) < 2:
            raise uh.exc.InvalidHashError(cls)
        salt = int(hash[:2]) # may throw ValueError
        return cls(salt=salt, checksum=hash[2:].upper())

    def __init__(self, salt=None, **kwds):
        super(cisco_type7, self).__init__(**kwds)
        self.salt = self._norm_salt(salt)

    def _norm_salt(self, salt):
        """the salt for this algorithm is an integer 0-52, not a string"""
        # XXX: not entirely sure that values >15 are valid, so for
        # compatibility we don't output those values, but we do accept them.
        if salt is None:
            if self.use_defaults:
                salt = self._generate_salt()
            else:
                raise TypeError("no salt specified")
        if not isinstance(salt, int):
            raise uh.exc.ExpectedTypeError(salt, "integer", "salt")
        if salt < 0 or salt > self.max_salt_value:
            msg = "salt/offset must be in 0..52 range"
            if self.relaxed:
                warn(msg, uh.PasslibHashWarning)
                salt = 0 if salt < 0 else self.max_salt_value
            else:
                raise ValueError(msg)
        return salt

    def _generate_salt(self):
        return uh.rng.randint(0, 15)

    def to_string(self):
        return "%02d%s" % (self.salt, uascii_to_str(self.checksum))

    def _calc_checksum(self, secret):
        # XXX: no idea what unicode policy is, but all examples are
        # 7-bit ascii compatible, so using UTF-8
        if isinstance(secret, unicode):
            secret = secret.encode("utf-8")
        return hexlify(self._cipher(secret, self.salt)).decode("ascii").upper()

    @classmethod
    def decode(cls, hash, encoding="utf-8"):
        """decode hash, returning original password.

        :arg hash: encoded password
        :param encoding: optional encoding to use (defaults to ``UTF-8``).
        :returns: password as unicode
        """
        self = cls.from_string(hash)
        tmp = unhexlify(self.checksum.encode("ascii"))
        raw = self._cipher(tmp, self.salt)
        return raw.decode(encoding) if encoding else raw

    # type7 uses a xor-based vingere variant, using the following secret key:
    _key = u("dsfd;kfoA,.iyewrkldJKDHSUBsgvca69834ncxv9873254k;fg87")

    @classmethod
    def _cipher(cls, data, salt):
        """xor static key against data - encrypts & decrypts"""
        key = cls._key
        key_size = len(key)
        return join_byte_values(
            value ^ ord(key[(salt + idx) % key_size])
            for idx, value in enumerate(iter_byte_values(data))
        )

#=============================================================================
# eof
#=============================================================================
