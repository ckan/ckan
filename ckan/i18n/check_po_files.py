#!/usr/bin/env python
# encoding: utf-8

'''Script for checking for common translation mistakes in po files, see:

    paster check-po-files --help

for usage.
'''
from __future__ import print_function
import polib
import re

import six


def simple_conv_specs(s):
    '''Return the simple Python string conversion specifiers in the string s.

    e.g. ['%s', '%i']

    See http://docs.python.org/library/stdtypes.html#string-formatting

    '''
    simple_conv_specs_re = re.compile(r'\%\w')
    return simple_conv_specs_re.findall(s)


def mapping_keys(s):
    '''Return a sorted list of the mapping keys in the string s.

    e.g. ['%(name)s', '%(age)i']

    See http://docs.python.org/library/stdtypes.html#string-formatting

    '''
    mapping_keys_re = re.compile(r'\%\([^\)]*\)\w')
    return sorted(mapping_keys_re.findall(s))


def replacement_fields(s):
    '''Return a sorted list of the Python replacement fields in the string s.

    e.g. ['{}', '{2}', '{object}', '{target}']

    See http://docs.python.org/library/string.html#formatstrings

    '''
    repl_fields_re = re.compile(r'\{[^\}]*\}')
    return sorted(repl_fields_re.findall(s))


def check_po_files(paths):
    for path in paths:
        print(u'Checking file {}'.format(path))
        errors = check_po_file(path)
        if errors:
            for msgid, msgstr in errors:
                print("Format specifiers don't match:")
                print(u'    {0} -> {1}'.format(
                    msgid, msgstr.encode('ascii', 'replace')))


def check_po_file(path):
    errors = []

    def check_translation(validator, msgid, msgstr):
        if not validator(msgid) == validator(msgstr):
            errors.append((msgid, msgstr))

    po = polib.pofile(path)
    for entry in po.translated_entries():
        if entry.msgid_plural and entry.msgstr_plural:
            for function in (simple_conv_specs, mapping_keys,
                             replacement_fields):
                for key, msgstr in six.iteritems(entry.msgstr_plural):
                    if key == '0':
                        check_translation(function, entry.msgid,
                                          entry.msgstr_plural[key])
                    else:
                        check_translation(function, entry.msgid_plural,
                                          entry.msgstr_plural[key])
        elif entry.msgstr:
            for function in (simple_conv_specs, mapping_keys,
                             replacement_fields):
                check_translation(function, entry.msgid, entry.msgstr)

    return errors
