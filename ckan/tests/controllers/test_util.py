# encoding: utf-8

from nose.tools import assert_equal
from pylons.test import pylonsapp
import paste.fixture

from routes import url_for as url_for

import ckan.tests.helpers as helpers


class TestUtil(helpers.FunctionalTestBase):
    def test_redirect_ok(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': '/dataset'},
            status=302,
        )
        assert_equal(response.headers.get('Location'),
                     'http://test.ckan.net/dataset')

    def test_redirect_external(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': 'http://nastysite.com'},
            status=403,
        )

    def test_redirect_no_params(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='redirect'),
            params={},
            status=400,
        )

    def test_redirect_no_params_2(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': ''},
            status=400,
        )
