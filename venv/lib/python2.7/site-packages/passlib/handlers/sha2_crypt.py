"""passlib.handlers.sha2_crypt - SHA256-Crypt / SHA512-Crypt"""
#=============================================================================
# imports
#=============================================================================
# core
import hashlib
import logging; log = logging.getLogger(__name__)
from warnings import warn
# site
# pkg
from passlib.utils import classproperty, h64, safe_crypt, test_crypt, \
                          repeat_string, to_unicode
from passlib.utils.compat import b, bytes, byte_elem_value, irange, u, \
                                 uascii_to_str, unicode
import passlib.utils.handlers as uh
# local
__all__ = [
    "sha512_crypt",
    "sha256_crypt",
]

#=============================================================================
# pure-python backend, used by both sha256_crypt & sha512_crypt
# when crypt.crypt() backend is not available.
#=============================================================================
_BNULL = b('\x00')

# pre-calculated offsets used to speed up C digest stage (see notes below).
# sequence generated using the following:
    ##perms_order = "p,pp,ps,psp,sp,spp".split(",")
    ##def offset(i):
    ##    key = (("p" if i % 2 else "") + ("s" if i % 3 else "") +
    ##        ("p" if i % 7 else "") + ("" if i % 2 else "p"))
    ##    return perms_order.index(key)
    ##_c_digest_offsets = [(offset(i), offset(i+1)) for i in range(0,42,2)]
_c_digest_offsets = (
    (0, 3), (5, 1), (5, 3), (1, 2), (5, 1), (5, 3), (1, 3),
    (4, 1), (5, 3), (1, 3), (5, 0), (5, 3), (1, 3), (5, 1),
    (4, 3), (1, 3), (5, 1), (5, 2), (1, 3), (5, 1), (5, 3),
    )

# map used to transpose bytes when encoding final sha256_crypt digest
_256_transpose_map = (
    20, 10,  0, 11,  1, 21,  2, 22, 12, 23, 13,  3, 14,  4, 24,  5,
    25, 15, 26, 16,  6, 17,  7, 27,  8, 28, 18, 29, 19,  9, 30, 31,
)

# map used to transpose bytes when encoding final sha512_crypt digest
_512_transpose_map = (
    42, 21,  0,  1, 43, 22, 23,  2, 44, 45, 24,  3,  4, 46, 25, 26,
     5, 47, 48, 27,  6,  7, 49, 28, 29,  8, 50, 51, 30,  9, 10, 52,
    31, 32, 11, 53, 54, 33, 12, 13, 55, 34, 35, 14, 56, 57, 36, 15,
    16, 58, 37, 38, 17, 59, 60, 39, 18, 19, 61, 40, 41, 20, 62, 63,
)

