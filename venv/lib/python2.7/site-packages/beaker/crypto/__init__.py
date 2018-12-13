from .._compat import JYTHON


from beaker.crypto.pbkdf2 import pbkdf2
from beaker.crypto.util import hmac, sha1, hmac_sha1, md5
from beaker import util
from beaker.exceptions import InvalidCryptoBackendError

keyLength = None
DEFAULT_NONCE_BITS = 128

CRYPTO_MODULES = {}


def load_default_module():
    """ Load the default crypto module
    """
    if JYTHON:
        try:
            from beaker.crypto import jcecrypto
            return jcecrypto
        except ImportError:
            pass
    else:
        try:
            from beaker.crypto import nsscrypto
            return nsscrypto
        except ImportError:
            try:
                from beaker.crypto import pycrypto
                return pycrypto
            except ImportError:
                pass
    from beaker.crypto import noencryption
    return noencryption


def register_crypto_module(name, mod):
    """
    Register the given module under the name given.
    """
    CRYPTO_MODULES[name] = mod


def get_crypto_module(name):
    """
    Get the active crypto module for this name
    """
    if name not in CRYPTO_MODULES:
        if name == 'default':
            register_crypto_module('default', load_default_module())
        elif name == 'nss':
            from beaker.crypto import nsscrypto
            register_crypto_module(name, nsscrypto)
        elif name == 'pycrypto':
            from beaker.crypto import pycrypto
            register_crypto_module(name, pycrypto)
        elif name == 'cryptography':
            from beaker.crypto import pyca_cryptography
            register_crypto_module(name, pyca_cryptography)
        else:
            raise InvalidCryptoBackendError(
                "No crypto backend with name '%s' is registered." % name)

    return CRYPTO_MODULES[name]



def generateCryptoKeys(master_key, salt, iterations, keylen):
    # NB: We XOR parts of the keystream into the randomly-generated parts, just
    # in case os.urandom() isn't as random as it should be.  Note that if
    # os.urandom() returns truly random data, this will have no effect on the
    # overall security.
    return pbkdf2(master_key, salt, iterations=iterations, dklen=keylen)


def get_nonce_size(number_of_bits):
    if number_of_bits % 8:
        raise ValueError('Nonce complexity currently supports multiples of 8')

    bytes = number_of_bits // 8
    b64bytes = ((4 * bytes // 3) + 3) & ~3
    return bytes, b64bytes
