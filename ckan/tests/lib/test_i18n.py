# encoding: utf-8

u"""
Tests for ``ckan.lib.i18n``.
"""

import codecs
import json
import os.path
import shutil
import tempfile

import six
import pytest
from ckan.lib import i18n
from ckan import plugins
from ckan.lib.plugins import DefaultTranslation


HERE = os.path.abspath(os.path.dirname(__file__))
I18N_DIR = os.path.join(HERE, u"_i18n_build_js_translations")
I18N_DUMMY_DIR = os.path.join(HERE, u"_i18n_dummy_es")


class JSTranslationsTestPlugin(plugins.SingletonPlugin, DefaultTranslation):
    u"""
    CKAN plugin for testing JavaScript translations from extensions.

    Registered in ``setup.py`` as ``test_js_translations_plugin``.
    """
    plugins.implements(plugins.ITranslation)

    def i18n_directory(self):
        return I18N_DIR

    def i18n_domain(self):
        return u"ckanext-test_js_translations"


@pytest.mark.ckan_config(u"ckan.plugins", u"test_js_translations_plugin")
@pytest.mark.usefixtures(u"with_plugins")
class TestBuildJSTranslations(object):
    u"""
    Tests for ``ckan.lib.i18n.build_js_translations``.
    """

    def setup(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def build_js_translations(self):
        u"""
        Build JS translations in temporary directory.
        """
        old_translations_dir = i18n._JS_TRANSLATIONS_DIR
        i18n._JS_TRANSLATIONS_DIR = self.temp_dir
        try:
            return i18n.build_js_translations()
        finally:
            i18n._JS_TRANSLATIONS_DIR = old_translations_dir

    def test_output_is_valid(self):
        u"""
        Test that the generated JS files are valid.
        """

        def check_file(path):
            with codecs.open(path, u"r", encoding=u"utf-8") as f:
                data = json.load(f)
            assert data[u""].get(u"domain", None) == u"ckan"

        self.build_js_translations()
        files = os.listdir(self.temp_dir)

        # Check that all locales have been generated
        assert set(i18n.get_locales()).difference([u"en"]) == set(
            os.path.splitext(fn)[0] for fn in files
        )

        # Check that each file is valid
        for filename in files:
            check_file(os.path.join(self.temp_dir, filename))

    def test_regenerate_only_if_necessary(self):
        u"""
        Test that translation files are only generated when necessary.
        """
        self.build_js_translations()
        mtimes = {}
        for filename in os.listdir(self.temp_dir):
            fullname = os.path.join(self.temp_dir, filename)
            mtimes[filename] = os.path.getmtime(fullname)

        # Remove an output file and back-date another one
        removed_filename, outdated_filename = sorted(mtimes.keys())[:2]
        mtimes.pop(removed_filename)
        outdated_mtime = mtimes.pop(outdated_filename)
        os.remove(os.path.join(self.temp_dir, removed_filename))
        os.utime(os.path.join(self.temp_dir, outdated_filename), (0, 0))

        self.build_js_translations()

        # Make sure deleted file has been rebuild
        assert os.path.isfile(os.path.join(self.temp_dir, removed_filename))

        # Make sure outdated file has been rebuild
        fullname = os.path.join(self.temp_dir, outdated_filename)
        assert os.path.getmtime(fullname) >= outdated_mtime

        # Make sure the other files have not been rebuild
        for filename in os.listdir(self.temp_dir):
            if filename in [removed_filename, outdated_filename]:
                continue
            fullname = os.path.join(self.temp_dir, filename)
            new_mtime = os.path.getmtime(fullname)
            assert new_mtime == mtimes[filename]

    def test_translations_from_extensions(self):
        u"""
        Test that translations from extensions are taken into account.
        """
        self.build_js_translations()
        filename = os.path.join(self.temp_dir, u"de.js")
        with codecs.open(filename, u"r", encoding=u"utf-8") as f:
            de = json.load(f)

        # Check overriding a JS translation from CKAN core
        assert u"Loading..." in de
        assert de[u"Loading..."] == [None, u"foo"]

        # Check introducing a new JS translation
        assert u"Test JS Translations 1" in de
        assert de[u"Test JS Translations 1"] == [None, u"bar"]

        # Check that non-JS strings are not exported
        assert u"Test JS Translations 2" not in de


@pytest.mark.ckan_config(u"ckan.plugins", u"test_blueprint_plugin")
@pytest.mark.usefixtures(u"with_plugins")
class TestI18nFlask(object):
    def test_translation_works_on_flask_and_pylons(self, app):
        resp = app.get(u"/view_translated")
        assert six.ensure_text(resp.data) == str(u"Dataset")

        resp = app.get(u"/es/view_translated")
        assert six.ensure_text(resp.data) == str(u"Conjunto de datos")

    @pytest.mark.ckan_config(u"ckan.i18n_directory", I18N_DUMMY_DIR)
    def test_config_i18n_directory(self, app):
        resp = app.get(u"/view_translated")
        assert six.ensure_text(resp.data) == str(u"Dataset")

        resp = app.get(u"/es/view_translated")
        assert six.ensure_text(resp.data) == str(u"Foo baz 123")
