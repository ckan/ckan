# encoding: utf-8

import pytest

import ckan.plugins as p

toolkit = p.toolkit


@pytest.mark.ckan_config(u'ckan.plugins', u'example_iauthenticator')
@pytest.mark.usefixtures(u'with_plugins')
class TestExampleIAuthenticator(object):

    def test_identify_sets_cookie(self, app):

        resp = app.get(toolkit.url_for(u'home.index'))

        assert u'example_iauthenticator=hi' in resp.headers[u'Set-Cookie']

    def test_login_redirects(self, app):

        resp = app.get(
            toolkit.url_for(u'user.login'),
            follow_redirects=False
        )

        assert resp.status_code == 302
        assert resp.headers[u'Location'] == toolkit.url_for(u'example_iauthenticator.custom_login', _external=True)

    def test_logout_redirects(self, app):

        resp = app.get(
            toolkit.url_for(u'user.logout'),
            follow_redirects=False
        )

        assert resp.status_code == 302
        assert resp.headers[u'Location'] == toolkit.url_for(u'example_iauthenticator.custom_logout', _external=True)
