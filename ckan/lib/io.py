# encoding: utf-8

u'''
Utility functions for I/O.
'''

import sys

import six

_FILESYSTEM_ENCODING = six.text_type(
    sys.getfilesystemencoding() or sys.getdefaultencoding()
)


def encode_path(p):
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
    if not isinstance(p, six.text_type):
        raise TypeError(u'Can only encode unicode, not {}'.format(type(p)))
    return six.ensure_text(p).encode(_FILESYSTEM_ENCODING)


def decode_path(p):
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

    if not isinstance(p, six.binary_type):
        raise TypeError(u'Can only decode str, not {}'.format(type(p)))
    return six.ensure_binary(p).decode(_FILESYSTEM_ENCODING)
