# encoding: utf-8

import pytest
import six
from flask import Blueprint, render_template

import ckan.lib.helpers as h
import ckan.plugins as p
from ckan.lib.base import render as pylons_render
from ckan.tests.helpers import body_contains


@pytest.mark.ckan_config(u"ckan.plugins", u"test_flash_plugin")
@pytest.mark.usefixtures(u"with_request_context")
class TestWithFlashPlugin:
    # @pytest.mark.skipif(six.PY3, reason=u"There is no pylons app in Py3")
    def test_flash_populated_by_flask_redirect_to_flask(self, app):
        u"""
        Flash store is populated by Flask view is accessible by another Flask
        view.
        """
        url = u"/flask_add_flash_message_redirect_to_flask"
        res = app.get(url)
        assert body_contains(res, u"This is a success message populated by Flask")

    @pytest.mark.skipif(six.PY3, reason=u"There is no pylons app in Py3")
    def test_flash_populated_in_pylons_action_redirect_to_flask(self, app):
        u"""
        Flash store is populated by pylons action is accessible by Flask view.
        """
        res = app.get(u"/pylons_add_flash_message_redirect_view")

        assert body_contains(res, u"This is a success message populated by Pylons")

    @pytest.mark.skipif(six.PY3, reason=u"There is no pylons app in Py3")
    def test_flash_populated_in_flask_view_redirect_to_pylons(self, app):
        u"""
        Flash store is populated by flask view is accessible by pylons action.
        """
        res = app.get(u"/flask_add_flash_message_redirect_pylons")

        assert body_contains(res, u"This is a success message populated by Flask")


class FlashMessagePlugin(p.SingletonPlugin):
    u"""
    A Flask and Pylons compatible IRoutes/IBlueprint plugin to add Flask views
    and Pylons actions to display flash messages.
    """

    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IBlueprint)

    def flash_message_view(self):
        u"""Flask view that renders the flash message html template."""
        return render_template(u"tests/flash_messages.html")

    def add_flash_message_view_redirect_to_flask(self):
        u"""Add flash message, then redirect to Flask view to render it."""
        h.flash_success(u"This is a success message populated by Flask")
        return h.redirect_to(
            h.url_for(u"test_flash_plugin.flash_message_view")
        )

    def add_flash_message_view_redirect_to_pylons(self):
        u"""Add flash message, then redirect to view that renders it"""
        h.flash_success(u"This is a success message populated by Flask")
        return h.redirect_to(u"/pylons_view_flash_message")

    def get_blueprint(self):
        u"""Return Flask Blueprint object to be registered by the Flask app."""

        # Create Blueprint for plugin
        blueprint = Blueprint(self.name, self.__module__)
        # Add plugin url rules to Blueprint object
        rules = [
            (
                u"/flask_add_flash_message_redirect_to_flask",
                u"add_flash_message",
                self.add_flash_message_view_redirect_to_flask,
            ),
            (
                u"/flask_add_flash_message_redirect_pylons",
                u"add_flash_message_view_redirect_to_pylons",
                self.add_flash_message_view_redirect_to_pylons,
            ),
            (
                u"/flask_view_flash_message",
                u"flash_message_view",
                self.flash_message_view,
            ),
        ]
        for rule in rules:
            blueprint.add_url_rule(*rule)

        return blueprint

    controller = (
        u"ckan.tests.config.test_sessions:PylonsAddFlashMessageController"
    )

    def before_map(self, _map):
        u"""Update the pylons route map to be used by the Pylons app."""
        _map.connect(
            u"/pylons_add_flash_message_redirect_view",
            controller=self.controller,
            action=u"add_flash_message_redirect",
        )

        _map.connect(
            u"/pylons_view_flash_message",
            controller=self.controller,
            action=u"flash_message_action",
        )
        return _map


if six.PY2:
    class PylonsAddFlashMessageController(p.toolkit.BaseController):
        def flash_message_action(self):
            u"""Pylons view to render flash messages in a template."""
            return pylons_render(u"tests/flash_messages.html")

        def add_flash_message_redirect(self):
            # Adds a flash message and redirects to flask view
            h.flash_success(u"This is a success message populated by Pylons")
            return h.redirect_to(u"/flask_view_flash_message")
