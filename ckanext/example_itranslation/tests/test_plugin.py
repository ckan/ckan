# encoding: utf-8

from ckan import plugins
from ckan.tests import helpers

from nose.tools import assert_true, assert_false


class TestExampleITranslationPlugin(helpers.FunctionalTestBase):

    @classmethod
    def _apply_config_changes(cls, config):
        config['ckan.plugins'] = 'example_itranslation'

    @classmethod
    def setup_class(cls):
        super(TestExampleITranslationPlugin, cls).setup_class()
        # plugins.load('example_itranslation')

    @classmethod
    def teardown_class(cls):
        if plugins.plugin_loaded('example_itranslation'):
            plugins.unload('example_itranslation')
        super(TestExampleITranslationPlugin, cls).teardown_class()

    def test_translated_string_in_extensions_templates(self):
        app = self._get_test_app()
        response = app.get(
            url=plugins.toolkit.url_for(u'home.index',
                                        locale='fr'),
        )
        assert_true('This is a itranslated string' in response.body)
        assert_false('This is an untranslated string' in response.body)

        # double check the untranslated strings
        response = app.get(
            url=plugins.toolkit.url_for(u'home.index'),
        )
        assert_true('This is an untranslated string' in response.body)
        assert_false('This is a itranslated string' in response.body)

    def test_translated_string_in_core_templates(self):
        app = self._get_test_app()
        response = app.get(
            url=plugins.toolkit.url_for(u'home.index',
                                        locale='fr'),
        )
        assert_true('Overwritten string in ckan.mo' in response.body)
        assert_false('Connexion' in response.body)

        # double check the untranslated strings
        response = app.get(
            url=plugins.toolkit.url_for(u'home.index'),
        )
        assert_true('Log in' in response.body)
        assert_false('Overwritten string in ckan.mo' in response.body)

        # check that we have only overwritten 'fr'
        response = app.get(
            url=plugins.toolkit.url_for(u'home.index', locale='de'),
        )
        assert_true('Einloggen' in response.body)
        assert_false('Overwritten string in ckan.mo' in response.body)

    def test_english_translation_replaces_default_english_string(self):
        app = self._get_test_app()
        response = app.get(
            url=plugins.toolkit.url_for(u'home.index'),
        )
        assert_true('Replaced' in response.body)
        assert_false('Register' in response.body)
