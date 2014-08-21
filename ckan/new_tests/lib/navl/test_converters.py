import nose

from ckan import model
import ckan.plugins as p
import ckan.lib.plugins as lib_plugins
from ckan.lib.navl.dictization_functions import validate


eq_ = nose.tools.eq_


class TestConvertToExtras(object):

    @classmethod
    def setup_class(cls):
        p.load('example_idatasetform')

    @classmethod
    def teardown_class(cls):
        p.unload('example_idatasetform')

    def test_convert_to_extras_field_gets_stored_as_extra(self):

        data_dict = {
            'name': 'test-dataset',
            'custom_text': 'Hi',
        }

        context = {
            'model': model,
            'session': model.Session,
        }

        package_plugin = lib_plugins.lookup_package_plugin('dataset')
        schema = package_plugin.create_package_schema()

        data, errors = validate(data_dict, schema, context)

        assert 'extras' in data
        eq_(len(data['extras']), 1)
        eq_(data['extras'][0]['key'], 'custom_text')
        eq_(data['extras'][0]['value'], 'Hi')

    def test_convert_to_extras_field_can_be_combined_with_a_proper_extra(self):

        data_dict = {
            'name': 'test-dataset',
            'custom_text': 'Hi',
            'extras': [
                {'key': 'proper_extra', 'value': 'Bye'},

            ]
        }

        context = {
            'model': model,
            'session': model.Session,
        }

        package_plugin = lib_plugins.lookup_package_plugin('dataset')
        schema = package_plugin.create_package_schema()

        data, errors = validate(data_dict, schema, context)

        assert 'extras' in data
        eq_(len(data['extras']), 2)
        eq_(sorted([e['key'] for e in data['extras']]),
            ['custom_text', 'proper_extra'])
        eq_(sorted([e['value'] for e in data['extras']]),
            ['Bye', 'Hi'])

    def test_convert_to_extras_field_can_be_combined_with_more_extras(self):

        data_dict = {
            'name': 'test-dataset',
            'custom_text': 'Hi',
            'extras': [
                {'key': 'proper_extra', 'value': 'Bye'},
                {'key': 'proper_extra2', 'value': 'Bye2'},
            ]
        }

        context = {
            'model': model,
            'session': model.Session,
        }

        package_plugin = lib_plugins.lookup_package_plugin('dataset')
        schema = package_plugin.create_package_schema()

        data, errors = validate(data_dict, schema, context)

        assert 'extras' in data
        eq_(len(data['extras']), 3)
        eq_(sorted([e['key'] for e in data['extras']]),
            ['custom_text', 'proper_extra', 'proper_extra2'])
        eq_(sorted([e['value'] for e in data['extras']]),
            ['Bye', 'Bye2', 'Hi'])
