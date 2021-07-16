# encoding: utf-8

import pytest

import ckan.plugins as p

toolkit = p.toolkit


@pytest.mark.ckan_config('ckan.plugins', 'example_iauthenticator')
@pytest.mark.usefixtures('with_plugins')
class TestExampleIAuthenticator(object):

    def test_identify_sets_cookie(self, app):

        resp = app.get(toolkit.url_for('home.index'))

        assert 'example_iauthenticator=hi' in resp.headers['Set-Cookie']

    def test_login_redirects(self, app):

        resp = app.get(
            toolkit.url_for('user.login'),
            follow_redirects=False
        )

        assert resp.status_code == 302
        assert resp.headers['Location'] == toolkit.url_for('example_iauthenticator.custom_login', _external=True)

    def test_logout_redirects(self, app):

        resp = app.get(
            toolkit.url_for('user.logout'),
            follow_redirects=False
        )

        assert resp.status_code == 302
        assert resp.headers['Location'] == toolkit.url_for('example_iauthenticator.custom_logout', _external=True)
