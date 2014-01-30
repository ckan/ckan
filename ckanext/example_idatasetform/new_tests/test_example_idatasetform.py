import nose.tools as nt

import ckan.model as model
import ckan.plugins as plugins
import ckan.new_tests.helpers as helpers
import ckanext.example_idatasetform as idf


class ExampleIDatasetFormPluginBase(object):
    '''Version 1, 2 and 3 of the plugin are basically the same, so this class
    provides the tests that all three versions of the plugins will run'''
    def teardown(self):
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        helpers.reset_db()

    def test_package_create(self):
        result = helpers.call_action('package_create', name='test_package',
                                     custom_text='this is my custom text')
        nt.assert_equals('this is my custom text', result['custom_text'])

    def test_package_update(self):
        helpers.call_action('package_create', name='test_package',
                            custom_text='this is my custom text')
        result = helpers.call_action('package_update', name='test_package',
                                     custom_text='this is my updated text')
        nt.assert_equals('this is my updated text', result['custom_text'])

    def test_package_show(self):
        helpers.call_action('package_create', name='test_package',
                            custom_text='this is my custom text')
        result = helpers.call_action('package_show', name_or_id='test_package')
        nt.assert_equals('this is my custom text', result['custom_text'])


class TestVersion1(ExampleIDatasetFormPluginBase):
    @classmethod
    def setup_class(cls):
        plugins.load('example_idatasetform_v1')

    @classmethod
    def teardown_class(cls):
        super(TestVersion1, cls).teardown_class()
        plugins.unload('example_idatasetform_v1')


class TestVersion2(ExampleIDatasetFormPluginBase):
    @classmethod
    def setup_class(cls):
        plugins.load('example_idatasetform_v2')

    @classmethod
    def teardown_class(cls):
        super(TestVersion2, cls).teardown_class()
        plugins.unload('example_idatasetform_v2')


class TestVersion3(ExampleIDatasetFormPluginBase):
    @classmethod
    def setup_class(cls):
        plugins.load('example_idatasetform_v3')

    @classmethod
    def teardown_class(cls):
        super(TestVersion3, cls).teardown_class()
        plugins.unload('example_idatasetform_v3')


class TestIDatasetFormPluginVersion4(object):
    @classmethod
    def setup_class(cls):
        plugins.load('example_idatasetform_v4')

    def teardown(self):
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_idatasetform_v4')
        helpers.reset_db()

    def test_package_create(self):
        idf.plugin_v4.create_country_codes()
        result = helpers.call_action('package_create', name='test_package',
                                     custom_text='this is my custom text',
                                     country_code='uk')
        nt.assert_equals('this is my custom text', result['custom_text'])
        nt.assert_equals([u'uk'], result['country_code'])

    def test_package_create_wrong_country_code(self):
        idf.plugin_v4.create_country_codes()
        nt.assert_raises(plugins.toolkit.ValidationError,
                         helpers.call_action,
                         'package_create',
                         name='test_package',
                         custom_text='this is my custom text',
                         country_code='notcode')

    def test_package_update(self):
        idf.plugin_v4.create_country_codes()
        helpers.call_action('package_create', name='test_package',
                            custom_text='this is my custom text',
                            country_code='uk')
        result = helpers.call_action('package_update', name='test_package',
                                     custom_text='this is my updated text',
                                     country_code='ie')
        nt.assert_equals('this is my updated text', result['custom_text'])
        nt.assert_equals([u'ie'], result['country_code'])


class TestIDatasetFormPlugin(object):
    @classmethod
    def setup_class(cls):
        plugins.load('example_idatasetform')

    def teardown(self):
        model.repo.rebuild_db()

    @classmethod
    def teardown_class(cls):
        plugins.unload('example_idatasetform')
        helpers.reset_db()

    def test_package_create(self):
        idf.plugin.create_country_codes()
        result = helpers.call_action(
            'package_create', name='test_package',
            custom_text='this is my custom text', country_code='uk',
            resources=[{
                'url': 'http://test.com/',
                'custom_resource_text': 'my custom resource',
            }])
        nt.assert_equals('my custom resource',
                         result['resources'][0]['custom_resource_text'])

    def test_package_update(self):
        idf.plugin.create_country_codes()
        helpers.call_action(
            'package_create', name='test_package',
            custom_text='this is my custom text', country_code='uk',
            resources=[{
                'url': 'http://test.com/',
                'custom_resource_text': 'my custom resource',
            }])
        result = helpers.call_action(
            'package_update',
            name='test_package',
            custom_text='this is my updated text',
            country_code='ie',
            resources=[{
                'url': 'http://test.com/',
                'custom_resource_text': 'updated custom resource',
            }]
        )
        nt.assert_equals('this is my updated text', result['custom_text'])
        nt.assert_equals([u'ie'], result['country_code'])
        nt.assert_equals('updated custom resource',
                         result['resources'][0]['custom_resource_text'])

    def test_package_show(self):
        idf.plugin.create_country_codes()
        helpers.call_action(
            'package_create', name='test_package',
            custom_text='this is my custom text', country_code='uk',
            resources=[{
                'url': 'http://test.com/',
                'custom_resource_text': 'my custom resource',
            }]
        )
        result = helpers.call_action('package_show', name_or_id='test_package')
        nt.assert_equals('my custom resource',
                         result['resources'][0]['custom_resource_text'])
        nt.assert_equals('my custom resource',
                         result['resources'][0]['custom_resource_text'])
