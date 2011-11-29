import os

import pylons
from pylons.i18n import _, add_fallback, set_lang, gettext, LanguageError
from pylons.i18n.translation import _get_translator
from babel import Locale, localedata
from babel.core import LOCALE_ALIASES

import ckan.i18n

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

i18n_path = os.path.dirname(ckan.i18n.__file__)

@singleton
class Locales(object):
    def __init__(self):
        from pylons import config

        # Get names of the locales
        # (must be a better way than scanning for i18n directory?)
        known_locales = ['en'] + [locale_name for locale_name in os.listdir(i18n_path) \
                                  if localedata.exists(locale_name)]
        self._locale_names, self._default_locale_name = self._work_out_locales(
            known_locales, config)
        self._locale_objects = map(Locale.parse, self._locale_names)
        self._default_locale_object = Locale.parse(self._default_locale_name)

        self._aliases = LOCALE_ALIASES
        self._aliases['pt'] = 'pt_BR' # Default Portuguese language to
                                     # Brazilian territory, since
                                     # we don't have a Portuguese territory
                                     # translation currently.

    def _work_out_locales(self, known_locales, config_dict):
        '''Work out the locale_names to offer to the user and the default locale.
        All locales in this method are strings, not Locale objects.'''
        # pass in a config_dict rather than ckan.config to make this testable

        # Get default locale
        assert not config_dict.get('lang'), \
               '"lang" config option not supported - please use ckan.locale_default instead.'
        default_locale = config_dict.get('ckan.locale_default') or \
                         config_dict.get('ckan.locale') or \
                         None # in this case, set it later on
        if default_locale:
            assert default_locale in known_locales

        # Filter and reorder locales by config options
        def get_locales_in_config_option(config_option):
            locales_ = config_dict.get(config_option, '').split()
            if locales_:
                unknown_locales = set(locales_) - set(known_locales)
                assert not unknown_locales, \
                       'Bad config option %r - locales not found: %s' % \
                       (config_option, unknown_locales)
            return locales_
        only_locales_offered = get_locales_in_config_option('ckan.locales_offered')
        if only_locales_offered:
            locales = only_locales_offered
        else:
            locales = known_locales
            
        def move_locale_to_start_of_list(locale_):
            if locale_ not in locales:
                raise ValueError('Cannot find locale "%s" in locales offered.' % locale_)
            locales.pop(locales.index(locale_))
            locales.insert(0, locale_)
            
        locales_filtered_out = get_locales_in_config_option('ckan.locales_filtered_out')
        for locale in locales_filtered_out:
            try:
                locales.pop(locales.index(locale))
            except ValueError, e:
                raise ValueError('Could not filter out locale "%s" from offered locale list "%s": %s') % \
                      (locale, locales, e)

        locale_order = get_locales_in_config_option('ckan.locale_order')
        if locale_order:
            for locale in locale_order[::-1]:
                # bring locale_name to the front
                try:
                    move_locale_to_start_of_list(locale)
                except ValueError, e:
                    raise ValueError('Could not process ckan.locale_order options "%s" for offered locale list "%s": %s' % \
                                     (locale_order, locales, e))
        elif default_locale:
            if default_locale not in locales:
                raise ValueError('Default locale "%s" is not amongst locales offered: %s' % \
                                 (default_locale, locales))
            # move the default locale to the start of the list
            try:
                move_locale_to_start_of_list(default_locale)
            except ValueError, e:
                raise ValueError('Could not move default locale "%s" to the start ofthe list of offered locales "%s": %s' % \
                                 (default_locale, locales, e))

        assert locales
            
        if not default_locale:
            default_locale = locales[0]
        assert default_locale in locales

        return locales, default_locale

    def get_available_locales(self):
        '''Returns a list of the locale objects for which translations are
        available.'''
        return self._locale_objects

    def get_available_locale_names(self):
        '''Returns a list of the locale strings for which translations are
        available.'''
        return self._locale_names

    def get_default_locale(self):
        '''Returns the default locale/language as specified in the CKAN
        config. It is a locale object.'''
        return self._default_locale_object

    def get_aliases(self):
        '''Returns a mapping of language aliases, like the Babel LOCALE_ALIASES
        but with hacks for specific CKAN issues.'''
        return self._aliases

    def negotiate_known_locale(self, preferred_locales):
        '''Given a list of preferred locales, this method returns the best
        match locale object from the known ones.'''
        assert isinstance(preferred_locales, (tuple, list))
        preferred_locales = [str(l).replace('-', '_') for l in preferred_locales]
        return Locale.parse(Locale.negotiate(preferred_locales,
                                             self.get_available_locale_names(),
                                             aliases=self.get_aliases()
                                             ))

def get_available_locales():
    return Locales().get_available_locales()

def set_session_locale(locale):
    if locale not in get_available_locales():
        raise ValueError
    from pylons import session
    session['locale'] = locale
    session.save()

def handle_request(request, tmpl_context):
    from pylons import session

    # Work out what language to show the page in.
    locales = [] # Locale objects. Ordered highest preference first.
    tmpl_context.language = None
    if session.get('locale'):
        # First look for locale saved in the session (by home controller)
        locales.append(Locale.parse(session.get('locale')))

    # Browser language detection disabled temporarily - see #1452
##    else:
##        # Next try to detect languages in the HTTP_ACCEPT_LANGUAGE header
##        locale = Locales().negotiate_known_locale(request.languages)
##        if locale:
##            locales.append(locale)

    # Next try the default locale in the CKAN config file
    locales.append(Locales().get_default_locale())

    locale = set_lang_list(locales)
    tmpl_context.language = locale.language
    return locale

def set_lang_list(locales):
    '''Takes a list of locales (ordered by reducing preference) and tries
    to set them in order. If one fails then it puts up a flash message and
    tries the next.'''
    import ckan.lib.helpers as h
    failed_locales = set()
    for locale in locales:
        # try locales in order of preference until one works
        try:
            if str(locale) == 'en':
                # There is no language file for English, so if we set_lang
                # we would get an error. Just don't set_lang and finish.
                break
            set_lang(str(locale))
            break
        except LanguageError, e:
            if str(locale) not in failed_locales:
                h.flash_error(_('Could not change language to %r: %s') % \
                              (str(locale), e))
                failed_locales.add(str(locale))
    return locale

def get_lang():
    '''Returns the current language. Based on babel.i18n.get_lang but works
    when set_lang has not been run (i.e. still in English).'''
    langs = pylons.i18n.get_lang()
    if langs:
        return langs[0]
    else:
        return 'en'
