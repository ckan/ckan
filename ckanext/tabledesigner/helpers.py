from __future__ import annotations

from typing import Callable, List, Any
from collections.abc import Iterable, Mapping

from . import plugin
from .column_types import ColumnType, TextColumn

from ckan.plugins.toolkit import (
    _, NotAuthorized, ObjectNotFound, get_action, chained_helper, h
)


def tabledesigner_column_type_options() -> List[dict[str, Any]]:
    """
    return list of {'value':..., 'text':...} dicts
    with the type name and label for all registered column types
    """
    return [
        {"value": k, "text": _(v.label)}
        for k, v in plugin._column_types.items()
    ]


def tabledesigner_column_type(field: dict[str, Any]) -> ColumnType:
    """
    return column type object (fall back to text if not found)
    """
    tdtype = field.get('tdtype', field.get('type', 'text'))
    return plugin._column_types.get(
        tdtype,
        plugin._column_types.get('text', TextColumn)
    )(field, plugin._column_constraints.get(tdtype, []))


def tabledesigner_choices(
        field: dict[str, Any]) -> Iterable[str] | Mapping[str, str]:
    ct = h.tabledesigner_column_type(field)
    if hasattr(ct, 'choices'):
        return ct.choices()
    return {}


def tabledesigner_data_api_examples(resource_id: str) -> dict[str, Any]:
    resp = None
    try:
        resp = get_action('datastore_search')(
            {},
            {'resource_id': resource_id, 'limit': 1}
        )
    except (ObjectNotFound, NotAuthorized):
        pass
    if resp and resp['records']:
        record = resp['records'][0]
        fields = [f['id'] for f in resp['fields']]
        filtr = {k: record[k] for k in fields[1:3]}
        txtcols = [f['id'] for f in resp['fields'] if f['type'] == 'text']
        if filtr and txtcols:
            return {
                "text_column_filters_object": filtr,
                "text_column_name_sql": txtcols[0],
                "insert_record_object": {
                    k: v for k, v in record.items() if k != '_id'
                },
                "update_record_object": record,
                "unique_filter_object": {"_id": 1},
            }
    return {
        "text_column_filters_object": {
            "subject": ["watershed", "survey"],
            "stage": "active",
        },
        "text_column_name_sql": "title",
        "insert_record_object": {
            "subject": "watershed",
            "stage": "active",
        },
        "update_record_object": {
            "_id": 1,
            "subject": "survey",
            "stage": "inactive",
        },
        "unique_filter_object": {"_id": 1},
    }


@chained_helper
def datastore_rw_resource_url_types(
        next_func: Callable[[], List[str]]) -> List[str]:
    '''tabledesigner datastore tables can be updated without force=True'''
    return ['tabledesigner'] + next_func()
