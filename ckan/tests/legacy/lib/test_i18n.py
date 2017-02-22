# encoding: utf-8

from nose.tools import assert_equal
import pylons

import ckan.lib.i18n
from ckan.common import config, session

from ckan.tests.legacy.pylons_controller import PylonsTestCase


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
            pylons.request = request  # for set_lang to work

            class FakeTmplContext:
                language = None  # gets filled in by handle_request
            tmpl_context = FakeTmplContext()
            ckan.lib.i18n.handle_request(request, tmpl_context)
            return tmpl_context.language  # the language that got set
        finally:
            pylons.request = real_pylons_request

    def test_handle_request__default(self):
        assert_equal(self.handle_request(),
                     config['ckan.locale_default'])
