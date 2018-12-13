"""Beaker exception classes"""


class BeakerException(Exception):
    pass


class BeakerWarning(RuntimeWarning):
    """Issued at runtime."""


class CreationAbortedError(Exception):
    """Deprecated."""


class InvalidCacheBackendError(BeakerException, ImportError):
    pass


class MissingCacheParameter(BeakerException):
    pass


class LockError(BeakerException):
    pass


class InvalidCryptoBackendError(BeakerException):
    pass
