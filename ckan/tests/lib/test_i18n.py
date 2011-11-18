from nose.tools import assert_equal, assert_raises
from babel import Locale
from pylons import config, session
import pylons
from pylons.i18n import get_lang

from ckan.lib.i18n import Locales, set_session_locale, set_lang
import ckan.lib.i18n

from ckan.tests.pylons_controller import PylonsTestCase, TestSession

class TestLocales:
    def test_work_out_locales__thedatahub(self):
        # as it is (roughly) on thedatahub.org
        locales, default = Locales()._work_out_locales(
            ['en', 'fr', 'de'],
            {'ckan.locale': 'en'})
        assert_equal(locales, ['en', 'fr', 'de'])
        assert_equal(default, 'en')

    def test_work_out_locales__france(self):
        # as it is (roughly) on a foreign language site
        locales, default = Locales()._work_out_locales(
            ['en', 'fr', 'de'],
            {'ckan.locale': 'fr'})
        # fr moved to start of the list
        assert_equal(locales, ['fr', 'en', 'de'])
        assert_equal(default, 'fr')

    def test_work_out_locales__locales_offered(self):
        locales, default = Locales()._work_out_locales(
            ['en', 'fr', 'de'],
            {'ckan.locales_offered': 'fr de'})
        assert_equal(locales, ['fr', 'de'])
        assert_equal(default, 'fr')

    def test_work_out_locales__locales_order(self):
        locales, default = Locales()._work_out_locales(
            ['en', 'fr', 'de'],
            {'ckan.locale': 'fr',
             'ckan.locale_order': 'de fr en'})
        assert_equal(locales, ['de', 'fr', 'en'])
        assert_equal(default, 'fr')

    def test_work_out_locales__locales_filtered_out(self):
        locales, default = Locales()._work_out_locales(
            ['en', 'fr', 'de'],
            {'ckan.locale': 'fr',
             'ckan.locales_filtered_out': 'de'})
        assert_equal(locales, ['fr', 'en'])
        assert_equal(default, 'fr')
        
    def test_work_out_locales__default(self):
        # don't specify default lang and it is not en,
        # so default to next in list.
        locales, default = Locales()._work_out_locales(
            ['en', 'fr', 'de'],
            {'ckan.locale': 'fr',
             'ckan.locales_filtered_out': 'en'})
        assert_equal(locales, ['fr', 'de'])
        assert_equal(default, 'fr')

    def test_work_out_locales__bad_default(self):
        assert_raises(ValueError, Locales()._work_out_locales, 
            ['en', 'fr', 'de'],
            {'ckan.locale': 'en',
             'ckan.locales_offered': 'fr de'})

    def test_get_available_locales(self):
        locales = Locales().get_available_locales()
        assert len(locales) > 5, locales
        locale = locales[0]
        assert isinstance(locale, Locale)

        locales_str = set([str(locale) for locale in locales])
        langs = set([locale.language for locale in locales])
        assert set(('en', 'de', 'cs_CZ')) < locales_str, locales_str
        assert set(('en', 'de', 'cs')) < langs, langs

    def test_default_locale(self):
        # This should be setup in test-core.ini
        assert_equal(config.get('ckan.locale_default'), 'en')
        default_locale = Locales().get_default_locale()
        assert isinstance(default_locale, Locale)
        assert_equal(default_locale.language, 'en')

    def test_negotiate_known_locale(self):
        # check exact matches always work
        locales = Locales().get_available_locales()
        for locale in locales:
            result = Locales().negotiate_known_locale([locale])
            assert_equal(result, locale)

        assert_equal(Locales().negotiate_known_locale(['en_US']), 'en')
        assert_equal(Locales().negotiate_known_locale(['en_AU']), 'en')
        assert_equal(Locales().negotiate_known_locale(['es_ES']), 'es')
        assert_equal(Locales().negotiate_known_locale(['pt']), 'pt_BR')

class TestI18n(PylonsTestCase):
    def test_set_session_locale(self):
        set_session_locale('en')
        assert_equal(session['locale'], 'en')

        set_session_locale('fr')
        assert_equal(session['locale'], 'fr')

    def handle_request(self, session_language=None, languages_header=[]):
        session['locale'] = session_language
        class FakePylons:
            translator = None
        class FakeRequest:
            # Populated from the HTTP_ACCEPT_LANGUAGE header normally
            languages = languages_header
            # Stores details of the translator
            environ = {'pylons.pylons': FakePylons()}
        request = FakeRequest()
        real_pylons_request = pylons.request
        try:
            pylons.request = request # for set_lang to work
            class FakeTmplContext:
                language = None # gets filled in by handle_request
            tmpl_context = FakeTmplContext()
            ckan.lib.i18n.handle_request(request, tmpl_context)
            return tmpl_context.language # the language that got set
        finally:
            pylons.request = real_pylons_request
    
    def test_handle_request__default(self):
        assert_equal(self.handle_request(),
                     'en')
        
    def test_handle_request__session(self):
        assert_equal(self.handle_request(session_language='fr'),
                     'fr')
## Browser lang detection disabled - see #1452

##    def test_handle_request__header(self):
##        assert_equal(self.handle_request(languages_header=['de']),
##                     'de')

##    def test_handle_request__header_negotiate(self):
##        # Language so is not an option, so reverts to next one
##        assert_equal(self.handle_request(languages_header=['so_KE', 'de']),
##                     'de')

##    def test_handle_request__header_but_defaults(self):
##        # Language so is not an option, so reverts to default
##        assert_equal(self.handle_request(languages_header=['so_KE']),
##                     'en')

##    def test_handle_request__header_territory(self):
##        # Request for specific version of German ends up simply as de.
##        assert_equal(self.handle_request(languages_header=['fr_CA', 'en']),
##                     'fr')
        
