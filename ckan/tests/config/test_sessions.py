# encoding: utf-8

import re
import pytest
from flask import Blueprint, render_template

import ckan.lib.helpers as h
import ckan.plugins as p
from ckan.config.middleware.flask_app import CKANJsonSessionSerializer
from ckan.lib.redis import connect_to_redis
from ckan import common as c
from ckan.tests.helpers import body_contains, CKANTestApp


@pytest.mark.ckan_config("ckan.plugins", "test_flash_plugin")
class TestWithFlashPlugin:
    def test_flash_success(self, app: CKANTestApp):
        """
        Test flash_success messages are rendered.
        """
        url = "/flash_success_redirect"
        res = app.get(url)
        assert body_contains(res, "This is a success message")
        assert body_contains(res, 'alert-success')

    @pytest.mark.parametrize("session_type", ["cookie", "redis"])
    def test_flash_success_with_html(
            self, make_app, session_type, ckan_config, monkeypatch,
    ):
        """Test flash_success messages are rendered.

        After migration to flask-session, cookie and other backends are using a
        bit different strategies for session data serialization, so it's better
        to test both options with JSON incompatible data, like Markup produced
        by flash messages.
        """
        monkeypatch.setitem(ckan_config, "SESSION_TYPE", session_type)
        url = "/flash_success_html_redirect"
        res = make_app().get(url)
        assert body_contains(res, "<h1> This is a success message with HTML</h1>")
        assert body_contains(res, 'alert-success')


class FlashMessagePlugin(p.SingletonPlugin):
    """
    A Flask compatible IBlueprint plugin to add Flask views to display flash
    messages.
    """

    p.implements(p.IBlueprint)

    def flash_message_view(self):
        """Flask view that renders the flash message html template."""
        return render_template("tests/flash_messages.html")

    def add_flash_success_message(self):
        """Add flash message, then redirect to render it."""
        h.flash_success(u"This is a success message")
        return h.redirect_to(
            h.url_for("test_flash_plugin.flash_message_view")
        )

    def add_flash_success_message_with_html(self):
        """Add flash message, then redirect to render it."""
        h.flash_success(u"<h1> This is a success message with HTML</h1>", allow_html=True)
        return h.redirect_to(
            h.url_for("test_flash_plugin.flash_message_view")
        )

    def get_blueprint(self):
        """Return Flask Blueprint object."""

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        # Add plugin url rules to Blueprint object
        rules = [
            (
                "/flash_success_redirect",
                "add_flash_success_message",
                self.add_flash_success_message,
            ),
            (
                "/flash_success_html_redirect",
                "add_flash_success_message_with_html",
                self.add_flash_success_message_with_html,
            ),
            (
                "/flask_view_flash_message",
                "flash_message_view",
                self.flash_message_view,
            ),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint


class TestSessionTypes:
    @pytest.mark.usefixtures("clean_redis")
    @pytest.mark.ckan_config("SESSION_TYPE", "redis")
    def test_redis_storage(self, app: CKANTestApp, monkeypatch):
        """Redis session interface creates a record in redis upon request.
        """
        redis = connect_to_redis()

        assert not redis.keys("*")
        response = app.get("/")

        cookie = re.match(r'ckan=([^;]+)', response.headers['set-cookie'])
        assert cookie

        assert redis.keys("*") == [f"session:{cookie.group(1)}".encode()]

    @pytest.mark.usefixtures("test_request_context")
    def test_cookie_storage(self, app: CKANTestApp, user_factory, faker):
        """User's ID added to session cookie upon login
        """
        password = faker.password()
        user = user_factory(password=password)

        response = app.post(h.url_for("user.login"), data={
            "login": user["name"],
            "password": password
        })

        cookie = re.match(r'ckan=([^;]+)', response.headers['set-cookie'])
        assert cookie

        serializer = app.flask_app.session_interface.get_signing_serializer(
            app.flask_app
        )
        data = serializer.loads(cookie.group(1))
        assert data["_user_id"] == user["id"]


@pytest.mark.ckan_config("SESSION_TYPE", "redis")
class TestCKANJsonSessionSerializer:
    def test_encode_returns_bytes(self, app: CKANTestApp):
        with app.flask_app.test_request_context():
            serializer = CKANJsonSessionSerializer()
            session = c.session
            session['user_id'] = '123'

            encoded = serializer.encode(session)
            assert isinstance(encoded, bytes)
            assert b'"user_id":"123"' in encoded

    def test_decode_round_trip(self, app: CKANTestApp):
        with app.flask_app.test_request_context():
            serializer = CKANJsonSessionSerializer()
            session = c.session
            session['theme'] = 'qld'

            encoded = serializer.encode(session)
            decoded = serializer.decode(encoded)
            assert decoded == session

    def test_decode_unicode_error_logs(self, app: CKANTestApp):
        with app.flask_app.test_request_context():
            serializer = CKANJsonSessionSerializer()
            bad_data = b'\xff\xfe\xfd'  # Invalid UTF-8

            result = serializer.decode(bad_data)

            assert result is None
