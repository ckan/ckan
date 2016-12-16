# encoding: utf-8

import StringIO
import unicodecsv as csv

import pylons

from ckan.plugins.toolkit import (
    Invalid,
    ObjectNotFound,
    get_action,
    get_validator,
    _,
    request,
    response,
    BaseController,
    abort,
)

int_validator = get_validator('int_validator')

PAGINATE_BY = 10000


class DatastoreController(BaseController):
    def dump(self, resource_id):
        try:
            offset = int_validator(request.GET.get('offset', 0), {})
        except Invalid as e:
            abort(400, u'offset: ' + e.error)
        try:
            limit = int_validator(request.GET.get('limit'), {})
        except Invalid as e:
            abort(400, u'limit: ' + e.error)

        wr = None
        while True:
            if limit is not None and limit <= 0:
                break

            try:
                result = get_action('datastore_search')(None, {
                    'resource_id': resource_id,
                    'limit':
                        PAGINATE_BY if limit is None
                        else min(PAGINATE_BY, limit),
                    'offset': offset,
                    })
            except ObjectNotFound:
                abort(404, _('DataStore resource not found'))

            if not wr:
                response.headers['Content-Type'] = 'text/csv; charset=utf-8'
                response.headers['Content-disposition'] = (
                    'attachment; filename="{name}.csv"'.format(
                        name=resource_id))
                wr = csv.writer(response, encoding='utf-8')

                header = [x['id'] for x in result['fields']]
                wr.writerow(header)

            for record in result['records']:
                wr.writerow([record[column] for column in header])

            if len(result['records']) < PAGINATE_BY:
                break
            offset += PAGINATE_BY
            if limit is not None:
                limit -= PAGINATE_BY
