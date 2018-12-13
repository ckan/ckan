from hashlib import md5

try:
    # Use PyCrypto (if available)
    from Crypto.Hash import HMAC as hmac, SHA as hmac_sha1
    sha1 = hmac_sha1.new

except ImportError:

    # PyCrypto not available.  Use the Python standard library.
    import hmac

    # NOTE: We have to use the callable with hashlib (hashlib.sha1),
    # otherwise hmac only accepts the sha module object itself
    from hashlib import sha1
    hmac_sha1 = sha1