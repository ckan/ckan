# encoding: utf-8

import datetime

import mock
import pytest
from ckan.logic import _actions

from ckan.tests import helpers, factories


def _pending_task(resource_id):
    return {
        "entity_id": resource_id,
        "entity_type": "resource",
        "task_type": "datapusher",
        "last_updated": str(datetime.datetime.utcnow()),
        "state": "pending",
        "key": "datapusher",
        "value": "{}",
        "error": "{}",
    }


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_submit(monkeypatch):
    dataset = factories.Dataset()
    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)
    func.assert_not_called()

    helpers.call_action(
        "resource_create",
        {},
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
    )

    func.assert_called()


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_submit_when_url_changes(monkeypatch):
    dataset = factories.Dataset()
    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)

    resource = helpers.call_action(
        "resource_create",
        {},
        package_id=dataset["id"],
        url="http://example.com/file.pdf",
    )

    func.assert_not_called()

    helpers.call_action(
        "resource_update",
        {},
        id=resource["id"],
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
    )

    func.assert_called()


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_does_not_submit_while_ongoing_job(monkeypatch):
    dataset = factories.Dataset()
    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)

    resource = helpers.call_action(
        "resource_create",
        {},
        package_id=dataset["id"],
        url="http://example.com/file.CSV",
        format="CSV",
    )

    func.assert_called()
    func.reset_mock()
    # Create a task with a state pending to mimic an ongoing job
    # on the DataPusher
    helpers.call_action(
        "task_status_update", {}, **_pending_task(resource["id"])
    )

    # Update the resource
    helpers.call_action(
        "resource_update",
        {},
        id=resource["id"],
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
        description="Test",
    )
    # Not called
    func.assert_not_called()


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_resubmits_if_url_changes_in_the_meantime(monkeypatch):
    dataset = factories.Dataset()
    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)

    resource = helpers.call_action(
        "resource_create",
        {},
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
    )

    func.assert_called()
    func.reset_mock()
    # Create a task with a state pending to mimic an ongoing job
    # on the DataPusher
    task = helpers.call_action(
        "task_status_update", {}, **_pending_task(resource["id"])
    )

    # Update the resource, set a new URL
    helpers.call_action(
        "resource_update",
        {},
        id=resource["id"],
        package_id=dataset["id"],
        url="http://example.com/another.file.csv",
        format="CSV",
    )
    # Not called
    func.assert_not_called()

    # Call datapusher_hook with state complete, to mock the DataPusher
    # finishing the job and telling CKAN
    data_dict = {
        "metadata": {
            "resource_id": resource["id"],
            "original_url": "http://example.com/file.csv",
            "task_created": task["last_updated"],
        },
        "status": "complete",
    }

    helpers.call_action("datapusher_hook", {}, **data_dict)

    # datapusher_submit was called again
    func.assert_called()


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_resubmits_if_upload_changes_in_the_meantime(monkeypatch):
    dataset = factories.Dataset()
    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)

    resource = helpers.call_action(
        "resource_create",
        {},
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
    )

    func.assert_called()
    func.reset_mock()
    # Create a task with a state pending to mimic an ongoing job
    # on the DataPusher
    task = helpers.call_action(
        "task_status_update", {}, **_pending_task(resource["id"])
    )

    # Update the resource, set a new last_modified (changes on file upload)
    helpers.call_action(
        "resource_update",
        {},
        id=resource["id"],
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
        last_modified=datetime.datetime.utcnow().isoformat(),
    )
    # Not called
    func.assert_not_called()

    # Call datapusher_hook with state complete, to mock the DataPusher
    # finishing the job and telling CKAN
    data_dict = {
        "metadata": {
            "resource_id": resource["id"],
            "original_url": "http://example.com/file.csv",
            "task_created": task["last_updated"],
        },
        "status": "complete",
    }
    helpers.call_action("datapusher_hook", {}, **data_dict)

    # datapusher_submit was called again
    func.assert_called()


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_does_not_resubmit_if_a_resource_field_changes_in_the_meantime(
    monkeypatch
):
    dataset = factories.Dataset()
    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)

    resource = helpers.call_action(
        "resource_create",
        {},
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
    )

    func.assert_called()
    func.reset_mock()

    # Create a task with a state pending to mimic an ongoing job
    # on the DataPusher
    task = helpers.call_action(
        "task_status_update", {}, **_pending_task(resource["id"])
    )

    # Update the resource, set a new description
    helpers.call_action(
        "resource_update",
        {},
        id=resource["id"],
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
        description="Test",
    )
    # Not called
    func.assert_not_called()

    # Call datapusher_hook with state complete, to mock the DataPusher
    # finishing the job and telling CKAN
    data_dict = {
        "metadata": {
            "resource_id": resource["id"],
            "original_url": "http://example.com/file.csv",
            "task_created": task["last_updated"],
        },
        "status": "complete",
    }
    helpers.call_action("datapusher_hook", {}, **data_dict)

    # Not called
    func.assert_not_called()


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_does_not_resubmit_if_a_dataset_field_changes_in_the_meantime(
        monkeypatch
):
    dataset = factories.Dataset()
    func = mock.Mock()
    monkeypatch.setitem(_actions, 'datapusher_submit', func)

    resource = helpers.call_action(
        "resource_create",
        {},
        package_id=dataset["id"],
        url="http://example.com/file.csv",
        format="CSV",
    )

    func.assert_called()
    func.reset_mock()
    # Create a task with a state pending to mimic an ongoing job
    # on the DataPusher
    task = helpers.call_action(
        "task_status_update", {}, **_pending_task(resource["id"])
    )

    # Update the parent dataset
    helpers.call_action(
        "package_update",
        {},
        id=dataset["id"],
        notes="Test notes",
        resources=[resource],
    )
    # Not called
    func.assert_not_called()
    # Call datapusher_hook with state complete, to mock the DataPusher
    # finishing the job and telling CKAN
    data_dict = {
        "metadata": {
            "resource_id": resource["id"],
            "original_url": "http://example.com/file.csv",
            "task_created": task["last_updated"],
        },
        "status": "complete",
    }
    helpers.call_action("datapusher_hook", {}, **data_dict)

    # Not called
    func.assert_not_called()


@pytest.mark.ckan_config("ckan.plugins", "datapusher datastore")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
def test_duplicated_tasks(app):
    def submit(res, user):
        return helpers.call_action(
            "datapusher_submit",
            context=dict(user=user["name"]),
            resource_id=res["id"],
        )

    user = factories.User()
    res = factories.Resource(user=user)

    with app.flask_app.test_request_context():
        with mock.patch("requests.post") as r_mock:
            r_mock().json = mock.Mock(
                side_effect=lambda: dict.fromkeys(["job_id", "job_key"])
            )
            r_mock.reset_mock()
            submit(res, user)
            submit(res, user)

            assert r_mock.call_count == 1
