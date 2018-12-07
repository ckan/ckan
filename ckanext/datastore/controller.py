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
    config,
)
from ckanext.datastore.writer import (
    csv_writer,
    tsv_writer,
    json_writer,
    xml_writer,
)
from ckanext.datastore.logic.schema import (
    list_of_strings_or_string,
    json_validator,
    unicode_or_json_validator,
)
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
import ckan.lib.navl.dictization_functions as dict_fns

from itertools import izip_longest

int_validator = get_validator('int_validator')
boolean_validator = get_validator('boolean_validator')
ignore_missing = get_validator('ignore_missing')
OneOf = get_validator('OneOf')
default = get_validator('default')
unicode_only = get_validator('unicode_only')


DUMP_FORMATS = 'csv', 'tsv', 'json', 'xml'
PAGINATE_BY = 32000


def dump_schema():
    return {
        'offset': [default(0), int_validator],
        'limit': [ignore_missing, int_validator],
        'format': [default('csv'), OneOf(DUMP_FORMATS)],
        'bom': [default(False), boolean_validator],
        'filters': [ignore_missing, json_validator],
        'q': [ignore_missing, unicode_or_json_validator],
        'distinct': [ignore_missing, boolean_validator],
        'plain': [ignore_missing, boolean_validator],
        'language': [ignore_missing, unicode_only],
        'fields': [ignore_missing, list_of_strings_or_string],
        'sort': [default('_id'), list_of_strings_or_string],
    }


class DatastoreController(BaseController):
    def dump(self, resource_id):
        data, errors = dict_fns.validate(dict(request.GET), dump_schema())
        if errors:
            abort(400, u'\n'.join(
                u'{0}: {1}'.format(k, ' '.join(e)) for k, e in errors.items()))

        try:
            dump_to(
                resource_id,
                response,
                fmt=data['format'],
                offset=data['offset'],
                limit=data.get('limit'),
                options={u'bom': data['bom']},
                sort=data['sort'],
                search_params={
                    k: v for k, v in data.items() if k in [
                        'filters',
                        'q',
                        'distinct',
                        'plain',
                        'language',
                        'fields']},
                )
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

            h.flash_success(_('Data Dictionary saved. Any type overrides will '
                              'take effect when the resource is next uploaded '
                              'to DataStore'))
            h.redirect_to(
                controller='ckanext.datastore.controller:DatastoreController',
                action='dictionary',
                id=id,
                resource_id=resource_id)

        return render(
            'datastore/dictionary.html',
            extra_vars={
                'fields': fields,
                'pkg_dict': c.pkg_dict,
                'resource': c.resource,
            })


def dump_to(
        resource_id, output, fmt, offset, limit, options, sort, search_params):
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
        return get_action('datastore_search')(None, dict({
            'resource_id': resource_id,
            'limit':
                PAGINATE_BY if limit is None
                else min(PAGINATE_BY, lim),
            'offset': offs,
            'sort': sort,
            'records_format': records_format,
            'include_total': False,
            }, **search_params))

    result = result_page(offset, limit)

    if result['limit'] != limit:
        # `limit` (from PAGINATE_BY) must have been more than
        # ckan.datastore.search.rows_max, so datastore_search responded with a
        # limit matching ckan.datastore.search.rows_max. So we need to paginate
        # by that amount instead, otherwise we'll have gaps in the records.
        paginate_by = result['limit']
    else:
        paginate_by = PAGINATE_BY

    with start_writer(result['fields']) as wr:
        while True:
            if limit is not None and limit <= 0:
                break

            records = result['records']

            wr.write_records(records)

            if records_format == 'objects' or records_format == 'lists':
                if len(records) < paginate_by:
                    break
            elif not records:
                break

            offset += paginate_by
            if limit is not None:
                limit -= paginate_by
                if limit <= 0:
                    break

            result = result_page(offset, limit)
