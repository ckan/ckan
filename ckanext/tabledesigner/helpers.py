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
    if tdtype not in plugin._column_types:
        if tdtype.startswith('int'):
            tdtype = 'integer'
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
    """
    return API example data for a resource (best effort)

    1. use real data and column types from the resource if possible
    2. use canned data and real column types otherwise
    3. use canned data and canned column types as a last resort
    """
    # future improvements: use real tdtype, use real choice values etc.
    resp = {}
    try:
        resp = get_action('datastore_search')(
            {},
            {'resource_id': resource_id, 'limit': 1}
        )
    except (ObjectNotFound, NotAuthorized):
        pass
    fields = []
    txtcols = []
    record = {}
    filtr = {}
    if resp and resp['fields']:
        fields = [f['id'] for f in resp['fields']]
        txtcols = [f['id'] for f in resp['fields'] if f['type'] == 'text']
        if resp['records'] and txtcols:
            record = resp['records'][0]
            filtr = {k: record[k] for k in fields[1:3]}

    if not txtcols:
        resp['fields'] = [
            {'id': '_id', 'type': 'int'},
            {'id': 'subject', 'type': 'text'},
            {'id': 'rating', 'type': 'numeric'},
        ]
        fields = [f['id'] for f in resp['fields']]
        txtcols = [f['id'] for f in resp['fields'] if f['type'] == 'text']

    if not filtr:
        record = {
            f['id']: h.tabledesigner_column_type(f).example
            for f in resp['fields']
        }
        filtr = {k: record[k] for k in fields[1:3]}

    return {
        "text_column_filters_object": filtr,
        "text_column_name_sql": txtcols[0],
        "insert_record_object": {
            k: v for k, v in record.items() if k != '_id'
        },
        "update_record_object": record,
        "unique_filter_object": {"_id": 1},
    }


@chained_helper
def datastore_rw_resource_url_types(
        next_func: Callable[[], List[str]]) -> List[str]:
    '''tabledesigner datastore tables can be updated without force=True'''
    return ['tabledesigner'] + next_func()