def _raw_sha2_crypt(pwd, salt, rounds, use_512=False):
    """perform raw sha256-crypt / sha512-crypt

    this function provides a pure-python implementation of the internals
    for the SHA256-Crypt and SHA512-Crypt algorithms; it doesn't
    handle any of the parsing/validation of the hash strings themselves.

    :arg pwd: password chars/bytes to encrypt
    :arg salt: salt chars to use
    :arg rounds: linear rounds cost
    :arg use_512: use sha512-crypt instead of sha256-crypt mode

    :returns:
        encoded checksum chars
    """
    #===================================================================
    # init & validate inputs
    #===================================================================

    # validate secret
    if isinstance(pwd, unicode):
        # XXX: not sure what official unicode policy is, using this as default
        pwd = pwd.encode("utf-8")
    assert isinstance(pwd, bytes)
    if _BNULL in pwd:
        raise uh.exc.NullPasswordError(sha512_crypt if use_512 else sha256_crypt)
    pwd_len = len(pwd)

    # validate rounds
    assert 1000 <= rounds <= 999999999, "invalid rounds"
        # NOTE: spec says out-of-range rounds should be clipped, instead of
        # causing an error. this function assumes that's been taken care of
        # by the handler class.

    # validate salt
    assert isinstance(salt, unicode), "salt not unicode"
    salt = salt.encode("ascii")
    salt_len = len(salt)
    assert salt_len < 17, "salt too large"
        # NOTE: spec says salts larger than 16 bytes should be truncated,
        # instead of causing an error. this function assumes that's been
        # taken care of by the handler class.

    # load sha256/512 specific constants
    if use_512:
        hash_const = hashlib.sha512
        hash_len = 64
        transpose_map = _512_transpose_map
    else:
        hash_const = hashlib.sha256
        hash_len = 32
        transpose_map = _256_transpose_map

    #===================================================================
    # digest B - used as subinput to digest A
    #===================================================================
    db = hash_const(pwd + salt + pwd).digest()

    #===================================================================
    # digest A - used to initialize first round of digest C
    #===================================================================
    # start out with pwd + salt
    a_ctx = hash_const(pwd + salt)
    a_ctx_update = a_ctx.update

    # add pwd_len bytes of b, repeating b as many times as needed.
    a_ctx_update(repeat_string(db, pwd_len))

    # for each bit in pwd_len: add b if it's 1, or pwd if it's 0
    i = pwd_len
    while i:
        a_ctx_update(db if i & 1 else pwd)
        i >>= 1

    # finish A
    da = a_ctx.digest()

    #===================================================================
    # digest P from password - used instead of password itself
    #                          when calculating digest C.
    #===================================================================
    if pwd_len < 64:
        # method this is faster under python, but uses O(pwd_len**2) memory
        # so we don't use it for larger passwords, to avoid a potential DOS.
        dp = repeat_string(hash_const(pwd * pwd_len).digest(), pwd_len)
    else:
        tmp_ctx = hash_const(pwd)
        tmp_ctx_update = tmp_ctx.update
        i = pwd_len-1
        while i:
            tmp_ctx_update(pwd)
            i -= 1
        dp = repeat_string(tmp_ctx.digest(), pwd_len)
    assert len(dp) == pwd_len

    #===================================================================
    # digest S  - used instead of salt itself when calculating digest C
    #===================================================================
    ds = hash_const(salt * (16 + byte_elem_value(da[0]))).digest()[:salt_len]
    assert len(ds) == salt_len, "salt_len somehow > hash_len!"

    #===================================================================
    # digest C - for a variable number of rounds, combine A, S, and P
    #            digests in various ways; in order to burn CPU time.
    #===================================================================

    # NOTE: the original SHA256/512-Crypt specification performs the C digest
    # calculation using the following loop:
    #
    ##dc = da
    ##i = 0
    ##while i < rounds:
    ##    tmp_ctx = hash_const(dp if i & 1 else dc)
    ##    if i % 3:
    ##        tmp_ctx.update(ds)
    ##    if i % 7:
    ##        tmp_ctx.update(dp)
    ##    tmp_ctx.update(dc if i & 1 else dp)
    ##    dc = tmp_ctx.digest()
    ##    i += 1
    #
    # The code Passlib uses (below) implements an equivalent algorithm,
    # it's just been heavily optimized to pre-calculate a large number
    # of things beforehand. It works off of a couple of observations
    # about the original algorithm:
    #
    # 1. each round is a combination of 'dc', 'ds', and 'dp'; determined
    #    by the whether 'i' a multiple of 2,3, and/or 7.
    # 2. since lcm(2,3,7)==42, the series of combinations will repeat
    #    every 42 rounds.
    # 3. even rounds 0-40 consist of 'hash(dc + round-specific-constant)';
    #    while odd rounds 1-41 consist of hash(round-specific-constant + dc)
    #
    # Using these observations, the following code...
    # * calculates the round-specific combination of ds & dp for each round 0-41
    # * runs through as many 42-round blocks as possible
    # * runs through as many pairs of rounds as possible for remaining rounds
    # * performs once last round if the total rounds should be odd.
    #
    # this cuts out a lot of the control overhead incurred when running the
    # original loop 40,000+ times in python, resulting in ~20% increase in
    # speed under CPython (though still 2x slower than glibc crypt)

    # prepare the 6 combinations of ds & dp which are needed
    # (order of 'perms' must match how _c_digest_offsets was generated)
    dp_dp = dp+dp
    dp_ds = dp+ds
    perms = [dp, dp_dp, dp_ds, dp_ds+dp, ds+dp, ds+dp_dp]

    # build up list of even-round & odd-round constants,
    # and store in 21-element list as (even,odd) pairs.
    data = [ (perms[even], perms[odd]) for even, odd in _c_digest_offsets]

    # perform as many full 42-round blocks as possible
    dc = da
    blocks, tail = divmod(rounds, 42)
    while blocks:
        for even, odd in data:
            dc = hash_const(odd + hash_const(dc + even).digest()).digest()
        blocks -= 1

    # perform any leftover rounds
    if tail:
        # perform any pairs of rounds
        pairs = tail>>1
        for even, odd in data[:pairs]:
            dc = hash_const(odd + hash_const(dc + even).digest()).digest()

        # if rounds was odd, do one last round (since we started at 0,
        # last round will be an even-numbered round)
        if tail & 1:
            dc = hash_const(dc + data[pairs][0]).digest()

    #===================================================================
    # encode digest using appropriate transpose map
    #===================================================================
    return h64.encode_transposed_bytes(dc, transpose_map).decode("ascii")

