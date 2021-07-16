# encoding: utf-8

from six.moves.urllib.parse import urlencode

from flask import Blueprint
from six import text_type

from ckan.common import json
from ckan.plugins.toolkit import get_action, request, h
import re

datatablesview = Blueprint('datatablesview', __name__)


def merge_filters(view_filters, user_filters_str):
    '''
    view filters are built as part of the view, user filters
    are selected by the user interacting with the view. Any filters
    selected by user may only tighten filters set in the view,
    others are ignored.

    >>> merge_filters({
    ...    'Department': ['BTDT'], 'OnTime_Status': ['ONTIME']},
    ...    'CASE_STATUS:Open|CASE_STATUS:Closed|Department:INFO')
    {'Department': ['BTDT'],
     'OnTime_Status': ['ONTIME'],
     'CASE_STATUS': ['Open', 'Closed']}
    '''
    filters = dict(view_filters)
    if not user_filters_str:
        return filters
    user_filters = {}
    for k_v in user_filters_str.split('|'):
        k, sep, v = k_v.partition(':')
        if k not in view_filters or v in view_filters[k]:
            user_filters.setdefault(k, []).append(v)
    for k in user_filters:
        filters[k] = user_filters[k]
    return filters


def ajax(resource_view_id):
    resource_view = get_action('resource_view_show'
                               )(None, {
                                   'id': resource_view_id
                               })

    draw = int(request.form['draw'])
    search_text = text_type(request.form['search[value]'])
    offset = int(request.form['start'])
    limit = int(request.form['length'])
    view_filters = resource_view.get('filters', {})
    user_filters = text_type(request.form['filters'])
    filters = merge_filters(view_filters, user_filters)

    datastore_search = get_action('datastore_search')
    unfiltered_response = datastore_search(
        None, {
            "resource_id": resource_view['resource_id'],
            "limit": 0,
            "filters": view_filters,
        }
    )

    cols = [f['id'] for f in unfiltered_response['fields']]
    if 'show_fields' in resource_view:
        cols = [c for c in cols if c in resource_view['show_fields']]

    sort_list = []
    i = 0
    while True:
        if 'order[%d][column]' % i not in request.form:
            break
        sort_by_num = int(request.form['order[%d][column]' % i])
        sort_order = (
            'desc' if request.form['order[%d][dir]' %
                                    i] == 'desc' else 'asc'
        )
        sort_list.append(cols[sort_by_num] + ' ' + sort_order)
        i += 1

    colsearch_dict = {}
    i = 0
    while True:
        if 'columns[%d][search][value]' % i not in request.form:
            break
        v = text_type(request.form['columns[%d][search][value]' % i])
        if v:
            k = text_type(request.form['columns[%d][name]' % i])
            # replace non-alphanumeric characters with FTS wildcard (_)
            v = re.sub(r'[^0-9a-zA-Z\-]+', '_', v)
            # append ':*' so we can do partial FTS searches
            colsearch_dict[k] = v + ':*'
        i += 1

    if colsearch_dict:
        search_text = json.dumps(colsearch_dict)
    else:
        search_text = re.sub(r'[^0-9a-zA-Z\-]+', '_',
                             search_text) + ':*' if search_text else ''

    try:
        response = datastore_search(
            None, {
                "q": search_text,
                "resource_id": resource_view['resource_id'],
                'plain': False,
                'language': 'simple',
                "offset": offset,
                "limit": limit,
                "sort": ', '.join(sort_list),
                "filters": filters,
            }
        )
    except Exception:
        query_error = 'Invalid search query... ' + search_text
        dtdata = {'error': query_error}
    else:
        data = []
        for row in response['records']:
            record = {colname: text_type(row.get(colname, ''))
                      for colname in cols}
            # the DT_RowId is used in DT to set an element id for each record
            record['DT_RowId'] = 'row' + text_type(row.get('_id', ''))
            data.append(record)

        dtdata = {
            'draw': draw,
            'recordsTotal': unfiltered_response.get('total', 0),
            'recordsFiltered': response.get('total', 0),
            'data': data
        }

    return json.dumps(dtdata)


def filtered_download(resource_view_id):
    params = json.loads(request.form['params'])
    resource_view = get_action('resource_view_show'
                               )(None, {
                                   'id': resource_view_id
                               })

    search_text = text_type(params['search']['value'])
    view_filters = resource_view.get('filters', {})
    user_filters = text_type(params['filters'])
    filters = merge_filters(view_filters, user_filters)

    datastore_search = get_action('datastore_search')
    unfiltered_response = datastore_search(
        None, {
            "resource_id": resource_view['resource_id'],
            "limit": 0,
            "filters": view_filters,
        }
    )

    cols = [f['id'] for f in unfiltered_response['fields']]
    if 'show_fields' in resource_view:
        cols = [c for c in cols if c in resource_view['show_fields']]

    sort_list = []
    for order in params['order']:
        sort_by_num = int(order['column'])
        sort_order = ('desc' if order['dir'] == 'desc' else 'asc')
        sort_list.append(cols[sort_by_num] + ' ' + sort_order)

    cols = [c for (c, v) in zip(cols, params['visible']) if v]

    colsearch_dict = {}
    columns = params['columns']
    for column in columns:
        if column['search']['value']:
            v = column['search']['value']
            if v:
                k = column['name']
                # replace non-alphanumeric characters with FTS wildcard (_)
                v = re.sub(r'[^0-9a-zA-Z\-]+', '_', v)
                # append ':*' so we can do partial FTS searches
                colsearch_dict[k] = v + ':*'

    if colsearch_dict:
        search_text = json.dumps(colsearch_dict)
    else:
        search_text = re.sub(r'[^0-9a-zA-Z\-]+', '_',
                             search_text) + ':*' if search_text else ''

    return h.redirect_to(
        h.url_for(
            'datastore.dump',
            resource_id=resource_view['resource_id']) + '?' + urlencode(
            {
                'q': search_text,
                'plain': False,
                'language': 'simple',
                'sort': ','.join(sort_list),
                'filters': json.dumps(filters),
                'format': request.form['format'],
                'fields': ','.join(cols),
            }))


datatablesview.add_url_rule(
    '/datatables/ajax/<resource_view_id>', view_func=ajax, methods=['POST']
)

datatablesview.add_url_rule(
    '/datatables/filtered-download/<resource_view_id>',
    view_func=filtered_download, methods=['POST']
)
