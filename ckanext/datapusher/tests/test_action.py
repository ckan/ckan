# encoding: utf-8

import datetime

import unittest.mock as mock
import pytest
from ckan.logic import _actions

from ckan.tests import helpers, factories
from ckanext.datapusher.tests import get_api_token


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
@pytest.mark.ckan_config("ckan.datapusher.api_token", get_api_token())
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
class TestSubmit:
    def test_submit(self, monkeypatch):
        """Auto-submit when creating a resource with supported format.

        """
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

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    @pytest.mark.flaky(reruns=2)
    def test_submit_when_url_changes(self, monkeypatch):
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

    def test_does_not_submit_while_ongoing_job(self, monkeypatch):
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

    def test_resubmits_if_url_changes_in_the_meantime(self, monkeypatch):
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

    def test_resubmits_if_upload_changes_in_the_meantime(self, monkeypatch):
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

    def test_does_not_resubmit_if_a_resource_field_changes_in_the_meantime(
            self, monkeypatch
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

    def test_does_not_resubmit_if_a_dataset_field_changes_in_the_meantime(
            self, monkeypatch
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

    def test_duplicated_tasks(self, app):
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

    @pytest.mark.usefixtures("with_request_context")
    def test_task_status_changes(self, create_with_upload):
        """While updating task status, datapusher commits changes to database.

        Make sure that changes to task_status won't close session that is still
        used on higher levels of API for resource updates.

        """
        user = factories.User()
        dataset = factories.Dataset()
        context = {"user": user["name"]}
        resource = create_with_upload(
            "id,name\n1,2\n3,4", "file.csv", package_id=dataset["id"],
            context=context)

        create_with_upload(
            "id,name\n1,2\n3,4", "file.csv", package_id=dataset["id"],
            id=resource["id"], context=context, action="resource_update")
