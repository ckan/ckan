import ckan.plugins
import ckan.lib.helpers
import ckan.logic.action.update
import ckan.tests.html_check
import routes
import paste.fixture
import pylons.test


class TestDatasetTermTranslation(ckan.tests.html_check.HtmlCheckMethods):
    '''Test the translation of datasets by the multilingual_dataset plugin.

    '''
    @classmethod
    def setup(cls):
        ckan.tests.CreateTestData.create()
        cls.normal_user = ckan.model.User.get('annafan')
        cls.sysadmin_user = ckan.model.User.get('testsysadmin')
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        ckan.plugins.load('multilingual_dataset')

    @classmethod
    def teardown(cls):
        ckan.model.repo.rebuild_db()

    def test_dataset_view_translation(self):
        '''Test the translation of dataset view pages by the
        multilingual_dataset plugin.

        '''
        # Get a package.
        context = {
            'model': ckan.model,
            'session': ckan.model.Session,
            'user': self.normal_user.name,
            'allow_partial_update': True
        }
        package = ckan.logic.action.get.package_show(context,
                {'id': "annakarenina"})

        # Add some new tags to the package.
        # These tags are codes that are meant to be always translated before
        # display, if not into the user's current language then into the
        # fallback language.
        new_tag_list = package['tags'] + [
                {'name': '123'},
                {'name': '456'},
                {'name': '789'},
                ]
        data_dict = {
            'id': package['id'],
            'tags': new_tag_list
            }
        package = ckan.logic.action.update.package_update(context, data_dict)

        # Test translations for some of the package's fields.
        terms = ('A Novel By Tolstoy',
            'Index of the novel',
            'russian',
            'tolstoy',
            "Dave's books",
            "Roger's books",
            'Other (Open)',
            'romantic novel',
            'book',
            '123',
            '456',
            '789',
            )
        english_translations = {
            '123': 'jealousy',
            '456': 'realism',
            '789': 'hypocrisy',
                }
        german_translations = {
            'A Novel By Tolstoy': 'Roman von Tolstoi',
            'Index of the novel': 'Index des Romans',
            'russian': 'Russisch',
            'tolstoy': 'Tolstoi',
            "Dave's books": 'Daves Bucher',
            "Roger's books": 'Rogers Bucher',
            'Other (Open)': 'Andere (Open)',
            'romantic novel': 'Liebesroman',
            'book': 'Buch',
            '456': 'Realismus',
            '789': 'Heuchelei',
                }
        french_translations = {
            'A Novel By Tolstoy': 'A Novel par Tolstoi',
            'Index of the novel': 'Indice du roman',
            'russian': 'russe',
            'romantic novel': 'roman romantique',
            'book': 'livre',
            '123': 'jalousie',
            '789': 'hypocrisie',
                }

        # Use the term_translation_update API to add the above translations to
        # CKAN.
        for (lang_code, translations) in (('de', german_translations),
                ('fr', french_translations), ('en', english_translations)):
            for term in terms:
                if term in translations:
                    paramd = {
                            'term': term,
                            'term_translation': translations[term],
                            'lang_code': lang_code,
                            }
                    response = self.app.post(
                            '/api/action/term_translation_update',
                            params=ckan.lib.helpers.json.dumps(paramd),
                            extra_environ={
                                'Authorization': str(self.sysadmin_user.apikey)
                                },
                            status=200)
                    assert response.json['success'] is True

        # Fetch the dataset view page for a number of different languages and
        # test for the presence of translated and not translated terms.
        offset = routes.url_for(controller='package', action='read',
                id='annakarenina')
        for (lang_code, translations) in (('de', german_translations),
                ('fr', french_translations), ('pl', {})):
            response = self.app.get(offset, status=200,
                    extra_environ={'CKAN_LANG': lang_code,
                        'CKAN_CURRENT_URL': offset})
            for term in terms:
                if term in translations:
                    response.mustcontain(translations[term])
                elif term in english_translations:
                    response.mustcontain(english_translations[term])
                else:
                    response.mustcontain(term)
