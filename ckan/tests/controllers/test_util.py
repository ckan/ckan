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
                     'http://localhost/dataset')

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

    def test_set_timezone_valid(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='set_timezone_offset') + '/600',
            status=200,
        )
        assert_true('utc_timezone_offset: 600' in response)

    def test_set_timezone_string(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='set_timezone_offset') + '/test',
            status=400,
        )

    def test_set_timezone_too_big(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='set_timezone_offset') + '/1000',
            status=400,
        )

    def test_set_timezone_too_big(self):
        app = self._get_test_app()
        response = app.get(
            url=url_for(controller='util', action='set_timezone_offset') + '/-841',
            status=400,
        )
