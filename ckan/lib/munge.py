# encoding: utf-8

# Note these functions are similar to, but separate from name/title mungers
# found in the ckanext importer. That one needs to be stable to prevent
# packages changing name on reimport, but these ones can be changed and
# improved.

import os.path
import re

import regex
from six import text_type, u

from ckan import model
from ckan.lib.io import decode_path

# Maximum length of a filename's extension (including the '.')
MAX_FILENAME_EXTENSION_LENGTH = 21

# Maximum total length of a filename (including extension)
MAX_FILENAME_TOTAL_LENGTH = 100

# Minimum total length of a filename (including extension)
MIN_FILENAME_TOTAL_LENGTH = 3


def munge_name(name):
    '''Munges the package name field in case it is not to spec.'''
    # separators become dashes
    name = re.sub('[ .:/]', '-', name)
    # take out not-allowed characters
    name = _unicode_cleanup(name, keep='-_').lower()
    # keep it within the length spec
    name = _munge_to_length(name, model.PACKAGE_NAME_MIN_LENGTH,
                            model.PACKAGE_NAME_MAX_LENGTH)
    return name


def munge_title_to_name(name):
    '''Munge a package title into a package name.'''
    # convert spaces and separators
    name = re.sub('[ .:/]', '-', name)
    # take out not-allowed characters
    name = _unicode_cleanup(name, keep='-_').lower()
    # remove doubles
    name = re.sub('-+', '-', name)
    # remove leading or trailing hyphens
    name = name.strip('-')
    # if longer than max_length, keep last word if a year
    max_length = model.PACKAGE_NAME_MAX_LENGTH - 5
    # (make length less than max, in case we need a few for '_' chars
    # to de-clash names.)
    if len(name) > max_length:
        year_match = re.match('.*?[_-]((?:\d{2,4}[-/])?\d{2,4})$', name)
        if year_match:
            year = year_match.groups()[0]
            name = '%s-%s' % (name[:(max_length-len(year)-1)], year)
        else:
            name = name[:max_length]
    name = _munge_to_length(name, model.PACKAGE_NAME_MIN_LENGTH,
                            model.PACKAGE_NAME_MAX_LENGTH)
    return name


def munge_tag(tag):
    tag = tag.lower().strip()
    tag = _unicode_cleanup(tag, keep='- ').replace(' ', '-')
    tag = _munge_to_length(tag, model.MIN_TAG_LENGTH, model.MAX_TAG_LENGTH)
    return tag


def munge_filename_legacy(filename):
    ''' Tidies a filename. NB: deprecated

    Unfortunately it mangles any path or filename extension, so is deprecated.
    It needs to remain unchanged for use by group_dictize() and
    Upload.update_data_dict() because if this routine changes then group images
    uploaded previous to the change may not be viewable.
    '''
    filename = filename.strip()
    filename = _unicode_cleanup(filename, keep='.- ').replace(' ', '-')
    filename = _munge_to_length(filename, 3, 100)
    return filename


def munge_filename(filename):
    ''' Tidies a filename

    Keeps the filename extension (e.g. .csv).
    Strips off any path on the front.

    Returns a Unicode string.
    '''
    if not isinstance(filename, text_type):
        filename = decode_path(filename)

    # Ignore path
    filename = os.path.split(filename)[1]

    # Clean up
    filename = filename.lower().strip()
    filename = _unicode_cleanup(filename, keep='_.- ').replace(u' ', u'-')
    filename = re.sub(u'-+', u'-', filename)

    # Enforce length constraints
    name, ext = os.path.splitext(filename)
    ext = ext[:MAX_FILENAME_EXTENSION_LENGTH]
    ext_len = len(ext)
    name = _munge_to_length(name, max(1, MIN_FILENAME_TOTAL_LENGTH - ext_len),
                            MAX_FILENAME_TOTAL_LENGTH - ext_len)
    filename = name + ext

    return filename


def _munge_to_length(string, min_length, max_length):
    '''Pad/truncates a string'''
    if len(string) < min_length:
        string += '_' * (min_length - len(string))
    if len(string) > max_length:
        string = string[:max_length]
    return string


def _unicode_cleanup(text, keep=''):
    '''Remove unwanted Unicode characters'''
    keep = ''.join(['\\'+c for c in keep])
    return regex.sub(u(r'[^\p{NUMBER}\p{LETTER}%s]' % keep), '', text)
