from __future__ import annotations

import sqlalchemy

from ckan import model
from ckan.common import _
from ckan.lib.dictization import model_dictize, model_save
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.logic import (
    NotFound,
    ValidationError,
    side_effect_free,
)
from ckan.logic import check_access as _check_access
from ckan.logic import get_action as _get_action
from ckan.logic import get_or_bust as _get_or_bust
from ckan.logic import schema as schema_
from ckan.types import ActionResult, Context, DataDict

_and_ = sqlalchemy.and_


@side_effect_free
def task_status_show(
    context: Context, data_dict: DataDict
) -> ActionResult.TaskStatusShow:
    """Return a task status.

    Either the ``id`` parameter *or* the ``entity_id``, ``task_type`` *and*
    ``key`` parameters must be given.

    :param id: the id of the task status (optional)
    :type id: string
    :param entity_id: the entity_id of the task status (optional)
    :type entity_id: string
    :param task_type: the task_type of the task status (optional)
    :type task_type: string
    :param key: the key of the task status (optional)
    :type key: string

    :rtype: dictionary
    """
    id = data_dict.get("id")

    if id:
        task_status = model.TaskStatus.get(id)
    else:
        query = model.Session.query(model.TaskStatus).filter(
            _and_(
                model.TaskStatus.entity_id == _get_or_bust(data_dict, "entity_id"),
                model.TaskStatus.task_type == _get_or_bust(data_dict, "task_type"),
                model.TaskStatus.key == _get_or_bust(data_dict, "key"),
            )
        )
        task_status = query.first()

    if task_status is None:
        raise NotFound
    context["task_status"] = task_status
    _check_access("task_status_show", context, data_dict)

    task_status_dict = model_dictize.task_status_dictize(task_status, context)
    return task_status_dict


def task_status_update(
    context: Context, data_dict: DataDict
) -> ActionResult.TaskStatusUpdate:
    """Update a task status.

    :param id: the id of the task status to update
    :type id: string
    :param entity_id:
    :type entity_id: string
    :param entity_type:
    :type entity_type: string
    :param task_type:
    :type task_type: string
    :param key:
    :type key: string
    :param value: (optional)
    :type value:
    :param state: (optional)
    :type state:
    :param last_updated: (optional)
    :type last_updated:
    :param error: (optional)
    :type error:

    :returns: the updated task status
    :rtype: dictionary

    """
    session = context["session"]

    id = data_dict.get("id")
    schema = context.get("schema") or schema_.default_task_status_schema()

    if id:
        task_status = model.TaskStatus.get(id)
        if task_status is None:
            raise NotFound(_("TaskStatus was not found."))
        context["task_status"] = task_status

    _check_access("task_status_update", context, data_dict)

    data, errors = _validate(data_dict, schema, context)
    if errors:
        session.rollback()
        raise ValidationError(errors)

    task_status = model_save.task_status_dict_save(data, context)

    session.commit()
    session.close()
    return model_dictize.task_status_dictize(task_status, context)


def task_status_update_many(
    context: Context, data_dict: DataDict
) -> ActionResult.TaskStatusUpdateMany:
    """Update many task statuses at once.

    :param data: the task_status dictionaries to update, for the format of task
        status dictionaries see
        :py:func:`~task_status_update`
    :type data: list of dictionaries

    :returns: the updated task statuses
    :rtype: list of dictionaries

    """
    results = []
    deferred = context.get("defer_commit")
    context["defer_commit"] = True

    for data in data_dict["data"]:
        results.append(_get_action("task_status_update")(context, data))
    if not deferred:
        context.pop("defer_commit")
    if not context.get("defer_commit"):
        model.Session.commit()
    return {"results": results}


def task_status_delete(context: Context, data_dict: DataDict) -> None:
    """Delete a task status.

    You must be a sysadmin to delete task statuses.

    :param id: the id of the task status to delete
    :type id: string

    """
    id = _get_or_bust(data_dict, "id")

    entity = model.TaskStatus.get(id)

    if entity is None:
        raise NotFound

    _check_access("task_status_delete", context, data_dict)

    entity.delete()
    model.Session.commit()
