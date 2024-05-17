# encoding: utf-8

from six.moves import zip_longest
import six

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.lib.navl.dictization_functions as dict_fns
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
from ckan.plugins.toolkit import (
    ObjectNotFound, NotAuthorized, get_action, get_validator, _, request,
    abort, render, c, h, Invalid, ValidationError
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
if six.PY2:
    from cStringIO import StringIO
else:
    from io import StringIO

int_validator = get_validator(u'int_validator')
boolean_validator = get_validator(u'boolean_validator')
ignore_missing = get_validator(u'ignore_missing')
one_of = get_validator(u'one_of')
default = get_validator(u'default')
unicode_only = get_validator(u'unicode_only')
resource_id_validator = get_validator(u'resource_id_validator')

DUMP_FORMATS = u'csv', u'tsv', u'json', u'xml'
PAGINATE_BY = 32000

datastore = Blueprint(u'datastore', __name__)

# (canada fork only): exclude _id field from Blueprint dump
from ckan.plugins.toolkit import missing, StopOnError
from flask import has_request_context
from six import text_type
def exclude_id_from_ds_dump(key, data, errors, context):
    """
    Always set the list of fields to dump from the DataStore. Excluding to _id column.

    This validator is only used in the dump_schema.
    """
    value = data.get(key)

    if not has_request_context() and not hasattr(request, 'view_args') and 'resource_id' not in request.view_args:
        # treat as ignore_missing
        data.pop(key, None)
        raise StopOnError

    resource_id = request.view_args['resource_id']

    if value is missing or value is None:
        ds_info = get_action('datastore_info')(context, {'id': resource_id})
        # _id is never returned from datastore_info
        value = [field['id'] for field in ds_info.get('fields', [])]
    else:
        # fields accepts string or list of strings
        if isinstance(value, text_type):
            value = value.split(',')
        if isinstance(value, list):
            value.remove('_id')

    data[key] = value


def dump_schema():
    return {
        u'offset': [default(0), int_validator],
        u'limit': [ignore_missing, int_validator],
        u'format': [default(u'csv'), one_of(DUMP_FORMATS)],
        u'bom': [default(False), boolean_validator],
        u'filters': [ignore_missing, json_validator],
        u'q': [ignore_missing, unicode_or_json_validator],
        u'distinct': [ignore_missing, boolean_validator],
        u'plain': [ignore_missing, boolean_validator],
        u'language': [ignore_missing, unicode_only],
        u'fields': [exclude_id_from_ds_dump, list_of_strings_or_string],  # (canada fork only): exclude _id field from Blueprint dump
        u'sort': [default(u'_id'), list_of_strings_or_string],
    }


def dump(resource_id):
    try:
        resource_id = resource_id_validator(resource_id)
    except Invalid:
        abort(404, _(u'DataStore resource not found'))

    data, errors = dict_fns.validate(request.args.to_dict(), dump_schema())
    if errors:
        abort(
            400, u'\n'.join(
                u'{0}: {1}'.format(k, u' '.join(e)) for k, e in errors.items()
            )
        )

    fmt = data[u'format']
    offset = data[u'offset']
    limit = data.get(u'limit')
    options = {u'bom': data[u'bom']}
    sort = data[u'sort']
    search_params = {
        k: v
        for k, v in data.items()
        if k in [
            u'filters', u'q', u'distinct', u'plain', u'language',
            u'fields'
        ]
    }

    if fmt == u'csv':
        writer_factory = csv_writer
        records_format = u'csv'
        content_disposition = u'attachment; filename="{name}.csv"'.format(
                                    name=resource_id)
        content_type = b'text/csv; charset=utf-8'
    elif fmt == u'tsv':
        writer_factory = tsv_writer
        records_format = u'tsv'
        content_disposition = u'attachment; filename="{name}.tsv"'.format(
                                    name=resource_id)
        content_type = b'text/tab-separated-values; charset=utf-8'
    elif fmt == u'json':
        writer_factory = json_writer
        records_format = u'lists'
        content_disposition = u'attachment; filename="{name}.json"'.format(
                                    name=resource_id)
        content_type = b'application/json; charset=utf-8'
    elif fmt == u'xml':
        writer_factory = xml_writer
        records_format = u'objects'
        content_disposition = u'attachment; filename="{name}.xml"'.format(
                                    name=resource_id)
        content_type = b'text/xml; charset=utf-8'

    bom = options.get(u'bom', False)

    output_stream = StringIO()

    user_context = c.user

    def start_stream_writer(output_stream, fields):
        return writer_factory(output_stream, fields, bom=bom)

    def stream_result_page(offs, lim):
        return get_action(u'datastore_search')(
            {u'user': user_context},
            dict({
                u'resource_id': resource_id,
                u'limit': PAGINATE_BY
                if limit is None else min(PAGINATE_BY, lim),
                u'offset': offs,
                u'sort': sort,
                u'records_format': records_format,
                u'include_total': False,
            }, **search_params)
        )

    def stream_dump(offset, limit, paginate_by, result):
        with start_stream_writer(output_stream, result[u'fields']) as output:
            while True:
                if limit is not None and limit <= 0:
                    break

                records = result[u'records']

                output.write_records(records)
                output_stream.seek(0)
                yield output_stream.read()
                output_stream.truncate(0)
                output_stream.seek(0)

                if records_format == u'objects' or records_format == u'lists':
                    if len(records) < paginate_by:
                        break
                elif not records:
                    break

                offset += paginate_by
                if limit is not None:
                    limit -= paginate_by
                    if limit <= 0:
                        break

                result = stream_result_page(offset, limit)
        output_stream.seek(0)
        yield output_stream.read()

    try:
        result = stream_result_page(offset, limit)

        if result[u'limit'] != limit:
            # `limit` (from PAGINATE_BY) must have been more than
            # ckan.datastore.search.rows_max, so datastore_search responded with a
            # limit matching ckan.datastore.search.rows_max. So we need to paginate
            # by that amount instead, otherwise we'll have gaps in the records.
            paginate_by = result[u'limit']
        else:
            paginate_by = PAGINATE_BY

        return Response(stream_dump(offset, limit, paginate_by, result),
                        mimetype=u'application/octet-stream',
                        headers={'Content-Type': content_type,
                                'Content-disposition': content_disposition,})
    except ObjectNotFound:
        abort(404, _(u'DataStore resource not found'))


class DictionaryView(MethodView):

    def _prepare(self, id, resource_id):
        try:
            # resource_edit_base template uses these
            pkg_dict = get_action(u'package_show')({}, {'id': id})
            resource = get_action(u'resource_show')({}, {'id': resource_id})
            rec = get_action(u'datastore_info')({}, {'id': resource_id})
            return {
                u'pkg_dict': pkg_dict,
                u'resource': resource,
                u'fields': [
                    f for f in rec.get('fields', [])
                    if not f[u'id'].startswith(u'_')
                ]
            }

        except (ObjectNotFound, NotAuthorized):
            abort(404, _(u'Resource not found'))

    def get(self, id, resource_id, data=None, errors=None, error_summary=None):
        u'''Data dictionary view: show field labels and descriptions'''

        template_vars = self._prepare(id, resource_id)
        template_vars['data'] = data or {}
        template_vars['errors'] = errors or {}
        template_vars['error_summary'] = error_summary

        # global variables for backward compatibility
        c.pkg_dict = template_vars[u'pkg_dict']
        c.resource = template_vars[u'resource']

        return render('datastore/dictionary.html', template_vars)

    def post(self, id, resource_id):
        u'''Data dictionary view: edit field labels and descriptions'''
        data_dict = self._prepare(id, resource_id)
        fields = data_dict[u'fields']
        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        info = data.get(u'info')
        if not isinstance(info, list):
            info = []
        info = info[:len(fields)]
        custom = data.get('fields')
        if not isinstance(custom, list):
            custom = []

        try:
            get_action('datastore_create')(
                {}, {
                    'resource_id': resource_id,
                    'force': True,
                    'fields': [dict(
                        cu or {},
                        id=f['id'],
                        type=f['type'],
                        info=fi if isinstance(fi, dict) else {}
                    ) for f, fi, cu in zip_longest(fields, info, custom)]
                }
            )
        except ValidationError as e:
            errors = e.error_dict
            # flatten field errors for summary
            error_summary = {}
            field_errors = errors.get('fields', [])
            if isinstance(field_errors, list):
                for i, f in enumerate(field_errors, 1):
                    if isinstance(f, dict) and f:
                        error_summary[_('Field %d') % i] = ', '.join(
                            v for vals in f.values() for v in vals)
            return self.get(id, resource_id, data, errors, error_summary)

        h.flash_success(
            _(
                u'Data Dictionary saved. Any type overrides will '
                u'take effect when the resource is next uploaded '
                u'to DataStore'
            )
        )
        return h.redirect_to(
            u'datastore.dictionary', id=id, resource_id=resource_id
        )


def dump_to(
    resource_id, output, fmt, offset, limit, options, sort, search_params
):
    if fmt == u'csv':
        writer_factory = csv_writer
        records_format = u'csv'
    elif fmt == u'tsv':
        writer_factory = tsv_writer
        records_format = u'tsv'
    elif fmt == u'json':
        writer_factory = json_writer
        records_format = u'lists'
    elif fmt == u'xml':
        writer_factory = xml_writer
        records_format = u'objects'

    def start_writer(fields):
        bom = options.get(u'bom', False)
        return writer_factory(output, fields, bom)

    def result_page(offs, lim):
        return get_action(u'datastore_search')(
            None,
            dict({
                u'resource_id': resource_id,
                u'limit': PAGINATE_BY
                if limit is None else min(PAGINATE_BY, lim),
                u'offset': offs,
                u'sort': sort,
                u'records_format': records_format,
                u'include_total': False,
            }, **search_params)
        )

    result = result_page(offset, limit)

    if result[u'limit'] != limit:
        # `limit` (from PAGINATE_BY) must have been more than
        # ckan.datastore.search.rows_max, so datastore_search responded with a
        # limit matching ckan.datastore.search.rows_max. So we need to paginate
        # by that amount instead, otherwise we'll have gaps in the records.
        paginate_by = result[u'limit']
    else:
        paginate_by = PAGINATE_BY

    with start_writer(result[u'fields']) as wr:
        while True:
            if limit is not None and limit <= 0:
                break

            records = result[u'records']

            wr.write_records(records)

            if records_format == u'objects' or records_format == u'lists':
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


datastore.add_url_rule(u'/datastore/dump/<resource_id>', view_func=dump)
datastore.add_url_rule(
    u'/dataset/<id>/dictionary/<resource_id>',
    view_func=DictionaryView.as_view(str(u'dictionary'))
)
