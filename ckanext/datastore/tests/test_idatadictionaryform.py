# encoding: utf-8

import pytest
import ckan.tests.helpers as helpers
import ckan.tests.factories as factories
from ckan.plugins.toolkit import ValidationError
from ckanext.datastore.backend import DatastoreBackend


@pytest.mark.ckan_config(
    "ckan.plugins", "datastore example_idatadictionaryform")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
def test_accept_custom_fields():
    fields = [
        {
            "id": "one", "type": "text",
            "an_int": 42, "json_obj": {"a": "b"}, "secret": 7,
        },
        {
            "id": "two", "type": "text",
            "an_int": -4, "json_obj": {"q": []},
        },
    ]
    resource = _create_datastore_resource(fields)

    result = helpers.call_action(
        "datastore_info", id=resource["id"]
    )

    f1 = {k: v for k, v in result['fields'][0].items() if k != 'schema'}
    f2 = {k: v for k, v in result['fields'][1].items() if k != 'schema'}
    assert f1 == {
        "id": "one", "type": "text", "an_int": 42, "json_obj": {"a": "b"}}
    assert f2 == {
        "id": "two", "type": "text", "an_int": -4, "json_obj": {"q": []}}

    backend = DatastoreBackend.get_active_backend()

    plugin_data = backend.resource_plugin_data(resource["id"])

    assert plugin_data['one']['example_idatadictionaryform_secret'] == {
        'secret': 7}
    assert 'example_idatadictionaryform_secret' not in plugin_data['two']

    # excluding/passing empty values for all fields for a plugin data
    # key will leave existing values unchanged due to ignore_empty
    fields = [
        {
            "id": "one", "type": "text",
            "an_int": None, "json_obj": "",
        },
        {
            "id": "two", "type": "text",
            "json_obj": None,
        },
    ]
    helpers.call_action(
        "datastore_create",
        resource_id=resource['id'],
        force=True,
        fields=fields,
    )

    result = helpers.call_action(
        "datastore_info", id=resource["id"]
    )

    f1 = {k: v for k, v in result['fields'][0].items() if k != 'schema'}
    f2 = {k: v for k, v in result['fields'][1].items() if k != 'schema'}
    assert f1 == {
        "id": "one", "type": "text", "an_int": 42, "json_obj": {"a": "b"}}
    assert f2 == {
        "id": "two", "type": "text", "an_int": -4, "json_obj": {"q": []}}

    # excluding/passing empty values for some fields will clear all fields
    # in the same plugin data key
    fields = [
        {
            "id": "one", "type": "text",
            "an_int": 99, "json_obj": "",
        },
        {
            "id": "two", "type": "text",
            "json_obj": {"zz": []},
        },
    ]
    helpers.call_action(
        "datastore_create",
        resource_id=resource['id'],
        force=True,
        fields=fields,
    )

    result = helpers.call_action(
        "datastore_info", id=resource["id"]
    )

    f1 = {k: v for k, v in result['fields'][0].items() if k != 'schema'}
    f2 = {k: v for k, v in result['fields'][1].items() if k != 'schema'}
    assert f1 == {
        "id": "one", "type": "text", "an_int": 99}
    assert f2 == {
        "id": "two", "type": "text", "json_obj": {"zz": []}}

    # separate plugin data keys are unaffected
    plugin_data = backend.resource_plugin_data(resource["id"])

    assert plugin_data['one']['example_idatadictionaryform_secret'] == {
        'secret': 7}
    assert 'example_idatadictionaryform_secret' not in plugin_data['two']


@pytest.mark.ckan_config(
    "ckan.plugins", "datastore example_idatadictionaryform")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
def test_validate_custom_fields():
    fields = [
        {
            "id": "one", "type": "text",
            "an_int": 4.2, "json_obj": "hola",
        },
        {
            "id": "two", "type": "text",
            "an_int": "hello", "json_obj": None,
        },
        {
            "id": "three", "type": "text",
            "an_int": "", "json_obj": "{}",
        },
        {
            "id": "four", "type": "text",
            "an_int": "19", "json_obj": "{a}",
        },
    ]
    with pytest.raises(ValidationError) as err:
        _create_datastore_resource(fields)
    assert err.value.error_dict == {'fields': [
        {'an_int': ['Invalid integer'], 'json_obj': ['Not a JSON object']},
        {'an_int': ['Invalid integer']},
        {},
        {'json_obj': ['Not a JSON object']},
    ]}


@pytest.mark.ckan_config(
    "ckan.plugins", "datastore example_idatadictionaryform")
@pytest.mark.usefixtures("clean_datastore", "with_plugins")
def test_validators_access_current_values():
    fields = [
        {
            "id": "one", "type": "text",
            "only_up": 42, "sticky": "never give you up",
        },
        {
            "id": "two", "type": "text",
            "only_up": -4, "sticky": "let you down",
        },
    ]
    resource = _create_datastore_resource(fields)

    result = helpers.call_action(
        "datastore_info", id=resource["id"]
    )

    f1 = {k: v for k, v in result['fields'][0].items() if k != 'schema'}
    f2 = {k: v for k, v in result['fields'][1].items() if k != 'schema'}
    assert f1 == {
        "id": "one", "type": "text", "only_up": 42,
        "sticky": "never give you up"}
    assert f2 == {
        "id": "two", "type": "text", "only_up": -4,
        "sticky": "let you down"}

    # passing nothing/empty string/null will maintain sticky values
    # even when other values are set in the same plugin data key
    fields = [
        {
            "id": "one", "type": "text",
            "an_int": 19, "only_up": "", "sticky": None,
        },
        {
            "id": "two", "type": "text",
            "an_int": 20, "sticky": "",
        },
    ]
    helpers.call_action(
        "datastore_create",
        resource_id=resource['id'],
        force=True,
        fields=fields,
    )

    result = helpers.call_action(
        "datastore_info", id=resource["id"]
    )

    f1 = {k: v for k, v in result['fields'][0].items() if k != 'schema'}
    f2 = {k: v for k, v in result['fields'][1].items() if k != 'schema'}
    assert f1 == {
        "id": "one", "type": "text", "only_up": 42, "an_int": 19,
        "sticky": "never give you up"}
    assert f2 == {
        "id": "two", "type": "text", "only_up": -4, "an_int": 20,
        "sticky": "let you down"}

    fields = [
        {
            "id": "one", "type": "text",
            "only_up": "17", "sticky": 20,
        },
        {
            "id": "two", "type": "text",
            "only_up": -5,
        },
    ]
    with pytest.raises(ValidationError) as err:
        helpers.call_action(
            "datastore_create",
            resource_id=resource['id'],
            force=True,
            fields=fields,
        )
    assert err.value.error_dict == {'fields': [
        {'only_up': ['Value must be larger than 42'],
         'sticky': ['Must be a Unicode string value']},
        {'only_up': ['Value must be larger than -4']},
    ]}


def _create_datastore_resource(fields):
    resource = factories.Resource()

    data = {"resource_id": resource["id"], "force": True, "fields": fields}

    helpers.call_action("datastore_create", **data)

    return resource
