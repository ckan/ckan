# encoding: utf-8

import pytest
from flask import Blueprint, render_template
import re

from ckan.common import config
import ckan.lib.helpers as h
from ckan.lib.redis import connect_to_redis
import ckan.plugins as p
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


@pytest.mark.parametrize("timeout,normalized", [
    (None, None),
    ("", None),
    ("123", 123),
    ("1_000_000", 1_000_000),
    ("-1", -1),
])
def test_beaker_session_timeout(
        monkeypatch, ckan_config, make_app, timeout, normalized
):
    """Beaker timeout accepts `None`(never expires) and int(expires in
    n-seconds) values.

    """
    monkeypatch.setitem(ckan_config, "beaker.session.timeout", timeout)
    make_app()


@pytest.mark.usefixtures("clean_redis")
@pytest.mark.ckan_config("beaker.session.type", "ext:redis")
@pytest.mark.ckan_config("beaker.session.url", config["ckan.redis.url"])
def test_redis_storage(app, monkeypatch):
    """Redis session interface creates a record in redis upon request.
    """
    redis = connect_to_redis()

    assert not redis.keys("*")
    response = app.get("/")

    cookie = re.match(r'\W*ckan=([^;]+)', response.headers['set-cookie'])
    assert cookie

    assert redis.keys("*") == [f"beaker_cache:{cookie.group(1)[-32:]}:session".encode()]


@pytest.mark.ckan_config("beaker.session.type", "ext:redis")
@pytest.mark.ckan_config("beaker.session.url", config["ckan.redis.url"])
def test_redis_session_fixation(app, monkeypatch, user_factory, faker):
    """Session id is regenerated on login
    """

    # app convenience functions use separate test client for each request
    # so cookies aren't saved.
    test_client = app.test_client()

    response = test_client.get("/")
    orig_cookie = re.match(r'\W*ckan=([^;]+)', response.headers['set-cookie'])
    assert orig_cookie
    cookie_header = 'ckan=%s' % orig_cookie.group(1)
    same_session = test_client.get("/")
    # assert that we're using the same session prior to logging in.
    assert same_session.request.headers['cookie'] == cookie_header
    password = faker.password()
    user = user_factory(password=password)

    login_response = test_client.post(h.url_for("user.login"),
                                      follow_redirects=False,
                                      data={
                                          "login": user["name"],
                                          "password": password,
                                      }
                                      )

    assert 'set-cookie' in login_response.headers
    login_cookie = re.match(r'\W*ckan=([^;]+)', login_response.headers['set-cookie'])
    # assert that we're setting a new cookie on login.
    assert login_cookie.group(1) != orig_cookie.group(1)

