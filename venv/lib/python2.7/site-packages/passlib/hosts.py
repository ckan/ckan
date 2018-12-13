"""passlib.hosts"""
#=============================================================================
# imports
#=============================================================================
# core
import sys
from warnings import warn
# pkg
from passlib.context import LazyCryptContext
from passlib.exc import PasslibRuntimeWarning
from passlib.registry import get_crypt_handler
from passlib.utils import has_crypt, unix_crypt_schemes
# local
__all__ = [
    "linux_context", "linux2_context",
    "openbsd_context",
    "netbsd_context",
    "freebsd_context",
    "host_context",
]

#=============================================================================
# linux support
#=============================================================================

# known platform names - linux2

linux_context = linux2_context = LazyCryptContext(
    schemes = [ "sha512_crypt", "sha256_crypt", "md5_crypt",
               "des_crypt", "unix_disabled" ],
    deprecated = [ "des_crypt" ],
    )

#=============================================================================
# bsd support
#=============================================================================

# known platform names -
#   freebsd2
#   freebsd3
#   freebsd4
#   freebsd5
#   freebsd6
#   freebsd7
#
#   netbsd1

# referencing source via -http://fxr.googlebit.com
# freebsd 6,7,8 - des, md5, bcrypt, bsd_nthash
# netbsd - des, ext, md5, bcrypt, sha1
# openbsd - des, ext, md5, bcrypt

freebsd_context = LazyCryptContext(["bcrypt", "md5_crypt", "bsd_nthash",
                                    "des_crypt", "unix_disabled"])

openbsd_context = LazyCryptContext(["bcrypt", "md5_crypt", "bsdi_crypt",
                                    "des_crypt", "unix_disabled"])

netbsd_context = LazyCryptContext(["bcrypt", "sha1_crypt", "md5_crypt",
                                   "bsdi_crypt", "des_crypt", "unix_disabled"])

# XXX: include darwin in this list? it's got a BSD crypt variant,
# but that's not what it uses for user passwords.

#=============================================================================
# current host
#=============================================================================
if has_crypt:
    # NOTE: this is basically mimicing the output of os crypt(),
    # except that it uses passlib's (usually stronger) defaults settings,
    # and can be introspected and used much more flexibly.

    def _iter_os_crypt_schemes():
        """helper which iterates over supported os_crypt schemes"""
        found = False
        for name in unix_crypt_schemes:
            handler = get_crypt_handler(name)
            if handler.has_backend("os_crypt"):
                found = True
                yield name
        if found:
            # only offer disabled handler if there's another scheme in front,
            # as this can't actually hash any passwords
            yield "unix_disabled"
        else: # pragma: no cover -- sanity check
            # no idea what OS this could happen on...
            warn("crypt.crypt() function is present, but doesn't support any "
                 "formats known to passlib!", PasslibRuntimeWarning)

    host_context = LazyCryptContext(_iter_os_crypt_schemes())

#=============================================================================
# other platforms
#=============================================================================

# known platform strings -
# aix3
# aix4
# atheos
# beos5
# darwin
# generic
# hp-ux11
# irix5
# irix6
# mac
# next3
# os2emx
# riscos
# sunos5
# unixware7

#=============================================================================
# eof
#=============================================================================
