# encoding: utf-8

import pytest

import ckan.plugins as p

toolkit = p.toolkit


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthenticator')
@pytest.mark.usefixtures('with_plugins')
class TestExampleIAuthenticator(object):

    def test_identify_sets_cookie(self, app):
        resp = app.get("/")
        assert 'example_iauthenticator=hi' in resp.headers['Set-Cookie']

    def test_login_redirects(self, app):

        resp = app.get("/user/login", follow_redirects=False)

        assert resp.status_code == 302
        with app.flask_app.test_request_context():
            expected = toolkit.url_for('example_iauthenticator.custom_login', _external=True)
        assert resp.headers[u'Location'] == expected

    def test_logout_redirects(self, app):

        resp = app.get("/user/_logout", follow_redirects=False)

        assert resp.status_code == 302
        with app.flask_app.test_request_context():
            expected = toolkit.url_for('example_iauthenticator.custom_logout', _external=True)
        assert resp.headers['Location'] == expected
