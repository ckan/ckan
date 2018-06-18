# encoding: utf-8

u'''
Tests for ``ckan.lib.i18n``.
'''

import codecs
import json
import os.path
import shutil
import tempfile

from nose.tools import eq_, ok_

from ckan.lib import i18n
import ckan.plugins as p
from ckan import plugins
from ckan.lib.plugins import DefaultTranslation
from ckan.tests import helpers


HERE = os.path.abspath(os.path.dirname(__file__))
I18N_DIR = os.path.join(HERE, u'_i18n_build_js_translations')


class TestJSTranslationsPlugin(plugins.SingletonPlugin, DefaultTranslation):
    u'''
    CKAN plugin for testing JavaScript translations from extensions.

    Registered in ``setup.py`` as ``test_js_translations_plugin``.
    '''
    plugins.implements(plugins.ITranslation)

    def i18n_directory(self):
        return I18N_DIR

    def i18n_domain(self):
        return u'ckanext-test_js_translations'


class TestBuildJSTranslations(object):
    u'''
    Tests for ``ckan.lib.i18n.build_js_translations``.
    '''
    @classmethod
    def setup_class(cls):
        if not plugins.plugin_loaded(u'test_js_translations_plugin'):
            plugins.load(u'test_js_translations_plugin')

    @classmethod
    def teardown_class(cls):
        plugins.unload(u'test_js_translations_plugin')

    def setup(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def build_js_translations(self):
        u'''
        Build JS translations in temporary directory.
        '''
        old_translations_dir = i18n._JS_TRANSLATIONS_DIR
        i18n._JS_TRANSLATIONS_DIR = self.temp_dir
        try:
            return i18n.build_js_translations()
        finally:
            i18n._JS_TRANSLATIONS_DIR = old_translations_dir

    def test_output_is_valid(self):
        u'''
        Test that the generated JS files are valid.
        '''
        def check_file(path):
            with codecs.open(path, u'r', encoding=u'utf-8') as f:
                data = json.load(f)
            eq_(data[u''].get(u'domain', None), u'ckan')

        self.build_js_translations()
        files = os.listdir(self.temp_dir)

        # Check that all locales have been generated
        eq_(set(i18n.get_locales()).difference([u'en']),
            set(os.path.splitext(fn)[0] for fn in files))

        # Check that each file is valid
        for filename in files:
            check_file(os.path.join(self.temp_dir, filename))

    def test_regenerate_only_if_necessary(self):
        u'''
        Test that translation files are only generated when necessary.
        '''
        self.build_js_translations()
        mtimes = {}
        for filename in os.listdir(self.temp_dir):
            fullname = os.path.join(self.temp_dir, filename)
            mtimes[filename] = os.path.getmtime(fullname)

        # Remove an output file and back-date another one
        removed_filename, outdated_filename = sorted(mtimes.keys())[:2]
        removed_mtime = mtimes.pop(removed_filename)
        outdated_mtime = mtimes.pop(outdated_filename)
        os.remove(os.path.join(self.temp_dir, removed_filename))
        os.utime(os.path.join(self.temp_dir, outdated_filename), (0, 0))

        self.build_js_translations()

        # Make sure deleted file has been rebuild
        ok_(os.path.isfile(os.path.join(self.temp_dir, removed_filename)))

        # Make sure outdated file has been rebuild
        fullname = os.path.join(self.temp_dir, outdated_filename)
        ok_(os.path.getmtime(fullname) >= outdated_mtime)

        # Make sure the other files have not been rebuild
        for filename in os.listdir(self.temp_dir):
            if filename in [removed_filename, outdated_filename]:
                continue
            fullname = os.path.join(self.temp_dir, filename)
            new_mtime = os.path.getmtime(fullname)
            eq_(new_mtime, mtimes[filename])

    def test_translations_from_extensions(self):
        u'''
        Test that translations from extensions are taken into account.
        '''
        self.build_js_translations()
        filename = os.path.join(self.temp_dir, u'de.js')
        with codecs.open(filename, u'r', encoding=u'utf-8') as f:
            de = json.load(f)

        # Check overriding a JS translation from CKAN core
        ok_(u'Loading...' in de)
        eq_(de[u'Loading...'], [None, u'foo'])

        # Check introducing a new JS translation
        ok_(u'Test JS Translations 1' in de)
        eq_(de[u'Test JS Translations 1'], [None, u'bar'])

        # Check that non-JS strings are not exported
        ok_(u'Test JS Translations 2' not in de)


class TestI18nFlaskAndPylons(object):

    def test_translation_works_on_flask_and_pylons(self):

        app = helpers._get_test_app()
        if not p.plugin_loaded(u'test_routing_plugin'):
            p.load(u'test_routing_plugin')
        try:
            plugin = p.get_plugin(u'test_routing_plugin')
            app.flask_app.register_extension_blueprint(
                plugin.get_blueprint())

            resp = app.get(u'/flask_translated')

            eq_(resp.body, u'Dataset')

            resp = app.get(u'/es/flask_translated')

            eq_(resp.body, u'Conjunto de datos')

            resp = app.get(u'/pylons_translated')

            eq_(resp.body, u'Groups')

            resp = app.get(u'/es/pylons_translated')

            eq_(resp.body, u'Grupos')

        finally:

            if p.plugin_loaded(u'test_routing_plugin'):
                p.unload(u'test_routing_plugin')
