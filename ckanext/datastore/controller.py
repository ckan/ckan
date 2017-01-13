# encoding: utf-8

import StringIO

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
from ckanext.datastore.writer import (
    csv_writer,
    tsv_writer,
    json_writer,
    xml_writer,
)

int_validator = get_validator('int_validator')
boolean_validator = get_validator('boolean_validator')

DUMP_FORMATS = 'csv', 'tsv', 'json', 'xml'
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

        def start_writer(fields):
            if fmt == 'csv':
                return csv_writer(response, fields, resource_id, bom)
            if fmt == 'tsv':
                return tsv_writer(response, fields, resource_id, bom)
            if fmt == 'json':
                return json_writer(response, fields, resource_id, bom)
            if fmt == 'xml':
                return xml_writer(response, fields, resource_id, bom)
            abort(400, _(
                u'format: must be one of %s') % u', '.join(DUMP_FORMATS))

        def result_page(offset, limit):
            try:
                return get_action('datastore_search')(None, {
                    'resource_id': resource_id,
                    'limit':
                        PAGINATE_BY if limit is None
                        else min(PAGINATE_BY, limit),
                    'offset': offset,
                    })
            except ObjectNotFound:
                abort(404, _('DataStore resource not found'))

        result = result_page(offset, limit)
        columns = [x['id'] for x in result['fields']]

        with start_writer(result['fields']) as wr:
            while True:
                if limit is not None and limit <= 0:
                    break

                for record in result['records']:
                    wr.writerow([record[column] for column in columns])

                if len(result['records']) < PAGINATE_BY:
                    break
                offset += PAGINATE_BY
                if limit is not None:
                    limit -= PAGINATE_BY

                result = result_page(offset, limit)
