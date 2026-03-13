# encoding: utf-8
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode
from html import escape

from flask import Blueprint


from ckan.common import json
from ckan.lib.helpers import decode_view_request_filters
from ckan.plugins.toolkit import (
    get_action,
    h,
    NotAuthorized,
    ObjectNotFound,
    request,
    config,
)
import re

ESTIMATION_THRESHOLD = 100000

datatablesview = Blueprint(u'datatablesview', __name__)


def merge_filters(view_filters: dict[str, Any],
                  user_filters: dict[str, Any] | None) -> dict[str, Any]:
    u'''
    view filters are built as part of the view, user filters
    are selected by the user interacting with the view. Any filters
    selected by user may only tighten filters set in the view,
    others are ignored.

    >>> merge_filters({
    ...    u'Department': [u'BTDT'], u'OnTime_Status': [u'ONTIME']},
    ...    u'CASE_STATUS:Open|CASE_STATUS:Closed|Department:INFO')
    {u'Department': [u'BTDT'],
     u'OnTime_Status': [u'ONTIME'],
     u'CASE_STATUS': [u'Open', u'Closed']}
    '''
    filters = dict(view_filters)
    if not user_filters:
        return filters
    combined_user_filters = {}
    for k in user_filters:
        if k not in view_filters or user_filters[k] in view_filters[k]:
            combined_user_filters[k] = user_filters[k]
        else:
            combined_user_filters[k] = user_filters[k] + view_filters[k]
    for k in combined_user_filters:
        filters[k] = combined_user_filters[k]
    return filters


def ajax(resource_view_id: str):
    resource_view = get_action('resource_view_show')(
        {}, {'id': resource_view_id})

    draw = int(request.form['draw'])
    search_text = str(request.form['search[value]'])
    offset = int(request.form['start'])
    limit = int(request.form['length'])
    view_filters = resource_view.get('filters', {})
    user_filters = decode_view_request_filters()
    filters = merge_filters(view_filters, user_filters)

    datastore_search = get_action('datastore_search')
    try:
        unfiltered_response = datastore_search(
            {}, {
                "resource_id": resource_view['resource_id'],
                "limit": 0,
                "filters": view_filters,
                "total_estimation_threshold": ESTIMATION_THRESHOLD,
            }
        )
    except ObjectNotFound:
        return json.dumps({'error': 'Object not found'}), 404
    except NotAuthorized:
        return json.dumps({'error': 'Not Authorized'}), 403

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
        sort_list.append(cols[sort_by_num] + u' ' + sort_order)
        i += 1

    colsearch_dict = {}
    i = 0
    while True:
        if 'columns[%d][search][value]' % i not in request.form:
            break
        v = str(request.form['columns[%d][search][value]' % i])
        if v:
            k = str(request.form['columns[%d][name]' % i])
            # replace non-alphanumeric characters with FTS wildcard (_)
            v = re.sub(r'[^0-9a-zA-Z\-]+', '_', v)
            # append ':*' so we can do partial FTS searches
            colsearch_dict[k] = v + ':*'
        i += 1

    if colsearch_dict:
        search_text = json.dumps(colsearch_dict)
    else:
        search_text = re.sub(r'[^0-9a-zA-Z\-]+', '_',
                             search_text) + u':*' if search_text else u''

    histogram_data = {}

    try:
        response = datastore_search(
            {}, {
                "q": search_text,
                "resource_id": resource_view['resource_id'],
                'plain': False,
                'language': 'simple',
                "offset": offset,
                "limit": limit,
                "sort": ', '.join(sort_list),
                "filters": filters,
                "total_estimation_threshold": ESTIMATION_THRESHOLD,
            }
        )
        if config.get('ckan.datatables.show_histograms') and response['records']:
            # TODO: get flat data
            # datastore_search w/ buckets=
            histogram_response = get_action('datastore_search_buckets')(
                {'ignore_auth': True},
                {"q": search_text,
                 "resource_id": resource_view['resource_id'],
                 "plain": False,
                 "language": "simple",
                 "filters": filters})
    except Exception:
        query_error = 'Invalid search query... ' + search_text
        dtdata = {'error': query_error}
        status = 400
    else:
        data = []
        histogram_data = {}
        if config.get('ckan.datatables.show_histograms') and response['records']:
            # TODO: backend for flat histogram data!!!
            data = [dict({f['id']: '' for f in response['fields']},
                         DT_RowId='dt-row-histogram')]
            histogram_data = histogram_response.get('buckets', {})
        null_label = h.datatablesview_null_label()
        for row in response['records']:
            # NOTE: do null_label in backend for None, as front-end would
            #       also do blank values, and we want to show empty values
            #       as it could be considered data.
            record = {colname: escape(str(null_label if row.get(colname, '')
                                          is None else row.get(colname, None)))
                      for colname in cols}
            # the DT_RowId is used in DT to set an element id for each record
            record['DT_RowId'] = 'row' + str(row.get('_id', ''))
            data.append(record)

        dtdata = {
            'draw': draw,
            'recordsTotal': unfiltered_response.get('total', 0),
            'recordsFiltered': response.get('total', 0),
            'data': data,
            'histogram_data': histogram_data,
            'total_was_estimated': unfiltered_response.get(
                'total_was_estimated', False),
        }
        status = 200

    # return the response as JSON with status
    return json.dumps(dtdata), status


