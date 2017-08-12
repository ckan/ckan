# encoding: utf-8

from nose.tools import assert_equal

from ckan.lib.helpers import url_for

import ckan.tests.helpers as helpers


class TestUtil(helpers.FunctionalTestBase):
    def test_redirect_ok(self):
        app = self._get_test_app()

        with app.flask_app.test_request_context():
            url = url_for(controller='util', action='redirect')

        response = app.get(
            url,
            params={'url': '/dataset'},
            status=302,
        )
        assert_equal(response.headers.get('Location'),
                     'http://test.ckan.net/dataset')

    def test_redirect_external(self):
        app = self._get_test_app()

        with app.flask_app.test_request_context():
            url = url_for(controller='util', action='redirect')

        response = app.get(
            url,
            params={'url': 'http://nastysite.com'},
            status=403,
        )

    def test_redirect_no_params(self):
        app = self._get_test_app()

        with app.flask_app.test_request_context():
            url = url_for(controller='util', action='redirect')

        response = app.get(
            url,
            params={},
            status=400,
        )

    def test_redirect_no_params_2(self):
        app = self._get_test_app()

        with app.flask_app.test_request_context():
            url = url_for(controller='util', action='redirect')

        response = app.get(
            url,
            params={'url': ''},
            status=400,
        )
