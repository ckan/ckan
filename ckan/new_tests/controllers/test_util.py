from nose.tools import assert_equal
from pylons.test import pylonsapp
import paste.fixture

from routes import url_for as url_for

import ckan.new_tests.helpers as helpers


class TestUtil(helpers.FunctionalTestBaseClass):
    def test_redirect_ok(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': '/dataset'},
            status=302,
        )
        assert_equal(response.headers.get('Location'),
                     'http://localhost/dataset')

    def test_redirect_external(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': 'http://nastysite.com'},
            status=403,
        )

    def test_redirect_no_params(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={},
            status=400,
        )

    def test_redirect_no_params_2(self):
        response = self.app.get(
            url=url_for(controller='util', action='redirect'),
            params={'url': ''},
            status=400,
        )
