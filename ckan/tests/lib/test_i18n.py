from nose.tools import assert_equal, assert_raises
from pylons import config, session
import pylons

import ckan.lib.i18n

from ckan.tests.pylons_controller import PylonsTestCase


class TestI18n(PylonsTestCase):

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
                     config['ckan.locale_default'])

## Session no longer used to set languages so test no longer relevant
## see #1653

##    def test_handle_request__session(self):
##        assert_equal(self.handle_request(session_language='fr'),
##                     'fr')

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

