# encoding: utf-8

from six.moves.urllib.parse import urlencode

from flask import Blueprint
from six import text_type

from ckan.common import json
from ckan.plugins.toolkit import get_action, request, h

datatablesview = Blueprint(u'datatablesview', __name__)


def merge_filters(view_filters, user_filters_str):
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
    if not user_filters_str:
        return filters
    user_filters = {}
    for k_v in user_filters_str.split(u'|'):
        k, sep, v = k_v.partition(u':')
        if k not in view_filters or v in view_filters[k]:
            user_filters.setdefault(k, []).append(v)
    for k in user_filters:
        filters[k] = user_filters[k]
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
    user_filters = text_type(request.form[u'filters'])
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

    response = datastore_search(
        None, {
            u"q": search_text,
            u"resource_id": resource_view[u'resource_id'],
            u"offset": offset,
            u"limit": limit,
            u"sort": u', '.join(sort_list),
            u"filters": filters,
        }
    )

    return json.dumps({
        u'draw': draw,
        u'iTotalRecords': unfiltered_response.get(u'total', 0),
        u'iTotalDisplayRecords': response.get(u'total', 0),
        u'aaData': [[text_type(row.get(colname, u''))
                     for colname in cols]
                    for row in response[u'records']],
    })


def filtered_download(resource_view_id):
    params = json.loads(request.params[u'params'])
    resource_view = get_action(u'resource_view_show'
                               )(None, {
                                   u'id': resource_view_id
                               })

    search_text = text_type(params[u'search'][u'value'])
    view_filters = resource_view.get(u'filters', {})
    user_filters = text_type(params[u'filters'])
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

    h.redirect_to(
        h.
        url_for(u'datastore.dump', resource_id=resource_view[u'resource_id']) +
        u'?' + urlencode({
            u'q': search_text,
            u'sort': u','.join(sort_list),
            u'filters': json.dumps(filters),
            u'format': request.params[u'format'],
            u'fields': u','.join(cols),
        })
    )


datatablesview.add_url_rule(
    u'/datatables/ajax/<resource_view_id>', view_func=ajax, methods=[u'POST']
)

datatablesview.add_url_rule(
    u'/datatables/filtered-download/<resource_view_id>',
    view_func=filtered_download
)
