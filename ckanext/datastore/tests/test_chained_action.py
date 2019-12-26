# -*- coding: utf-8 -*-

import pytest

import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.logic.action.get import package_list as core_package_list


package_list_message = u"The content of this message is largely irrelevant"


class TestActionException(Exception):
    pass


@p.toolkit.chained_action
def datastore_delete(up_func, context, data_dict):
    res = helpers.call_action(
        u"datastore_search",
        resource_id=data_dict[u"resource_id"],
        filters=data_dict[u"filters"],
        limit=10,
    )
    result = up_func(context, data_dict)
    result["deleted_count"] = res.get(u"total", 0)
    return result


@p.toolkit.chained_action
def package_list(next_func, context, data_dict):
    # check it's received the core function as the first arg
    assert next_func == core_package_list
    raise TestActionException(package_list_message)


class ExampleDataStoreDeletedWithCountPlugin(p.SingletonPlugin):
    p.implements(p.IActions)

    def get_actions(self):
        return {
            u"datastore_delete": datastore_delete,
            u"package_list": package_list,
        }


@pytest.mark.usefixtures(u"with_request_context")
class TestChainedAction(object):
    @pytest.mark.ckan_config(
        u"ckan.plugins",
        u"datastore example_datastore_deleted_with_count_plugin",
    )
    @pytest.mark.usefixtures(u"with_plugins", u"clean_db")
    def test_datastore_delete_filters(self):
        records = [{u"age": 20}, {u"age": 30}, {u"age": 40}]
        resource = self._create_datastore_resource(records)
        filters = {u"age": 30}

        response = helpers.call_action(
            u"datastore_delete",
            resource_id=resource[u"id"],
            force=True,
            filters=filters,
        )

        result = helpers.call_action(
            u"datastore_search", resource_id=resource[u"id"]
        )

        new_records_ages = [r[u"age"] for r in result[u"records"]]
        new_records_ages.sort()
        assert new_records_ages == [20, 40]
        assert response["deleted_count"] == 1

    def _create_datastore_resource(self, records):
        dataset = factories.Dataset()
        resource = factories.Resource(package=dataset)

        data = {
            u"resource_id": resource[u"id"],
            u"force": True,
            u"records": records,
        }

        helpers.call_action(u"datastore_create", **data)

        return resource

    @pytest.mark.ckan_config(
        u"ckan.plugins",
        u"datastore example_datastore_deleted_with_count_plugin",
    )
    @pytest.mark.usefixtures(u"with_plugins", u"clean_db")
    def test_chain_core_action(self):
        with pytest.raises(TestActionException) as raise_context:
            helpers.call_action(u"package_list", {})
        assert raise_context.value.args == (package_list_message, )
