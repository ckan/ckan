# encoding: utf-8

from six.moves import zip_longest

from flask import Blueprint, make_response
from flask.views import MethodView

import ckan.lib.navl.dictization_functions as dict_fns
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
from ckan.plugins.toolkit import (
    ObjectNotFound, NotAuthorized, get_action, get_validator, _, request,
    abort, render, c, h
)
from ckanext.datastore.logic.schema import (
    list_of_strings_or_string,
    json_validator,
    unicode_or_json_validator,
)
from ckanext.datastore.writer import (
    csv_writer,
    tsv_writer,
    json_writer,
    xml_writer,
)

int_validator = get_validator('int_validator')
boolean_validator = get_validator('boolean_validator')
ignore_missing = get_validator('ignore_missing')
one_of = get_validator('one_of')
default = get_validator('default')
unicode_only = get_validator('unicode_only')

DUMP_FORMATS = 'csv', 'tsv', 'json', 'xml'
PAGINATE_BY = 32000

datastore = Blueprint('datastore', __name__)


def dump_schema():
    return {
        'offset': [default(0), int_validator],
        'limit': [ignore_missing, int_validator],
        'format': [default('csv'), one_of(DUMP_FORMATS)],
        'bom': [default(False), boolean_validator],
        'filters': [ignore_missing, json_validator],
        'q': [ignore_missing, unicode_or_json_validator],
        'distinct': [ignore_missing, boolean_validator],
        'plain': [ignore_missing, boolean_validator],
        'language': [ignore_missing, unicode_only],
        'fields': [ignore_missing, list_of_strings_or_string],
        'sort': [default('_id'), list_of_strings_or_string],
    }


def dump(resource_id):
    data, errors = dict_fns.validate(request.args.to_dict(), dump_schema())
    if errors:
        abort(
            400, '\n'.join(
                '{0}: {1}'.format(k, ' '.join(e)) for k, e in errors.items()
            )
        )

    response = make_response()
    response.headers['content-type'] = 'application/octet-stream'

    try:
        dump_to(
            resource_id,
            response,
            fmt=data['format'],
            offset=data['offset'],
            limit=data.get('limit'),
            options={'bom': data['bom']},
            sort=data['sort'],
            search_params={
                k: v
                for k, v in data.items()
                if k in [
                    'filters', 'q', 'distinct', 'plain', 'language',
                    'fields'
                ]
            },
        )
    except ObjectNotFound:
        abort(404, _('DataStore resource not found'))
    return response


class DictionaryView(MethodView):

    def _prepare(self, id, resource_id):
        try:
            # resource_edit_base template uses these
            pkg_dict = get_action('package_show')(None, {'id': id})
            resource = get_action('resource_show')(None, {'id': resource_id})
            rec = get_action('datastore_search')(
                None, {
                    'resource_id': resource_id,
                    'limit': 0
                }
            )
            return {
                'pkg_dict': pkg_dict,
                'resource': resource,
                'fields': [
                    f for f in rec['fields'] if not f['id'].startswith('_')
                ]
            }

        except (ObjectNotFound, NotAuthorized):
            abort(404, _('Resource not found'))

    def get(self, id, resource_id):
        '''Data dictionary view: show field labels and descriptions'''

        data_dict = self._prepare(id, resource_id)

        # global variables for backward compatibility
        c.pkg_dict = data_dict['pkg_dict']
        c.resource = data_dict['resource']

        return render('datastore/dictionary.html', data_dict)

    def post(self, id, resource_id):
        '''Data dictionary view: edit field labels and descriptions'''
        data_dict = self._prepare(id, resource_id)
        fields = data_dict['fields']
        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        info = data.get('info')
        if not isinstance(info, list):
            info = []
        info = info[:len(fields)]

        get_action('datastore_create')(
            None, {
                'resource_id': resource_id,
                'force': True,
                'fields': [{
                    'id': f['id'],
                    'type': f['type'],
                    'info': fi if isinstance(fi, dict) else {}
                } for f, fi in zip_longest(fields, info)]
            }
        )

        h.flash_success(
            _(
                'Data Dictionary saved. Any type overrides will '
                'take effect when the resource is next uploaded '
                'to DataStore'
            )
        )
        return h.redirect_to(
            'datastore.dictionary', id=id, resource_id=resource_id
        )


def dump_to(
    resource_id, output, fmt, offset, limit, options, sort, search_params
):
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
        bom = options.get('bom', False)
        return writer_factory(output, fields, resource_id, bom)

    def result_page(offs, lim):
        return get_action('datastore_search')(
            None,
            dict({
                'resource_id': resource_id,
                'limit': PAGINATE_BY
                if limit is None else min(PAGINATE_BY, lim),
                'offset': offs,
                'sort': sort,
                'records_format': records_format,
                'include_total': False,
            }, **search_params)
        )

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


datastore.add_url_rule('/datastore/dump/<resource_id>', view_func=dump)
datastore.add_url_rule(
    '/dataset/<id>/dictionary/<resource_id>',
    view_func=DictionaryView.as_view(str('dictionary'))
)
