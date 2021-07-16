# encoding: utf-8

import polib
import re
import logging
import os

import click
import six

from ckan.common import config
from ckan.lib.i18n import build_js_translations

ckan_path = os.path.join(os.path.dirname(__file__), '..')

log = logging.getLogger(__name__)


@click.group(name='translation', short_help='Translation management')
def translation():
    pass


@translation.command(
    'js', short_help='Generate the javascript translations.'
)
def js():
    build_js_translations()
    click.secho('JS translation build: SUCCESS', fg='green', bold=True)


@translation.command(
    'mangle', short_help='Mangle the zh_TW translations for testing.'
)
def mangle():
    '''This will mangle the zh_TW translations for translation coverage
    testing.

    NOTE: This will destroy the current translations fot zh_TW
    '''
    i18n_path = get_i18n_path()
    pot_path = os.path.join(i18n_path, 'ckan.pot')
    po = polib.pofile(pot_path)
    # we don't want to mangle the following items in strings
    # %(...)s  %s %0.3f %1$s %2$0.3f [1:...] {...} etc

    # sprintf bit after %
    spf_reg_ex = "\\+?(0|'.)?-?\\d*(.\\d*)?[\\%bcdeufosxX]"

    extract_reg_ex = '(\\%\\([^\\)]*\\)' + spf_reg_ex + \
                     '|\\[\\d*\\:[^\\]]*\\]' + \
                     '|\\{[^\\}]*\\}' + \
                     '|<[^>}]*>' + \
                     '|\\%((\\d)*\\$)?' + spf_reg_ex + ')'

    for entry in po:
        msg = entry.msgid.encode('utf-8')
        matches = re.finditer(extract_reg_ex, msg)
        length = len(msg)
        position = 0
        translation = ''
        for match in matches:
            translation += '-' * (match.start() - position)
            position = match.end()
            translation += match.group(0)
        translation += '-' * (length - position)
        entry.msgstr = translation
    out_dir = os.path.join(i18n_path, 'zh_TW', 'LC_MESSAGES')
    try:
        os.makedirs(out_dir)
    except OSError:
        pass
    po.metadata['Plural-Forms'] = "nplurals=1; plural=0\n"
    out_po = os.path.join(out_dir, 'ckan.po')
    out_mo = os.path.join(out_dir, 'ckan.mo')
    po.save(out_po)
    po.save_as_mofile(out_mo)
    click.secho('zh_TW has been mangled', fg='green', bold=True)


@translation.command(
    'check-po', short_help='Check po files for common mistakes'
)
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def check_po(files):
    for file in files:
        errors = check_po_file(file)
        for msgid, msgstr in errors:
            click.echo("Format specifiers don't match:")
            click.echo(
                '\t{} -> {}'.format(
                    msgid, msgstr.encode('ascii', 'replace')
                )
            )


@translation.command(
    'sync-msgids', short_help='Update the msgids on the po files '
    'with the ones on the pot file'
)
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def sync_po_msgids(files):
    i18n_path = get_i18n_path()
    pot_path = os.path.join(i18n_path, 'ckan.pot')
    po = polib.pofile(pot_path)
    entries_to_change = {}
    for entry in po.untranslated_entries():
        entries_to_change[normalize_string(entry.msgid)] = entry.msgid

    for path in files:
        sync_po_file_msgids(entries_to_change, path)


def normalize_string(s):
    return re.sub(r'\s\s+', ' ', s).strip()


def sync_po_file_msgids(entries_to_change, path):

    po = polib.pofile(path)
    cnt = 0

    for entry in po.translated_entries() + po.untranslated_entries():
        normalized = normalize_string(entry.msgid)

        if (normalized in entries_to_change
                and entry.msgid != entries_to_change[normalized]):
            entry.msgid = entries_to_change[normalized]
            cnt += 1

    po.save()
    click.echo(
        'Entries updated in {} file: {}'.format(po.metadata['Language'], cnt)
    )


def get_i18n_path():
    return config.get('ckan.i18n_directory', os.path.join(ckan_path, 'i18n'))


def simple_conv_specs(s):
    '''Return the simple Python string conversion specifiers in the string s.

    e.g. ['%s', '%i']

    See http://docs.python.org/library/stdtypes.html#string-formatting
    '''
    simple_conv_specs_re = re.compile('\\%\\w')
    return simple_conv_specs_re.findall(s)


def mapping_keys(s):
    '''Return a sorted list of the mapping keys in the string s.

    e.g. ['%(name)s', '%(age)i']

    See http://docs.python.org/library/stdtypes.html#string-formatting
    '''
    mapping_keys_re = re.compile('\\%\\([^\\)]*\\)\\w')
    return sorted(mapping_keys_re.findall(s))


def replacement_fields(s):
    '''Return a sorted list of the Python replacement fields in the string s.

    e.g. ['{}', '{2}', '{object}', '{target}']

    See http://docs.python.org/library/string.html#formatstrings
    '''
    repl_fields_re = re.compile('\\{[^\\}]*\\}')
    return sorted(repl_fields_re.findall(s))


def check_translation(validator, msgid, msgstr):
    if not validator(msgid) == validator(msgstr):
        return msgid, msgstr


def check_po_file(path):
    errors = []
    po = polib.pofile(path)
    for entry in po.translated_entries():
        if entry.msgid_plural and entry.msgstr_plural:
            for function in (
                simple_conv_specs, mapping_keys, replacement_fields
            ):
                for key, msgstr in six.iteritems(entry.msgstr_plural):
                    if key == '0':
                        error = check_translation(
                            function, entry.msgid, entry.msgstr_plural[key]
                        )
                    else:
                        error = check_translation(
                            function, entry.msgid_plural,
                            entry.msgstr_plural[key]
                        )
                    if error:
                        errors.append(error)

        elif entry.msgstr:
            for function in (
                simple_conv_specs, mapping_keys, replacement_fields
            ):
                error = check_translation(function, entry.msgid, entry.msgstr)
                if error:
                    errors.append(error)
    return errors
