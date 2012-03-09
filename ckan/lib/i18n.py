import os

from babel import Locale, localedata
from babel.core import LOCALE_ALIASES
from pylons import config
from pylons import i18n

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

def get_locales():
    ''' Get list of available locales
    e.g. [ 'en', 'de', ... ]
    '''
    global locales
    if not locales:
        locales = _get_locales()
    return locales

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
        available_locales = map(Locale.parse, get_locales())
    return available_locales

def handle_request(request, tmpl_context):
    ''' Set the language for the request '''
    lang = request.environ.get('CKAN_LANG') or \
                        config.get('ckan.locale_default', 'en')
    if lang != 'en':
        i18n.set_lang(lang)
    tmpl_context.language = lang
    return lang

def get_lang():
    ''' Returns the current language. Based on babel.i18n.get_lang but
    works when set_lang has not been run (i.e. still in English). '''
    langs = i18n.get_lang()
    if langs:
        return langs[0]
    else:
        return 'en'
