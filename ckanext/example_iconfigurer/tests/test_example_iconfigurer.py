# encoding: utf-8

from nose import tools as nosetools

import ckan.tests.helpers as helpers
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

    def test_config_page_has_custom_tabs(self):
        '''
        The admin base template should include our custom ckan-admin tabs
        added using the toolkit.add_ckan_admin_tab method.
        '''
        app = self._get_test_app()
        response = app.get('/ckan-admin/myext_config_one', status=200)
        # The label text
        nosetools.assert_true('My First Custom Config Tab' in response)
        nosetools.assert_true('My Second Custom Config Tab' in response)
        # The link path
        nosetools.assert_true('/ckan-admin/myext_config_one' in response)
        nosetools.assert_true('/ckan-admin/myext_config_two' in response)


class TestExampleIConfigurerBuildExtraAdminTabsHelper(helpers.FunctionalTestBase):

    """Tests for helpers.build_extra_admin_nav method."""

    @classmethod
    def setup_class(cls):
        super(TestExampleIConfigurerBuildExtraAdminTabsHelper, cls).setup_class()
        plugins.load('example_iconfigurer')

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_iconfigurer')
        super(TestExampleIConfigurerBuildExtraAdminTabsHelper, cls).teardown_class()

    @helpers.change_config('ckan.admin_tabs', {})
    def test_build_extra_admin_nav_config_option_present_but_empty(self):
        '''
        Empty string returned when ckan.admin_tabs option in config but empty.
        '''
        app = self._get_test_app()
        expected = ""
        response = app.get('/build_extra_admin_nav')
        nosetools.assert_equal(response.body, expected)

    @helpers.change_config('ckan.admin_tabs', {'ckanext_myext_config_one': 'My Label'})
    def test_build_extra_admin_nav_one_value_in_config(self):
        '''
        Correct string returned when ckan.admin_tabs option has single value in config.
        '''
        app = self._get_test_app()
        expected = """<li><a href="/ckan-admin/myext_config_one"><i class="fa fa-picture-o"></i> My Label</a></li>"""
        response = app.get('/build_extra_admin_nav')
        nosetools.assert_equal(response.body, expected)

    @helpers.change_config('ckan.admin_tabs', {'ckanext_myext_config_one': 'My Label', 'ckanext_myext_config_two': 'My Other Label'})
    def test_build_extra_admin_nav_two_values_in_config(self):
        '''
        Correct string returned when ckan.admin_tabs option has two values in config.
        '''
        app = self._get_test_app()
        expected = """<li><a href="/ckan-admin/myext_config_two"><i class="fa fa-picture-o"></i> My Other Label</a></li><li><a href="/ckan-admin/myext_config_one"><i class="fa fa-picture-o"></i> My Label</a></li>"""
        response = app.get('/build_extra_admin_nav')
        nosetools.assert_equal(response.body, expected)
