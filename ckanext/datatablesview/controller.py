# encoding: utf-8

import json

from ckan.plugins.toolkit import BaseController, request, get_action


class DataTablesController(BaseController):
    def ajax(self, resource_view_id):
        resource_view = get_action(u'resource_view_show')(
            None, {u'id': resource_view_id})

        draw = int(request.params['draw'])
        search_text = unicode(request.params['search[value]'])
        offset = int(request.params['start'])
        limit = int(request.params['length'])
        sort_by_num = int(request.params['order[0][column]'])
        sort_order = (
            u'desc' if request.params['order[0][dir]'] == u'desc'
            else u'asc')

        datastore_search = get_action(u'datastore_search')
        unfiltered_response = datastore_search(None, {
            u"resource_id": resource_view[u'resource_id'],
            u"limit": 0,
            u"filters": resource_view.get(u'filters', {}),
        })

        cols = [f['id'] for f in unfiltered_response['fields']]
        sort_str = cols[sort_by_num] + u' ' + sort_order

        response = datastore_search(None, {
            u"q": search_text,
            u"resource_id": resource_view[u'resource_id'],
            u"offset": offset,
            u"limit": limit,
            u"sort": sort_str,
            u"filters": resource_view.get(u'filters', {}),
        })

        return json.dumps({
            u'draw': draw,
            u'iTotalRecords': unfiltered_response.get(u'total', 0),
            u'iTotalDisplayRecords': response.get(u'total', 0),
            u'aaData': [
                [unicode(row.get(colname, u'')) for colname in cols]
                for row in response['records']
            ],
        })
