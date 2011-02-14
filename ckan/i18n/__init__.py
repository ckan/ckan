from pylons.i18n import _, add_fallback, get_lang, set_lang, gettext
from babel import Locale


# TODO: Figure out a nicer way to get this. From the .ini? 
_KNOWN_LOCALES = ['en', 'ca', 'de', 'el',
                  'es', 'fi', 'fr', 'hu',
                  'it', 'lt', 'nl', 'no',
                  'pl', 'pt_BR', 'ro', 'ru',
                  'sl', 'sq']

def get_available_locales():
    return map(Locale.parse, _KNOWN_LOCALES)

def get_default_locale():
    from pylons import config
    return Locale.parse(config.get('ckan.locale')) or \
            Locale.parse('en')

def set_session_locale(locale):
    assert locale in _KNOWN_LOCALES
    from pylons import session
    session['locale'] = locale
    session.save()

def handle_request(request, tmpl_context):
    from pylons import session

    tmpl_context.language = locale = None
    if 'locale' in session:
        locale = Locale.parse(session.get('locale'))
    else:
        requested = [l.replace('-', '_') for l in request.languages]
        locale = Locale.parse(Locale.negotiate(_KNOWN_LOCALES, requested))

    if locale is None:
        locale = get_default_locale()
    
    options = [str(locale), locale.language, str(get_default_locale()),
        get_default_locale().language]
    for language in options:
        try:
            set_lang(language) 
            tmpl_context.language = language
        except: pass


