# encoding: utf-8

from typing import Any
from unittest import mock
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


@pytest.mark.ckan_config("ckan.plugins", "example_iauthenticator")
@pytest.mark.usefixtures("with_plugins")
class TestIdentification:
    @pytest.fixture
    def identify_mock(self, monkeypatch: pytest.MonkeyPatch):
        plugin = p.get_plugin("example_iauthenticator")
        func = mock.Mock(return_value=None)
        monkeypatch.setattr(plugin, "identify_user", func)
        return func

    def test_anonymous(self, app: Any, identify_mock: mock.Mock):
        """Anonymous request without session relies only on request
        identifier."""
        app.get(toolkit.url_for('home.index'))
        identify_mock.assert_called_once_with()

    @pytest.mark.usefixtures("non_clean_db")
    def test_remembered_user(
            self,
            app: Any, user: dict[str, Any],
            identify_mock: mock.Mock,
    ):
        """Request with valid remember-cookie relies only on session
        identifier."""
        app.set_remember_user(user["name"])
        app.get(toolkit.url_for('home.index'))
        identify_mock.assert_called_once_with(user["name"])

    def test_remembered_invalid_user(self, app: Any, identify_mock: mock.Mock):
        """Failed session identification via remember-cookie does not fallback
        to request identifier(unlike identification via session data)."""
        name = "NOT A REAL USER"
        app.set_remember_user(name)
        app.get(toolkit.url_for('home.index'))
        identify_mock.assert_called_with(name)

    @pytest.mark.usefixtures("non_clean_db")
    def test_session_user(
            self, app: Any, user: dict[str, Any],
            identify_mock: mock.Mock,
    ):
        """Request with valid session relies only on session
        identifier."""
        app.set_session_user(user["name"])
        app.get(toolkit.url_for('home.index'))
        identify_mock.assert_called_once_with(user["id"])

    @pytest.mark.usefixtures("non_clean_db")
    def test_session_invalid_user(
            self, app: Any, user_factory: Any,
            identify_mock: mock.Mock,
    ):
        """Failed session identification via session data makes an attempt to
        identify user via request identifier."""
        user = user_factory.model()
        app.set_session_user(user.id)
        model.Session.delete(user)
        model.Session.commit()

        app.get(toolkit.url_for('home.index'))
        identify_mock.assert_has_calls([mock.call(user.id), mock.call()])
