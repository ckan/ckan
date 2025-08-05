# encoding: utf-8
from __future__ import annotations

from typing import Any, Callable

from ckan.types import Context
from ckan.plugins.toolkit import get_action, chained_action, ValidationError

from ckanext.tabledesigner.datastore import create_table


@chained_action
def resource_create(
        original_action: Callable[[Context, dict[str, Any]], dict[str, Any]],
        context: Context,
        data_dict: dict[str, Any]) -> dict[str, Any]:
    res = original_action(context, data_dict)
    _create_table_and_view(context, res)
    return res


@chained_action
def resource_update(
        original_action: Callable[[Context, dict[str, Any]], dict[str, Any]],
        context: Context,
        data_dict: dict[str, Any]) -> dict[str, Any]:
    res = original_action(context, data_dict)
    _create_table_and_view(context, res)
    return res


def _create_table_and_view(context: Context, res: dict[str, Any]) -> None:
    if res.get('url_type') != 'tabledesigner':
        return

    if not res.get('datastore_active'):
        create_table(context, res['id'], [])

    views = get_action('resource_view_list')(context, {
        'id': res['id']
    })

    if any(v['view_type'] == 'datatables_view' for v in views):
        return

    try:
        get_action('resource_view_create')(context, {
            'resource_id': res['id'],
            'view_type': 'datatables_view',
            'title': 'Table',
        })
    except ValidationError:
        # missing datatables_view but too late to abort resource
        # create/update, show warning on preview page instead
        return
