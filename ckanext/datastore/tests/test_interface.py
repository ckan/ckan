# encoding: utf-8

import nose

import ckan.plugins as p
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

from ckanext.datastore.tests.helpers import DatastoreFunctionalTestBase

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


class TestInterfaces(DatastoreFunctionalTestBase):
    _load_plugins = (
        u'datastore',
        u'sample_datastore_plugin')

    def test_datastore_search_can_create_custom_filters(self):
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

    def test_datastore_search_filters_sent_arent_modified(self):
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        filters = {'age_between': [25, 35]}

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'],
                                     filters=filters.copy())

        assert_equals(result['filters'], filters)

    def test_datastore_search_custom_filters_have_the_correct_operator_precedence(self):
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

    def test_datastore_search_insecure_filter(self):
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        sql_inject = '1=1); DELETE FROM "%s"; COMMIT; SELECT * FROM "%s";--' \
                     % (resource['id'], resource['id'])
        filters = {
            'insecure_filter': sql_inject
        }

        assert_raises(p.toolkit.ValidationError,
                      helpers.call_action, 'datastore_search',
                      resource_id=resource['id'], filters=filters)

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'])

        assert result['total'] == 3, result

    def test_datastore_delete_can_create_custom_filters(self):
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
                                     resource_id=resource['id'])

        new_records_ages = [r['age'] for r in result['records']]
        new_records_ages.sort()
        assert_equals(new_records_ages, [20, 40])

    def test_datastore_delete_custom_filters_have_the_correct_operator_precedence(self):
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
                                     resource_id=resource['id'])

        new_records_ages = [r['age'] for r in result['records']]
        new_records_ages.sort()
        assert_equals(new_records_ages, [20, 40])

    def test_datastore_delete_insecure_filter(self):
        records = [
            {'age': 20}, {'age': 30}, {'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        sql_inject = '1=1); DELETE FROM "%s"; SELECT * FROM "%s";--' \
                     % (resource['id'], resource['id'])
        filters = {
            'age': 20,
            'insecure_filter': sql_inject
        }

        assert_raises(p.toolkit.ValidationError,
                      helpers.call_action, 'datastore_delete',
                      resource_id=resource['id'], force=True,
                      filters=filters)

        result = helpers.call_action('datastore_search',
                                     resource_id=resource['id'])

        assert result['total'] == 3, result

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
