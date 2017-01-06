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
boolean_validator = get_validator('boolean_validator')

UTF8_BOM = u'\uFEFF'.encode('utf-8')
DUMP_FORMATS = 'csv', 'tsv'
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
        bom = boolean_validator(request.GET.get('bom'), {})
        fmt = request.GET.get('format', 'csv')

        def start_writer():
            if fmt == 'csv':
                response.headers['Content-Type'] = 'text/csv; charset=utf-8'
                response.headers['Content-disposition'] = (
                    'attachment; filename="{name}.csv"'.format(
                        name=resource_id))
                wr = csv.writer(response, encoding='utf-8')
            elif fmt == 'tsv':
                response.headers['Content-Type'] = (
                    'text/tab-separated-values; charset=utf-8')
                response.headers['Content-disposition'] = (
                    'attachment; filename="{name}.tsv"'.format(
                        name=resource_id))
                wr = csv.writer(
                    response, encoding='utf-8', dialect=csv.excel_tab)
            else:
                abort(400,
                    _(u'format: must be one of %s') % u', '.join(DUMP_FORMATS))

            if bom:
                response.write(UTF8_BOM)
            return wr

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
                wr = start_writer()

                header = [x['id'] for x in result['fields']]
                wr.writerow(header)

            for record in result['records']:
                wr.writerow([record[column] for column in header])

            if len(result['records']) < PAGINATE_BY:
                break
            offset += PAGINATE_BY
            if limit is not None:
                limit -= PAGINATE_BY
