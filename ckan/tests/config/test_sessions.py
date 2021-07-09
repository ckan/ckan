# encoding: utf-8

import pytest
from flask import Blueprint, render_template

import ckan.lib.helpers as h
import ckan.plugins as p
from ckan.tests.helpers import body_contains


@pytest.mark.ckan_config("ckan.plugins", "test_flash_plugin")
@pytest.mark.usefixtures("with_request_context")
class TestWithFlashPlugin:
    def test_flash_success(self, app):
        """
        Test flash_success messages are rendered.
        """
        url = "/flash_success_redirect"
        res = app.get(url)
        assert body_contains(res, "This is a success message populated by Flask")


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
        h.flash_success(u"This is a success message populated by Flask")
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
                "/flask_view_flash_message",
                "flash_message_view",
                self.flash_message_view,
            ),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint
