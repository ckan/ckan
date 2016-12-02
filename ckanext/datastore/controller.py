# encoding: utf-8

import StringIO
import unicodecsv as csv

import pylons

import ckan.plugins as p
import ckan.lib.base as base
import ckan.model as model

from ckan.common import request


PAGINATE_BY = 10000


class DatastoreController(base.BaseController):
    def dump(self, resource_id):
        context = {
            'model': model,
            'session': model.Session,
            'user': p.toolkit.c.user
        }

        offset = 0
        wr = None
        while True:
            data_dict = {
                'resource_id': resource_id,
                'limit': request.GET.get('limit', PAGINATE_BY),
                'offset': request.GET.get('offset', offset)
            }

            action = p.toolkit.get_action('datastore_search')
            try:
                result = action(context, data_dict)
            except p.toolkit.ObjectNotFound:
                base.abort(404, p.toolkit._('DataStore resource not found'))

            if not wr:
                pylons.response.headers['Content-Type'] = 'text/csv'
                pylons.response.headers['Content-disposition'] = (
                    'attachment; filename="{name}.csv"'.format(
                        name=resource_id))
                wr = csv.writer(pylons.response, encoding='utf-8')

                header = [x['id'] for x in result['fields']]
                wr.writerow(header)

            for record in result['records']:
                wr.writerow([record[column] for column in header])

            offset += PAGINATE_BY
            if len(result['records']) < PAGINATE_BY:
                break
