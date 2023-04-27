# encoding: utf-8

import pytest

from ckan import plugins
from ckan.tests import helpers


@pytest.mark.ckan_config("ckan.plugins", u"example_itranslation")
@pytest.mark.usefixtures("with_plugins")
class TestExampleITranslationPlugin(object):

    def test_translated_string_in_extensions_templates(self, app):
        response = app.get(
            url=plugins.toolkit.url_for(u"home.index", locale="fr"),
        )
        assert helpers.body_contains(response, "This is a itranslated string")
        assert not helpers.body_contains(response, "This is an untranslated string")

        # double check the untranslated strings
        response = app.get(url=plugins.toolkit.url_for(u"home.index"),)
        assert helpers.body_contains(response, "This is an untranslated string")
        assert not helpers.body_contains(response, "This is a itranslated string")

    def test_translated_string_in_core_templates(self, app):
        response = app.get(
            url=plugins.toolkit.url_for(u"home.index", locale="fr"),
        )
        assert helpers.body_contains(response, "Overwritten string in ckan.mo")
        assert not helpers.body_contains(response, "Connexion")

        # double check the untranslated strings
        response = app.get(url=plugins.toolkit.url_for(u"home.index"),)
        assert helpers.body_contains(response, "Log in")
        assert not helpers.body_contains(response, "Overwritten string in ckan.mo")

        # check that we have only overwritten 'fr'
        response = app.get(
            url=plugins.toolkit.url_for(u"home.index", locale="de"),
        )
        assert helpers.body_contains(response, "Einloggen")
        assert not helpers.body_contains(response, "Overwritten string in ckan.mo")

    @pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
    def test_english_translation_replaces_default_english_string(self, app):
        response = app.get(url=plugins.toolkit.url_for(u"home.index"),)
        assert helpers.body_contains(response, "Replaced")
        assert not helpers.body_contains(response, "Register")