#=============================================================================
# handlers
#=============================================================================
_UROUNDS = u("rounds=")
_UDOLLAR = u("$")
_UZERO = u("0")

class _SHA2_Common(uh.HasManyBackends, uh.HasRounds, uh.HasSalt,
                   uh.GenericHandler):
    """class containing common code shared by sha256_crypt & sha512_crypt"""
    #===================================================================
    # class attrs
    #===================================================================
    # name - set by subclass
    setting_kwds = ("salt", "rounds", "implicit_rounds", "salt_size")
    # ident - set by subclass
    checksum_chars = uh.HASH64_CHARS
    # checksum_size - set by subclass

    min_salt_size = 0
    max_salt_size = 16
    salt_chars = uh.HASH64_CHARS

    min_rounds = 1000 # bounds set by spec
    max_rounds = 999999999 # bounds set by spec
    rounds_cost = "linear"

    _cdb_use_512 = False # flag for _calc_digest_builtin()
    _rounds_prefix = None # ident + _UROUNDS

    #===================================================================
    # methods
    #===================================================================
    implicit_rounds = False

    def __init__(self, implicit_rounds=None, **kwds):
        super(_SHA2_Common, self).__init__(**kwds)
        # if user calls encrypt() w/ 5000 rounds, default to compact form.
        if implicit_rounds is None:
            implicit_rounds = (self.use_defaults and self.rounds == 5000)
        self.implicit_rounds = implicit_rounds

    @classmethod
    def from_string(cls, hash):
        # basic format this parses -
        # $5$[rounds=<rounds>$]<salt>[$<checksum>]

        # TODO: this *could* use uh.parse_mc3(), except that the rounds
        # portion has a slightly different grammar.

        # convert to unicode, check for ident prefix, split on dollar signs.
        hash = to_unicode(hash, "ascii", "hash")
        ident = cls.ident
        if not hash.startswith(ident):
            raise uh.exc.InvalidHashError(cls)
        assert len(ident) == 3
        parts = hash[3:].split(_UDOLLAR)

        # extract rounds value
        if parts[0].startswith(_UROUNDS):
            assert len(_UROUNDS) == 7
            rounds = parts.pop(0)[7:]
            if rounds.startswith(_UZERO) and rounds != _UZERO:
                raise uh.exc.ZeroPaddedRoundsError(cls)
            rounds = int(rounds)
            implicit_rounds = False
        else:
            rounds = 5000
            implicit_rounds = True

        # rest should be salt and checksum
        if len(parts) == 2:
            salt, chk = parts
        elif len(parts) == 1:
            salt = parts[0]
            chk = None
        else:
            raise uh.exc.MalformedHashError(cls)

        # return new object
        return cls(
            rounds=rounds,
            salt=salt,
            checksum=chk or None,
            implicit_rounds=implicit_rounds,
            relaxed=not chk, # NOTE: relaxing parsing for config strings
                             # so that out-of-range rounds are clipped,
                             # since SHA2-Crypt spec treats them this way.
            )

    def to_string(self):
        if self.rounds == 5000 and self.implicit_rounds:
            hash = u("%s%s$%s") % (self.ident, self.salt,
                                   self.checksum or u(''))
        else:
            hash = u("%srounds=%d$%s$%s") % (self.ident, self.rounds,
                                             self.salt, self.checksum or u(''))
        return uascii_to_str(hash)

    #===================================================================
    # backends
    #===================================================================
    backends = ("os_crypt", "builtin")

    _has_backend_builtin = True

    # _has_backend_os_crypt - provided by subclass

    def _calc_checksum_builtin(self, secret):
        return _raw_sha2_crypt(secret, self.salt, self.rounds,
                               self._cdb_use_512)

    def _calc_checksum_os_crypt(self, secret):
        hash = safe_crypt(secret, self.to_string())
        if hash:
            # NOTE: avoiding full parsing routine via from_string().checksum,
            # and just extracting the bit we need.
            cs = self.checksum_size
            assert hash.startswith(self.ident) and hash[-cs-1] == _UDOLLAR
            return hash[-cs:]
        else:
            return self._calc_checksum_builtin(secret)

    #===================================================================
    # eoc
    #===================================================================

