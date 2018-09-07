# encoding: utf-8

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
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
import ckan.lib.navl.dictization_functions as dict_fns

from itertools import izip_longest

int_validator = get_validator('int_validator')
boolean_validator = get_validator('boolean_validator')

DUMP_FORMATS = 'csv', 'tsv', 'json', 'xml'
PAGINATE_BY = 32000


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

        if fmt not in DUMP_FORMATS:
            abort(400, _(
                u'format: must be one of %s') % u', '.join(DUMP_FORMATS))

        try:
            dump_to(
                resource_id,
                response,
                fmt=fmt,
                offset=offset,
                limit=limit,
                options={u'bom': bom})
        except ObjectNotFound:
            abort(404, _('DataStore resource not found'))

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
            data = dict_fns.unflatten(tuplize_dict(parse_params(
                request.params)))
            info = data.get(u'info')
            if not isinstance(info, list):
                info = []
            info = info[:len(fields)]

            get_action('datastore_create')(None, {
                'resource_id': resource_id,
                'force': True,
                'fields': [{
                    'id': f['id'],
                    'type': f['type'],
                    'info': fi if isinstance(fi, dict) else {}
                    } for f, fi in izip_longest(fields, info)]})

            h.redirect_to(
                controller='ckanext.datastore.controller:DatastoreController',
                action='dictionary',
                id=id,
                resource_id=resource_id)

        return render(
            'datastore/dictionary.html',
            extra_vars={'fields': fields})


def dump_to(resource_id, output, fmt, offset, limit, options):
    if fmt == 'csv':
        writer_factory = csv_writer
        records_format = 'csv'
    elif fmt == 'tsv':
        writer_factory = tsv_writer
        records_format = 'tsv'
    elif fmt == 'json':
        writer_factory = json_writer
        records_format = 'lists'
    elif fmt == 'xml':
        writer_factory = xml_writer
        records_format = 'objects'

    def start_writer(fields):
        bom = options.get(u'bom', False)
        return writer_factory(output, fields, resource_id, bom)

    def result_page(offs, lim):
        return get_action('datastore_search')(None, {
            'resource_id': resource_id,
            'limit':
                PAGINATE_BY if limit is None
                else min(PAGINATE_BY, lim),
            'offset': offs,
            'sort': '_id',
            'records_format': records_format,
            'include_total': False,
        })

    result = result_page(offset, limit)

    with start_writer(result['fields']) as wr:
        while True:
            if limit is not None and limit <= 0:
                break

            records = result['records']

            wr.write_records(records)

            if records_format == 'objects' or records_format == 'lists':
                if len(records) < PAGINATE_BY:
                    break
            elif not records:
                break

            offset += PAGINATE_BY
            if limit is not None:
                limit -= PAGINATE_BY
                if limit <= 0:
                    break

            result = result_page(offset, limit)
