# encoding: utf-8

from six.moves.urllib.parse import urlencode

from flask import Blueprint
from six import text_type

from ckan.common import json
from ckan.lib.helpers import decode_view_request_filters
from ckan.plugins.toolkit import get_action, request, h

datatablesview = Blueprint(u'datatablesview', __name__)


def merge_filters(view_filters,
                  user_filters):
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


def ajax(resource_view_id):
    resource_view = get_action(u'resource_view_show'
                               )(None, {
                                   u'id': resource_view_id
                               })

    draw = int(request.form[u'draw'])
    search_text = text_type(request.form[u'search[value]'])
    offset = int(request.form[u'start'])
    limit = int(request.form[u'length'])
    view_filters = resource_view.get(u'filters', {})
    user_filters = decode_view_request_filters()
    filters = merge_filters(view_filters, user_filters)

    datastore_search = get_action(u'datastore_search')
    unfiltered_response = datastore_search(
        None, {
            u"resource_id": resource_view[u'resource_id'],
            u"limit": 0,
            u"filters": view_filters,
        }
    )

    cols = [f[u'id'] for f in unfiltered_response[u'fields']]
    if u'show_fields' in resource_view:
        cols = [c for c in cols if c in resource_view[u'show_fields']]

    sort_list = []
    i = 0
    while True:
        if u'order[%d][column]' % i not in request.form:
            break
        sort_by_num = int(request.form[u'order[%d][column]' % i])
        sort_order = (
            u'desc' if request.form[u'order[%d][dir]' %
                                    i] == u'desc' else u'asc'
        )
        sort_list.append(cols[sort_by_num] + u' ' + sort_order)
        i += 1

    colsearch_dict = {}
    while True:
        if u'columns[%d][search][value]' % i not in request.form:
            break
        v = text_type(request.form[u'columns[%d][search][value]' % i])
        if v:
            k = text_type(request.form[u'columns[%d][name]' % i])
            # append ':*' so we can do partial FTS searches
            colsearch_dict[k] = v + u':*'
        i += 1

    if colsearch_dict:
        search_text = colsearch_dict
    else:
        search_text = search_text + u':*' if search_text else ''

    try:
        response = datastore_search(
            None, {
                u"q": search_text,
                u"resource_id": resource_view[u'resource_id'],
                u'plain': False,
                u'language': u'simple',
                u"offset": offset,
                u"limit": limit,
                u"sort": u', '.join(sort_list),
                u"filters": filters,
            }
        )
    except Exception:
        query_error = u'Invalid search query... ' + search_text
        dtdata = { u'error': query_error }
    else:
        data = []
        for row in response[u'records']:
            record = {colname: text_type(row.get(colname, u'')) for colname in cols}
            # the DT_RowId is used in DataTables to set an element id for each record
            record['DT_RowId'] = 'row'+text_type(row.get(u'_id', u''))
            data.append(record)

        dtdata = {
            u'draw': draw,
            u'recordsTotal': unfiltered_response.get(u'total', 0),
            u'recordsFiltered': response.get(u'total', 0),
            u'data': data
        }
    return json.dumps(dtdata)


def filtered_download(resource_view_id):
    params = json.loads(request.form[u'params'])
    resource_view = get_action(u'resource_view_show'
                               )(None, {
                                   u'id': resource_view_id
                               })

    search_text = text_type(params[u'search'][u'value'])
    view_filters = resource_view.get(u'filters', {})
    user_filters = decode_view_request_filters()
    filters = merge_filters(view_filters, user_filters)

    datastore_search = get_action(u'datastore_search')
    unfiltered_response = datastore_search(
        None, {
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

    return h.redirect_to(
        h.
        url_for(u'datastore.dump', resource_id=resource_view[u'resource_id']) +
        u'?' + urlencode({
            u'q': search_text,
            u'sort': u','.join(sort_list),
            u'filters': json.dumps(filters),
            u'format': request.form[u'format'],
            u'fields': u','.join(cols),
        })
    )


datatablesview.add_url_rule(
    u'/datatables/ajax/<resource_view_id>', view_func=ajax, methods=[u'POST']
)

datatablesview.add_url_rule(
    u'/datatables/filtered-download/<resource_view_id>',
    view_func=filtered_download, methods=[u'POST']
)