class sha256_crypt(_SHA2_Common):
    """This class implements the SHA256-Crypt password hash, and follows the :ref:`password-hash-api`.

    It supports a variable-length salt, and a variable number of rounds.

    The :meth:`~passlib.ifc.PasswordHash.encrypt` and :meth:`~passlib.ifc.PasswordHash.genconfig` methods accept the following optional keywords:

    :type salt: str
    :param salt:
        Optional salt string.
        If not specified, one will be autogenerated (this is recommended).
        If specified, it must be 0-16 characters, drawn from the regexp range ``[./0-9A-Za-z]``.

    :type rounds: int
    :param rounds:
        Optional number of rounds to use.
        Defaults to 535000, must be between 1000 and 999999999, inclusive.

    :type implicit_rounds: bool
    :param implicit_rounds:
        this is an internal option which generally doesn't need to be touched.

        this flag determines whether the hash should omit the rounds parameter
        when encoding it to a string; this is only permitted by the spec for rounds=5000,
        and the flag is ignored otherwise. the spec requires the two different
        encodings be preserved as they are, instead of normalizing them.

    :type relaxed: bool
    :param relaxed:
        By default, providing an invalid value for one of the other
        keywords will result in a :exc:`ValueError`. If ``relaxed=True``,
        and the error can be corrected, a :exc:`~passlib.exc.PasslibHashWarning`
        will be issued instead. Correctable errors include ``rounds``
        that are too small or too large, and ``salt`` strings that are too long.

        .. versionadded:: 1.6
    """
    #===================================================================
    # class attrs
    #===================================================================
    name = "sha256_crypt"
    ident = u("$5$")
    checksum_size = 43
    # NOTE: using 25/75 weighting of builtin & os_crypt backends
    default_rounds = 535000

    #===================================================================
    # backends
    #===================================================================
    @classproperty
    def _has_backend_os_crypt(cls):
        return test_crypt("test", "$5$rounds=1000$test$QmQADEXMG8POI5W"
                                         "Dsaeho0P36yK3Tcrgboabng6bkb/")

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# sha 512 crypt
#=============================================================================
class sha512_crypt(_SHA2_Common):
    """This class implements the SHA512-Crypt password hash, and follows the :ref:`password-hash-api`.

    It supports a variable-length salt, and a variable number of rounds.

    The :meth:`~passlib.ifc.PasswordHash.encrypt` and :meth:`~passlib.ifc.PasswordHash.genconfig` methods accept the following optional keywords:

    :type salt: str
    :param salt:
        Optional salt string.
        If not specified, one will be autogenerated (this is recommended).
        If specified, it must be 0-16 characters, drawn from the regexp range ``[./0-9A-Za-z]``.

    :type rounds: int
    :param rounds:
        Optional number of rounds to use.
        Defaults to 656000, must be between 1000 and 999999999, inclusive.

    :type implicit_rounds: bool
    :param implicit_rounds:
        this is an internal option which generally doesn't need to be touched.

        this flag determines whether the hash should omit the rounds parameter
        when encoding it to a string; this is only permitted by the spec for rounds=5000,
        and the flag is ignored otherwise. the spec requires the two different
        encodings be preserved as they are, instead of normalizing them.

    :type relaxed: bool
    :param relaxed:
        By default, providing an invalid value for one of the other
        keywords will result in a :exc:`ValueError`. If ``relaxed=True``,
        and the error can be corrected, a :exc:`~passlib.exc.PasslibHashWarning`
        will be issued instead. Correctable errors include ``rounds``
        that are too small or too large, and ``salt`` strings that are too long.

        .. versionadded:: 1.6
    """

    #===================================================================
    # class attrs
    #===================================================================
    name = "sha512_crypt"
    ident = u("$6$")
    checksum_size = 86
    _cdb_use_512 = True
    # NOTE: using 25/75 weighting of builtin & os_crypt backends
    default_rounds = 656000

    #===================================================================
    # backend
    #===================================================================
    @classproperty
    def _has_backend_os_crypt(cls):
        return test_crypt("test", "$6$rounds=1000$test$2M/Lx6Mtobqj"
                                          "Ljobw0Wmo4Q5OFx5nVLJvmgseatA6oMn"
                                          "yWeBdRDx4DU.1H3eGmse6pgsOgDisWBG"
                                          "I5c7TZauS0")

    #===================================================================
    # eoc
    #===================================================================

#=============================================================================
# eof
#=============================================================================
