# -*- coding: utf-8 -*-
import nose

import ckan.plugins as p
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


@p.toolkit.chained_action
def datastore_delete(up_func, context, data_dict):
    res = helpers.call_action(u"datastore_search",
                              resource_id=data_dict[u'resource_id'],
                              filters=data_dict[u'filters'],
                              limit=10,)
    result = up_func(context, data_dict)
    result['deleted_count'] = res.get(u'total', 0)
    return result


class ExampleDataStoreDeletedWithCountPlugin(p.SingletonPlugin):
    p.implements(p.IActions)

    def get_actions(self):
        return ({u'datastore_delete': datastore_delete})


class TestChainedAction(object):
    @classmethod
    def setup_class(cls):
        p.load(u'datastore')
        p.load(u'example_datastore_deleted_with_count_plugin')

    @classmethod
    def teardown_class(cls):
        p.unload(u'example_datastore_deleted_with_count_plugin')
        p.unload(u'datastore')

    def setup(self):
        helpers.reset_db()

    def test_datastore_delete_filters(self):
        records = [
            {u'age': 20}, {u'age': 30}, {u'age': 40}
        ]
        resource = self._create_datastore_resource(records)
        filters = {u'age': 30}

        response = helpers.call_action(u'datastore_delete',
                                       resource_id=resource[u'id'],
                                       force=True,
                                       filters=filters)

        result = helpers.call_action(u'datastore_search',
                                     resource_id=resource[u'id'])

        new_records_ages = [r[u'age'] for r in result[u'records']]
        new_records_ages.sort()
        assert_equals(new_records_ages, [20, 40])
        assert_equals(response['deleted_count'], 1)

    def _create_datastore_resource(self, records):
        dataset = factories.Dataset()
        resource = factories.Resource(package=dataset)

        data = {
            u'resource_id': resource[u'id'],
            u'force': True,
            u'records': records
        }

        helpers.call_action(u'datastore_create', **data)

        return resource
