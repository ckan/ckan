import ckan.plugins
import ckan.lib.helpers
import ckan.lib.create_test_data
import ckan.logic.action.update
import ckan.tests
import ckan.tests.html_check
import routes
import paste.fixture
import pylons.test
import nose

class TestDatasetTermTranslation(ckan.tests.html_check.HtmlCheckMethods):
    '''Test the translation of datasets by the multilingual_dataset plugin.

    '''
    @classmethod
    def setup(cls):
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        ckan.plugins.load('multilingual_dataset')
        ckan.tests.setup_test_search_index()
        ckan.lib.create_test_data.CreateTestData.create_translations_test_data()
        # Add translation terms that match a couple of group names and package
        # names. Group names and package names should _not_ get translated even
        # if there are terms matching them, because they are used to form URLs.
        for term in ('roger', 'david', 'annakarenina', 'warandpeace'):
            for lang_code in ('en', 'de', 'fr'):
                data_dict = {
                        'term': term,
                        'term_translation': 'this should not be rendered',
                        'lang_code': lang_code,
                        }
                context = {
                    'model': ckan.model,
                    'session': ckan.model.Session,
                    'user': 'testsysadmin',
                }
                ckan.logic.action.update.term_translation_update(context,
                        data_dict)

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()
        ckan.lib.search.clear()

    def test_dataset_view_translation(self):
        '''Test the translation of dataset view pages by the
        multilingual_dataset plugin.

        '''
        # Fetch the dataset view page for a number of different languages and
        # test for the presence of translated and not translated terms.
        offset = routes.url_for(controller='package', action='read',
                id='annakarenina')
        for (lang_code, translations) in (
                ('de', ckan.lib.create_test_data.german_translations),
                ('fr', ckan.lib.create_test_data.french_translations),
                ('en', ckan.lib.create_test_data.english_translations),
                ('pl', {})):
            response = self.app.get(offset, status=200,
                    extra_environ={'CKAN_LANG': lang_code,
                        'CKAN_CURRENT_URL': offset})
            for term in ckan.lib.create_test_data.terms:
                if term in translations:
                    response.mustcontain(translations[term])
                elif term in ckan.lib.create_test_data.english_translations:
                    response.mustcontain(
                        ckan.lib.create_test_data.english_translations[term])
                else:
                    response.mustcontain(term)
            for tag_name in ('123', '456', '789', 'russian', 'tolstoy'):
                response.mustcontain('<a href="/tag/%s">' % tag_name)
            for group_name in ('david', 'roger'):
                response.mustcontain('<a href="/group/%s">' % group_name)
            nose.tools.assert_raises(IndexError, response.mustcontain,
                    'this should not be rendered')

    @ckan.tests.search_related
    def test_dataset_search_results_translation(self):
        for (lang_code, translations) in (
                ('de', ckan.lib.create_test_data.german_translations),
                ('fr', ckan.lib.create_test_data.french_translations),
                ('en', ckan.lib.create_test_data.english_translations),
                ('pl', {})):
            offset = '/%s/dataset' % lang_code
            response = self.app.get(offset, status=200)
            for term in ('Index of the novel', 'russian', 'tolstoy',
                    "Dave's books", "Roger's books", 'plain text'):
                if term in translations:
                    response.mustcontain(translations[term])
                elif term in ckan.lib.create_test_data.english_translations:
                    response.mustcontain(
                        ckan.lib.create_test_data.english_translations[term])
                else:
                    response.mustcontain(term)
            for tag_name in ('123', '456', '789', 'russian', 'tolstoy'):
                response.mustcontain('/%s/dataset?tags=%s' % (lang_code, tag_name))
            for group_name in ('david', 'roger'):
                response.mustcontain('/%s/dataset?groups=%s' % (lang_code, group_name))
            nose.tools.assert_raises(IndexError, response.mustcontain,
                    'this should not be rendered')
