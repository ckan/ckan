# encoding: utf-8

'''
Internationalization utilities.

This module contains code from the pojson project, which is subject to
the following license (see https://bitbucket.org/obviel/pojson):

Copyright (c) 2010, Fanstatic Developers
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in
      the documentation and/or other materials provided with the
      distribution.
    * Neither the name of the organization nor the names of its
      contributors may be used to endorse or promote products derived
      from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL FANSTATIC
DEVELOPERS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''

import collections
import json
import logging
import os
import os.path

from babel import Locale
from babel.core import (LOCALE_ALIASES,
                        get_locale_identifier,
                        UnknownLocaleError)
from babel.support import Translations
from paste.deploy.converters import aslist
from pylons import i18n
import pylons
import polib

from ckan.common import config
import ckan.i18n
from ckan.plugins import PluginImplementations
from ckan.plugins.interfaces import ITranslation


log = logging.getLogger(__name__)

# Default Portuguese language to Brazilian territory, since
# we don't have a Portuguese territory translation currently.
LOCALE_ALIASES['pt'] = 'pt_BR'

# CKAN root directory
_CKAN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), u'..'))

# Output directory for generated JavaScript translations
_JS_TRANSLATIONS_DIR = os.path.join(_CKAN_DIR, u'public', u'base', u'i18n')


def get_locales_from_config():
    ''' despite the name of this function it gets the locales defined by
    the config AND also the locals available subject to the config. '''
    locales_offered = config.get('ckan.locales_offered', '').split()
    filtered_out = config.get('ckan.locales_filtered_out', '').split()
    locale_default = [config.get('ckan.locale_default', 'en')]
    locale_order = config.get('ckan.locale_order', '').split()

    known_locales = get_locales()
    all_locales = (set(known_locales) |
                   set(locales_offered) |
                   set(locale_order) |
                   set(locale_default))
    all_locales -= set(filtered_out)
    return all_locales


def _get_locales():
    # FIXME this wants cleaning up and merging with get_locales_from_config()
    assert not config.get('lang'), \
        ('"lang" config option not supported - please use ckan.locale_default '
         'instead.')
    locales_offered = config.get('ckan.locales_offered', '').split()
    filtered_out = config.get('ckan.locales_filtered_out', '').split()
    locale_default = config.get('ckan.locale_default', 'en')
    locale_order = config.get('ckan.locale_order', '').split()

    locales = ['en']
    if config.get('ckan.i18n_directory'):
        i18n_path = os.path.join(config.get('ckan.i18n_directory'), 'i18n')
    else:
        i18n_path = os.path.dirname(ckan.i18n.__file__)

    # For every file in the ckan i18n directory see if babel can understand
    # the locale. If yes, add it to the available locales
    for locale in os.listdir(i18n_path):
        try:
            Locale.parse(locale)
            locales.append(locale)
        except (ValueError, UnknownLocaleError):
            # Babel does not know how to make a locale out of this.
            # This is fine since we are passing all files in the
            # ckan.i18n_directory here which e.g. includes the __init__.py
            pass

    assert locale_default in locales, \
        'default language "%s" not available' % locale_default

    locale_list = []
    for locale in locales:
        # no duplicates
        if locale in locale_list:
            continue
        # if offered locales then check locale is offered
        if locales_offered and locale not in locales_offered:
            continue
        # remove if filtered out
        if locale in filtered_out:
            continue
        # ignore the default as it will be added first
        if locale == locale_default:
            continue
        locale_list.append(locale)
    # order the list if specified
    ordered_list = [locale_default]
    for locale in locale_order:
        if locale in locale_list:
            ordered_list.append(locale)
            # added so remove from our list
            locale_list.remove(locale)
    # add any remaining locales not ordered
    ordered_list += locale_list

    return ordered_list


available_locales = None
locales = None
locales_dict = None
_non_translated_locals = None


def get_locales():
    ''' Get list of available locales
    e.g. [ 'en', 'de', ... ]
    '''
    global locales
    if not locales:
        locales = _get_locales()
    return locales


def non_translated_locals():
    ''' These are the locales that are available but for which there are
    no translations. returns a list like ['en', 'de', ...] '''
    global _non_translated_locals
    if not _non_translated_locals:
        locales = config.get('ckan.locale_order', '').split()
        _non_translated_locals = [x for x in locales if x not in get_locales()]
    return _non_translated_locals


def get_locales_dict():
    ''' Get a dict of the available locales
    e.g.  { 'en' : Locale('en'), 'de' : Locale('de'), ... } '''
    global locales_dict
    if not locales_dict:
        locales = _get_locales()
        locales_dict = {}
        for locale in locales:
            locales_dict[str(locale)] = Locale.parse(locale)
    return locales_dict


def get_available_locales():
    ''' Get a list of the available locales
    e.g.  [ Locale('en'), Locale('de'), ... ] '''
    global available_locales
    if not available_locales:
        available_locales = []
        for locale in get_locales():
            # Add the short names for the locales. This equals the filename
            # of the ckan translation files as opposed to the long name
            # that includes the script which is generated by babel
            # so e.g. `zn_CH` instead of `zn_Hans_CH` this is needed
            # to properly construct urls with url_for
            parsed_locale = Locale.parse(locale)
            parsed_locale.short_name = locale

            # Add the full identifier (eg `pt_BR`) to the locale classes,
            # as it does not offer a way of accessing it directly
            parsed_locale.identifier = \
                get_identifier_from_locale_class(parsed_locale)
            available_locales.append(parsed_locale)
    return available_locales


def get_identifier_from_locale_class(locale):
    return get_locale_identifier(
        (locale.language,
         locale.territory,
         locale.script,
         locale.variant))


def _set_lang(lang):
    ''' Allows a custom i18n directory to be specified.
    Creates a fake config file to pass to pylons.i18n.set_lang, which
    sets the Pylons root path to desired i18n_directory.
    This is needed as Pylons will only look for an i18n directory in
    the application root.'''
    if config.get('ckan.i18n_directory'):
        fake_config = {'pylons.paths': {'root': config['ckan.i18n_directory']},
                       'pylons.package': config['pylons.package']}
        i18n.set_lang(lang, pylons_config=fake_config, class_=Translations)
    else:
        i18n.set_lang(lang, class_=Translations)


def handle_request(request, tmpl_context):
    ''' Set the language for the request '''
    lang = request.environ.get('CKAN_LANG') or \
        config.get('ckan.locale_default', 'en')
    if lang != 'en':
        set_lang(lang)

    for plugin in PluginImplementations(ITranslation):
        if lang in plugin.i18n_locales():
            _add_extra_translations(plugin.i18n_directory(), lang,
                                    plugin.i18n_domain())

    extra_directory = config.get('ckan.i18n.extra_directory')
    extra_domain = config.get('ckan.i18n.extra_gettext_domain')
    extra_locales = aslist(config.get('ckan.i18n.extra_locales'))
    if extra_directory and extra_domain and extra_locales:
        if lang in extra_locales:
            _add_extra_translations(extra_directory, lang, extra_domain)

    tmpl_context.language = lang
    return lang


def _add_extra_translations(dirname, locales, domain):
    translator = Translations.load(dirname=dirname, locales=locales,
                                   domain=domain)
    try:
        pylons.translator.merge(translator)
    except AttributeError:
        # this occurs when an extension has 'en' translations that
        # replace the default strings. As set_lang has not been run,
        # pylons.translation is the NullTranslation, so we have to
        # replace the StackedObjectProxy ourselves manually.
        environ = pylons.request.environ
        environ['pylons.pylons'].translator = translator
        if 'paste.registry' in environ:
            environ['paste.registry'].replace(pylons.translator,
                                              translator)


def get_lang():
    ''' Returns the current language. Based on babel.i18n.get_lang but
    works when set_lang has not been run (i.e. still in English). '''
    langs = i18n.get_lang()
    if langs:
        return langs[0]
    else:
        return 'en'


def set_lang(language_code):
    ''' Wrapper to pylons call '''
    if language_code in non_translated_locals():
        language_code = config.get('ckan.locale_default', 'en')
    if language_code != 'en':
        _set_lang(language_code)


def _get_js_translation_entries(filename):
    '''
    Extract IDs of PO entries that are used in JavaScript files.

    :param filename: PO filename
    :type filename: string
    :return: The IDs of those entries which occur in a ``*.js`` file
    :rtype: set
    '''
    js_entries = set()
    for entry in polib.pofile(filename):
        if entry.obsolete:
            continue
        for occ in entry.occurrences:
            if occ[0].endswith(u'.js'):
                js_entries.add(entry.msgid)
    return js_entries


def _build_js_translation(lang, source_filenames, entries, dest_filename):
    '''
    Build JavaScript translations for a single language.

    Collects translations for a language from several PO files and
    stores the entries in a JSON file.

    :param lang: Language code
    :type lang: string
    :param source_filenames: Filenames of PO files
    :type source_filenames: List of strings
    :param entries: List of entry IDs. Only entries whose IDs are in
                    this list are exported.
    :type entries: List of strings
    :param dest_filename: Output filename
    '''
    pos = [polib.pofile(fn) for fn in source_filenames]

    result = {}
    result[u''] = {}
    result[u''][u'plural-forms'] = pos[0].metadata[u'Plural-Forms']
    result[u''][u'lang'] = lang
    result[u''][u'domain'] = u'ckan'

    for po in pos:
        for entry in po:
            if entry.msgid not in entries:
                continue
            if entry.msgstr:
                result[entry.msgid] = [None, entry.msgstr]
            elif entry.msgstr_plural:
                plural = result[entry.msgid] = [entry.msgid_plural]
                ordered_plural = sorted(entry.msgstr_plural.items())
                for order, msgstr in ordered_plural:
                    plural.append(msgstr)
    with open(dest_filename, u'w') as f:
        s = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False)
        f.write(s.encode(u'utf-8'))


def build_js_translations():
    '''
    Build JavaScript translation files.

    Takes the PO files from CKAN and from plugins that implement
    ``ITranslation`` and creates corresponding JS translation files in
    ``ckan.i18n_directory``. These include only those translation
    strings that are actually used in JS files.
    '''
    log.debug(u'Generating JavaScript translations')
    ckan_i18n_dir = config.get(u'ckan.i18n_directory',
                               os.path.join(_CKAN_DIR, u'i18n'))

    # Collect all language codes (an extension might add support for a
    # language that isn't supported by CKAN core, yet).
    langs = set()
    i18n_dirs = collections.OrderedDict([(ckan_i18n_dir, u'ckan')])
    for item in os.listdir(ckan_i18n_dir):
        if os.path.isdir(os.path.join(ckan_i18n_dir, item)):
            langs.add(item)
    for plugin in PluginImplementations(ITranslation):
        langs.update(plugin.i18n_locales())
        i18n_dirs[plugin.i18n_directory()] = plugin.i18n_domain()

    # Find out which translation entries are used in JS files. We use
    # the POT files for that, since they contain all translation entries
    # (even those for which no translation exists, yet).
    js_entries = set()
    for i18n_dir, domain in i18n_dirs.iteritems():
        pot_file = os.path.join(i18n_dir, domain + u'.pot')
        if os.path.isfile(pot_file):
            js_entries.update(_get_js_translation_entries(pot_file))

    # Build translations for each language
    for lang in sorted(langs):
        po_files = [
            fn for fn in (
                os.path.join(
                    i18n_dir,
                    lang,
                    u'LC_MESSAGES',
                    domain + u'.po'
                )
                for i18n_dir, domain in i18n_dirs.iteritems()
            ) if os.path.isfile(fn)
        ]
        if not po_files:
            continue

        latest = max(os.path.getmtime(fn) for fn in po_files)
        dest_file = os.path.join(_JS_TRANSLATIONS_DIR, lang + u'.js')
        if os.path.isfile(dest_file) and os.path.getmtime(dest_file) > latest:
            log.debug(u'JS translation for "{}" is up to date'.format(lang))
        else:
            log.debug(u'Generating JS translation for "{}"'.format(lang))
            _build_js_translation(lang, po_files, js_entries, dest_file)