def filtered_download(resource_view_id: str):
    params = json.loads(request.form[u'params'])
    resource_view = get_action(u'resource_view_show'
                               )({}, {
                                   u'id': resource_view_id
                               })

    search_text = str(params[u'search'][u'value'])
    view_filters = resource_view.get(u'filters', {})
    user_filters = decode_view_request_filters()
    filters = merge_filters(view_filters, user_filters)

    datastore_search = get_action(u'datastore_search')
    unfiltered_response = datastore_search(
        {}, {
            u"resource_id": resource_view[u'resource_id'],
            u"limit": 0,
            u"filters": view_filters,
        }
    )

    cols = [f[u'id'] for f in unfiltered_response[u'fields']]
    if u'show_fields' in resource_view:
        cols = [c for c in cols if c in resource_view[u'show_fields']]

    sort_list = []
    for order in params[u'order']:
        sort_by_num = int(order[u'column'])
        sort_order = (u'desc' if order[u'dir'] == u'desc' else u'asc')
        sort_list.append(cols[sort_by_num] + u' ' + sort_order)

    cols = [c for (c, v) in zip(cols, params[u'visible']) if v]

    colsearch_dict = {}
    columns = params[u'columns']
    for column in columns:
        if column[u'search'][u'value']:
            v = column[u'search'][u'value']
            if v:
                k = column[u'name']
                # replace non-alphanumeric characters with FTS wildcard (_)
                v = re.sub(r'[^0-9a-zA-Z\-]+', '_', v)
                # append ':*' so we can do partial FTS searches
                colsearch_dict[k] = v + u':*'

    if colsearch_dict:
        search_text = json.dumps(colsearch_dict)
    else:
        search_text = re.sub(r'[^0-9a-zA-Z\-]+', '_',
                             search_text) + u':*' if search_text else ''

    return h.redirect_to(
        h.url_for(
            u'datastore.dump',
            resource_id=resource_view[u'resource_id']) + u'?' + urlencode(
            {
                u'q': search_text,
                u'plain': False,
                u'language': u'simple',
                u'sort': u','.join(sort_list),
                u'filters': json.dumps(filters),
                u'format': request.form[u'format'],
                u'fields': u','.join(cols),
            }))


datatablesview.add_url_rule(
    u'/datatables/ajax/<resource_view_id>', view_func=ajax, methods=[u'POST']
)

datatablesview.add_url_rule(
    u'/datatables/filtered-download/<resource_view_id>',
    view_func=filtered_download, methods=[u'POST']
)
