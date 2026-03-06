# encoding: utf-8

import json
from unittest.mock import patch

import pytest

import ckanext.datastore.backend.postgres as db
from ckan.logic import NotFound
from ckan.tests import factories, helpers
from ckan.lib.helpers import url_for


@pytest.mark.ckan_config("ckan.plugins", "datastore datatables_view")
@pytest.mark.usefixtures("with_plugins")
def test_ajax_data(app, user):
    dataset = factories.Dataset()
    ds = helpers.call_action(
        'datastore_create',
        resource={'package_id': dataset['id']},
        fields=[{'id': 'a', 'type': 'text'}, {'id': 'b', 'type': 'int'}],
        records=[
            {'a': 'one', 'b': 1},
            {'a': 'two', 'b': 2},
            {'a': 'a < b && a > 0', 'b': None}
        ],
    )
    view = factories.ResourceView(
        view_type='datatables_view',
        resource_id=ds['resource_id']
    )
    resp = app.post(
        url=url_for('datatablesview.ajax', resource_view_id=view["id"]),
        data={
            'draw': 1,
            'search[value]': '',
            'start': 0,
            'length': 50,
        },
    )
    ajax = json.loads(b''.join(resp.response).decode('utf-8'))
    assert ajax == {
        'draw': 1,
        'recordsFiltered': 3,
        'recordsTotal': 3,
        'data': [
            {'_id': '1', 'a': 'one', 'b': '1', 'DT_RowId': 'row1'},
            {'_id': '2', 'a': 'two', 'b': '2', 'DT_RowId': 'row2'},
            {
                '_id': '3',
                'a': 'a &lt; b &amp;&amp; a &gt; 0',
                'b': '',
                'DT_RowId': 'row3',
            },
        ],
        'total_was_estimated': False,
    }


@pytest.mark.ckan_config("ckan.plugins", "datastore datatables_view")
@pytest.mark.usefixtures("with_plugins")
def test_datastore_search_raises_not_found_when_table_missing():
    """ datastore_search raises ObjectNotFound when the table does not exist
        and the resource_id_from_alias returns (True, None) to
        indicate that the view exists but the table is missing.
    """
    with patch.object(
        db.DatastorePostgresqlBackend,
        'resource_id_from_alias',
        return_value=(True, None),
    ):
        with pytest.raises(NotFound):
            helpers.call_action(
                'datastore_search',
                resource_id='00000000-0000-0000-0000-000000000000',
            )
