from nose import tools as nosetools

import ckan.new_tests.helpers as helpers
import ckan.plugins as plugins


class TestExampleIConfigurer(helpers.FunctionalTestBase):

    @classmethod
    def setup_class(cls):
        super(TestExampleIConfigurer, cls).setup_class()
        plugins.load('example_iconfigurer')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iconfigurer')
        super(TestExampleIConfigurer, cls).teardown_class()

    def test_template_renders(self):
        '''Our controller renders the extension's config template.'''
        app = self._get_test_app()
        response = app.get('/ckan-admin/myext_config_one', status=200)
        nosetools.assert_true('My First Config Page' in response)
