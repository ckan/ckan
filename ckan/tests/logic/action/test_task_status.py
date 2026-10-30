"""Tests for actions and authorization in ckan/logic/action/task_status.py."""

import pytest

from ckan import logic, model
from ckan.tests import factories, helpers


@pytest.mark.usefixtures("non_clean_db")
def test_task_status_update():
    pkg = factories.Dataset()

    task_status = {
        "entity_id": pkg["id"],
        "entity_type": "package",
        "task_type": "test_task",
        "key": "test_key",
        "value": "test_value",
        "state": "test_state",
        "error": "test_error",
    }
    task_status_updated = helpers.call_action("task_status_update", **task_status)

    task_status_id = task_status_updated.pop("id")
    task_status_updated.pop("last_updated")
    assert task_status_updated == task_status

    task_status_updated["id"] = task_status_id
    task_status_updated["value"] = "test_value_2"

    task_status_updated_2 = helpers.call_action(
        "task_status_update", **task_status_updated
    )
    task_status_updated_2.pop("last_updated")
    assert task_status_updated_2 == task_status_updated


@pytest.mark.usefixtures("non_clean_db")
def test_task_status_update_many():
    pkg = factories.Dataset()
    task_statuses = {
        "data": [
            {
                "entity_id": pkg["id"],
                "entity_type": "package",
                "task_type": "test_task",
                "key": "test_task_1",
                "value": "test_value_1",
                "state": "test_state",
                "error": "test_error",
            },
            {
                "entity_id": pkg["id"],
                "entity_type": "package",
                "task_type": "test_task",
                "key": "test_task_2",
                "value": "test_value_2",
                "state": "test_state",
                "error": "test_error",
            },
        ]
    }
    task_statuses_updated = helpers.call_action(
        "task_status_update_many", **task_statuses
    )["results"]

    for i in range(len(task_statuses["data"])):
        task_status = task_statuses["data"][i]
        task_status_updated = task_statuses_updated[i]
        task_status_updated.pop("id")
        task_status_updated.pop("last_updated")
        assert task_status == task_status_updated, (
            task_status_updated,
            task_status,
            i,
        )


@pytest.mark.usefixtures("non_clean_db")
def test_task_status_normal_user_not_authorized():
    user = factories.User()
    context = {"model": model, "user": user["name"]}
    with pytest.raises(logic.NotAuthorized):
        helpers.call_auth("task_status_update", context)


@pytest.mark.usefixtures("non_clean_db")
def test_task_status_validation():
    with pytest.raises(logic.ValidationError):
        helpers.call_action("task_status_update")


@pytest.mark.usefixtures("non_clean_db")
def test_task_status_show():
    pkg = factories.Dataset()
    task_status = {
        "entity_id": pkg["id"],
        "entity_type": "package",
        "task_type": "test_task",
        "key": "test_task_status_show",
        "value": "test_value",
        "state": "test_state",
        "error": "test_error",
    }
    task_status_updated = helpers.call_action("task_status_update", **task_status)
    task_status_show = helpers.call_action(
        "task_status_show", id=task_status_updated["id"]
    )

    task_status_show.pop("last_updated")
    task_status_updated.pop("last_updated")
    assert task_status_show == task_status_updated, (
        task_status_show,
        task_status_updated,
    )
    task_status_show = helpers.call_action(
        "task_status_show",
        entity_id=task_status["entity_id"],
        task_type=task_status["task_type"],
        key=task_status["key"],
    )

    task_status_show.pop("last_updated")
    assert task_status_show == task_status_updated, (
        task_status_show,
        task_status_updated,
    )


@pytest.mark.usefixtures("non_clean_db")
def test_task_status_delete():
    pkg = factories.Dataset()
    task_status = {
        "entity_id": pkg["id"],
        "entity_type": "package",
        "task_type": "test_task",
        "key": "test_task_status_delete",
        "value": "test_value",
        "state": "test_state",
        "error": "test_error",
    }
    task_status_updated = helpers.call_action("task_status_update", **task_status)
    helpers.call_action("task_status_delete", id=task_status_updated["id"])
