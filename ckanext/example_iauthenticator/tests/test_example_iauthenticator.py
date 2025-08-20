# encoding: utf-8

from typing import Any
import pytest
from faker import Faker

import ckan.plugins as p
from ckan import model
from ckan.lib.authenticator import ckan_authenticator

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

    @pytest.mark.usefixtures("with_request_context")
    def test_fallback_authentication(self, user_factory: Any, faker: Faker):
        """If IAuthenticator.authenticate returns `None`, application tries
        other authenticators.

        """

        password = faker.password()
        user = user_factory(password=password)
        result = ckan_authenticator({
            "login": user["name"],
            "password": password,
            "use_fallback": True
        })
        assert result is not None
        assert result.name == user["name"]

    @pytest.mark.usefixtures("with_request_context")
    def test_rejected_authentication(self, user_factory: Any, faker: Faker):
        """If IAuthenticator.authenticate returns `model.AnonymousUser`,
        application ignores other implementations.

        """

        password = faker.password()
        user = user_factory(password=password)
        result = ckan_authenticator({
            "login": user["name"],
            "password": password
        })
        assert isinstance(result, model.AnonymousUser)
