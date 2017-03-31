# encoding: utf-8

import json

from ckan.plugins.toolkit import (
    Invalid,
    ObjectNotFound,
    NotAuthorized,
    get_action,
    get_validator,
    _,
    request,
    response,
    BaseController,
    abort,
    render,
    c,
    h,
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

    def dictionary(self, id, resource_id):
        u'''data dictionary view: show/edit field labels and descriptions'''

        try:
            # resource_edit_base template uses these
            c.pkg_dict = get_action('package_show')(
                None, {'id': id})
            c.resource = get_action('resource_show')(
                None, {'id': resource_id})
            rec = get_action('datastore_search')(None, {
                'resource_id': resource_id,
                'limit': 0})
        except (ObjectNotFound, NotAuthorized):
            abort(404, _('Resource not found'))

        fields = [f for f in rec['fields'] if not f['id'].startswith('_')]

        if request.method == 'POST':
            get_action('datastore_create')(None, {
                'resource_id': resource_id,
                'force': True,
                'fields': [{
                    'id': f['id'],
                    'type': f['type'],
                    'info': {
                        'label': request.POST.get('f{0}label'.format(i)),
                        'notes': request.POST.get('f{0}notes'.format(i)),
                        }} for i, f in enumerate(fields, 1)]})

            h.redirect_to(
                controller='ckanext.datastore.controller:DatastoreController',
                action='dictionary',
                id=id,
                resource_id=resource_id)

        return render(
            'datastore/dictionary.html',
            extra_vars={'fields': fields})
