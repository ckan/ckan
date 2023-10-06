# encoding: utf-8

"""
Utility functions for I/O.
"""

import hashlib
import os
import sys
import tempfile
from typing import Any, Union

from ckan.common import config
from ckan.exceptions import CkanConfigurationException


_FILESYSTEM_ENCODING = str(
    sys.getfilesystemencoding() or sys.getdefaultencoding()
)


def encode_path(p: Union[str, Any]) -> bytes:
    u'''
    Convert a Unicode path string to a byte string.

    Intended to be used for encoding paths that are known to be
    compatible with the filesystem, for example paths of existing files
    that were previously decoded using :py:func:`decode_path`. If you're
    dynamically constructing names for new files using unknown inputs
    then pass them through :py:func:`ckan.lib.munge.munge_filename`
    before encoding them.

    Raises a ``UnicodeEncodeError`` if the path cannot be encoded using
    the filesystem's encoding. That will never happen for paths returned
    by :py:func:`decode_path`.

    Raises a ``TypeError`` is the input is not a Unicode string.
    '''
    if not isinstance(p, str):
        raise TypeError(u'Can only encode unicode, not {}'.format(type(p)))
    return p.encode(_FILESYSTEM_ENCODING)


def decode_path(p: Union[bytes, Any]) -> str:
    u'''
    Convert a byte path string to a Unicode string.

    Intended to be used for decoding byte paths to existing files as
    returned by some of Python's built-in I/O functions.

    Raises a ``UnicodeDecodeError`` if the path cannot be decoded using
    the filesystem's encoding. Assuming the path was returned by one of
    Python's I/O functions this means that the environment Python is
    running in is set up incorrectly.

    Raises a ``TypeError`` if the input is not a byte string.
    '''

    if not isinstance(p, bytes):
        raise TypeError(u'Can only decode bytes, not {}'.format(type(p)))
    return p.decode(_FILESYSTEM_ENCODING)


def get_ckan_temp_directory() -> str:
    """
    Returns the path to a securely created temporary directory that can be used
    to store internal generated files like webassets, i18n files, etc

    It is used as fallback when `ckan.storage_path` is not defined.
    """

    if not config.get("SECRET_KEY"):
        # This function can be called before the configuration is validated,
        # so we need to do this check here
        raise CkanConfigurationException(
            "Invalid configuration values provided:\n"
            "SECRET_KEY: Missing value")
    unique_suffix = hashlib.sha256(
        config["SECRET_KEY"].encode()).hexdigest()[:10]
    directory_name = f"ckan_{unique_suffix}"

    path = os.path.join(tempfile.gettempdir(), directory_name)

    if not os.path.exists(path):
        os.mkdir(path, mode=0o700)

    return path
