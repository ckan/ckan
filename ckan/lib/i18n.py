import os

import pylons
from pylons.i18n import set_lang
from babel import Locale, localedata
from babel.core import LOCALE_ALIASES
from pylons import config

import ckan.i18n

LOCALE_ALIASES['pt'] = 'pt_BR' # Default Portuguese language to
                               # Brazilian territory, since
                               # we don't have a Portuguese territory
                               # translation currently.

def _get_locales():

    assert not config.get('lang'), \
            '"lang" config option not supported - please use ckan.locale_default instead.'
    locales_offered = config.get('ckan.locales_offered', '').split()
    filtered_out = config.get('ckan.locales_filtered_out', '').split()
    locale_order = config.get('ckan.locale_order', '').split()
    locale_default = config.get('ckan.locale_default', 'en')

    locales = ['en']
    i18n_path = os.path.dirname(ckan.i18n.__file__)
    locales += [l for l in os.listdir(i18n_path) if localedata.exists(l)]

    assert locale_default in locales, \
            'default language "%s" not available' % locale_default

    locale_list = []
    for locale in locales:
        if locale in locale_list:
            continue
        if locales_offered and locale not in locales_offered:
            continue
        if locale in filtered_out:
            continue
        if locale == locale_default:
            continue
        locale_list.append(locale)
    ordered_list = [Locale.parse(locale_default)]
    for locale in locale_order:
        if locale in locale_list:
            ordered_list.append(Locale.parse(locale))

    return ordered_list

available_locales = None

def get_available_locales():
    if not available_locales:
        global available_locales
        available_locales = _get_locales()
    return available_locales

def handle_request(request, tmpl_context):
    lang = request.environ.get('CKAN_LANG', config['ckan.locale_default'])
    if lang != 'en':
        set_lang(lang)
    tmpl_context.language = lang
    return lang

def get_lang():
    '''Returns the current language. Based on babel.i18n.get_lang but works
    when set_lang has not been run (i.e. still in English).'''
    langs = pylons.i18n.get_lang()
    if langs:
        return langs[0]
    else:
        return 'en'
