# encoding: utf-8

import datetime

import pytest

from ckan.tests import helpers, factories


@pytest.mark.ckan_config("ckan.views.default_views", "recline_grid_view")
@pytest.mark.ckan_config(
    "ckan.plugins", "datapusher datastore recline_grid_view"
)
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_datapusher_creates_default_views_on_complete():

    dataset = factories.Dataset()

    resource = factories.Resource(package_id=dataset["id"])

    # Push data directly to the DataStore for the resource to be marked as
    # `datastore_active=True`, so the grid view can be created
    data = {
        "resource_id": resource["id"],
        "fields": [{"id": "a", "type": "text"}, {"id": "b", "type": "text"}],
        "records": [{"a": "1", "b": "2"}],
        "force": True,
    }
    helpers.call_action("datastore_create", **data)

    # Create a task for `datapusher_hook` to update
    task_dict = {
        "entity_id": resource["id"],
        "entity_type": "resource",
        "task_type": "datapusher",
        "key": "datapusher",
        "value": '{"job_id": "my_id", "job_key":"my_key"}',
        "last_updated": str(datetime.datetime.now()),
        "state": "pending",
    }
    helpers.call_action("task_status_update", context={}, **task_dict)

    # Call datapusher_hook with a status of complete to trigger the
    # default views creation
    params = {
        "status": "complete",
        "metadata": {"resource_id": resource["id"]},
    }

    helpers.call_action("datapusher_hook", context={}, **params)

    views = helpers.call_action("resource_view_list", id=resource["id"])

    assert len(views) == 1
    assert views[0]["view_type"] == "recline_grid_view"


@pytest.mark.ckan_config("ckan.views.default_views", "recline_grid_view")
@pytest.mark.ckan_config(
    "ckan.plugins", "datapusher datastore recline_grid_view"
)
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_datapusher_does_not_create_default_views_on_pending():

    dataset = factories.Dataset()

    resource = factories.Resource(package_id=dataset["id"])

    # Push data directly to the DataStore for the resource to be marked as
    # `datastore_active=True`, so the grid view can be created
    data = {
        "resource_id": resource["id"],
        "fields": [{"id": "a", "type": "text"}, {"id": "b", "type": "text"}],
        "records": [{"a": "1", "b": "2"}],
        "force": True,
    }
    helpers.call_action("datastore_create", **data)

    # Create a task for `datapusher_hook` to update
    task_dict = {
        "entity_id": resource["id"],
        "entity_type": "resource",
        "task_type": "datapusher",
        "key": "datapusher",
        "value": '{"job_id": "my_id", "job_key":"my_key"}',
        "last_updated": str(datetime.datetime.now()),
        "state": "pending",
    }
    helpers.call_action("task_status_update", context={}, **task_dict)

    # Call datapusher_hook with a status of complete to trigger the
    # default views creation
    params = {"status": "pending", "metadata": {"resource_id": resource["id"]}}

    helpers.call_action("datapusher_hook", context={}, **params)

    views = helpers.call_action("resource_view_list", id=resource["id"])

    assert len(views) == 0
