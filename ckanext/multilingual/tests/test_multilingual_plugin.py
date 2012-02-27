import ckan.plugins
import ckan.lib.helpers
import ckan.lib.create_test_data
import ckan.logic.action.update
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
        ckan.lib.create_test_data.CreateTestData.create_translations_test_data()

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()

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
                ('fr', ckan.lib.create_test_data.french_translations), ('pl', {})):
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
