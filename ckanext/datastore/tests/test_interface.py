import nose

import ckan.plugins as p
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

assert_equals = nose.tools.assert_equals


class TestInterfaces(object):
    @classmethod
    def setup_class(cls):
        p.load('datastore')
        p.load('sample_datastore_plugin')

    @classmethod
    def teardown_class(cls):
        p.unload('sample_datastore_plugin')
        p.unload('datastore')

    def setup(self):
        helpers.reset_db()

    def test_search_data_can_create_custom_filters(self):
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        filters = {'age_between': [25, 35]}

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'],
                                     filters=filters)

        assert result['total'] == 1, result
        assert result['records'][0]['age'] == 30, result

    def test_search_data_filters_sent_arent_modified(self):
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        filters = {'age_between': [25, 35]}

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'],
                                     filters=filters.copy())

        assert_equals(result['filters'], filters)

    def test_search_data_custom_filters_have_the_correct_operator_precedence(self):
        '''
        We're testing that the WHERE clause becomes:
            (age < 50 OR age > 60) AND age = 30
        And not:
            age < 50 OR age > 60 AND age = 30
        '''
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        filters = {
            'age_not_between': [50, 60],
            'age': 30
        }

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'],
                                     filters=filters)

        assert result['total'] == 1, result
        assert result['records'][0]['age'] == 30, result
        assert_equals(result['filters'], filters)

    def test_delete_data_can_create_custom_filters(self):
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        filters = {'age_between': [25, 35]}

        helpers.call_action('datastore_delete',
                            resource_id=resource['id'],
                            force=True,
                            filters=filters)

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'],
                                     filters=filters)

        assert_equals(result['records'], [])

    def test_delete_data_custom_filters_have_the_correct_operator_precedence(self):
        '''
        We're testing that the WHERE clause becomes:
            (age < 50 OR age > 60) AND age = 30
        And not:
            age < 50 OR age > 60 AND age = 30
        '''
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        filters = {
            'age_not_between': [50, 60],
            'age': 30
        }

        helpers.call_action('datastore_delete',
                            resource_id=resource['id'],
                            force=True,
                            filters=filters)

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'],
                                     filters=filters)

        assert_equals(result['records'], [])

    def _create_datastore_resource(self, records):
        dataset = factories.Dataset()
        resource = factories.Resource(package=dataset)

        data = {
            'resource_id': resource['id'],
            'force': True,
            'records': records
        }

        helpers.call_action('datastore_create', **data)

        return resource
