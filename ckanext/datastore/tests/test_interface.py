import nose

import ckan.plugins as p
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

import ckanext.datastore.interfaces as interfaces

assert_equals = nose.tools.assert_equals


class SampleDataStorePlugin(p.SingletonPlugin):
    p.implements(interfaces.IDataStore)

    def where(self, filters):
        clauses = []
        if 'age_between' in filters:
            age_between = filters['age_between']
            del filters['age_between']

            clause = ('"age" >= %s AND "age" <= %s',
                      age_between[0], age_between[1])
            clauses.append(clause)
        if 'age_not_between' in filters:
            age_not_between = filters['age_not_between']
            del filters['age_not_between']

            clause = ('"age" < %s OR "age" > %s',
                      age_not_between[0], age_not_between[1])
            clauses.append(clause)
        return filters, clauses


class TestInterfaces(object):
    @classmethod
    def setup_class(cls):
        cls.plugin = SampleDataStorePlugin()
        p.load('datastore')

    @classmethod
    def teardown_class(cls):
        p.unload('datastore')

    def setup(self):
        self.plugin.activate()
        helpers.reset_db()

    def teardown(self):
        self.plugin.deactivate()

    def test_can_create_custom_filters(self):
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
        assert_equals(result['filters'], filters)

    def test_custom_filters_have_the_correct_operator_precedence(self):
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
