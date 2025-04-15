# encoding: utf-8

import re
import pytest
from flask import Blueprint, render_template

import ckan.lib.helpers as h
import ckan.plugins as p
from ckan.lib.redis import connect_to_redis
from ckan.tests.helpers import body_contains


@pytest.mark.ckan_config("ckan.plugins", "test_flash_plugin")
class TestWithFlashPlugin:
    def test_flash_success(self, app):
        """
        Test flash_success messages are rendered.
        """
        url = "/flash_success_redirect"
        res = app.get(url)
        assert body_contains(res, "This is a success message")
        assert body_contains(res, 'alert-success')

    def test_flash_success_with_html(self, app):
        """
        Test flash_success messages are rendered.
        """
        url = "/flash_success_html_redirect"
        res = app.get(url)
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
    def test_redis_storage(self, app, ckan_config, monkeypatch):
        """Redis session interface creates a record in redis upon request.
        """
        redis = connect_to_redis()

        assert not redis.keys("*")
        # A page that sets session
        response = app.post("/user/login")

        cookie = re.match(r'ckan=([^;]+)', response.headers['set-cookie'])
        assert cookie

        assert redis.keys("*") == [f"session:{cookie.group(1)}".encode()]

    @pytest.mark.usefixtures("clean_redis")
    @pytest.mark.ckan_config("SESSION_TYPE", "redis")
    def test_redis_storage_no_session(self, app, ckan_config, monkeypatch):
        """Redis session interface creates a record in redis upon request.
        """
        redis = connect_to_redis()

        assert not redis.keys("*")
        # A page that sets session
        response = app.post("/")
        assert 'set-cookie' not in response.headers
        assert not redis.keys("*")

    @pytest.mark.usefixtures("test_request_context")
    def test_cookie_storage(self, app, user_factory, faker):
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
