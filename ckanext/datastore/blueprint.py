# encoding: utf-8

from six.moves import zip_longest

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.lib.navl.dictization_functions as dict_fns
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
from ckan.plugins.toolkit import (
    ObjectNotFound, NotAuthorized, get_action, get_validator, _, request,
    abort, render, c, h, g, ValidationError
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
        # treat as ignore, as outside of Blueprint/Request context.
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
        if isinstance(value, list) and '_id' in value:
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
        get_action('datastore_search')({}, {'resource_id': resource_id,
                                            'limit': 0})
    except ObjectNotFound:
        abort(404, _('DataStore resource not found'))

    data, errors = dict_fns.validate(request.args.to_dict(), dump_schema())
    if errors:
        abort(
            400, '\n'.join(
                '{0}: {1}'.format(k, ' '.join(e)) for k, e in errors.items()
            )
        )

    fmt = data['format']
    offset = data['offset']
    limit = data.get('limit')
    options = {'bom': data['bom']}
    sort = data['sort']
    search_params = {
        k: v
        for k, v in data.items()
        if k in [
            'filters', 'q', 'distinct', 'plain', 'language',
            'fields'
        ]
    }

    user_context = g.user

    content_type = None
    content_disposition = None

    if fmt == 'csv':
        content_disposition = 'attachment; filename="{name}.csv"'.format(
                                    name=resource_id)
        content_type = b'text/csv; charset=utf-8'
    elif fmt == 'tsv':
        content_disposition = 'attachment; filename="{name}.tsv"'.format(
                                    name=resource_id)
        content_type = b'text/tab-separated-values; charset=utf-8'
    elif fmt == 'json':
        content_disposition = 'attachment; filename="{name}.json"'.format(
                                    name=resource_id)
        content_type = b'application/json; charset=utf-8'
    elif fmt == 'xml':
        content_disposition = 'attachment; filename="{name}.xml"'.format(
                                    name=resource_id)
        content_type = b'text/xml; charset=utf-8'
    else:
        abort(404, _('Unsupported format'))

    headers = {}
    if content_type:
        headers['Content-Type'] = content_type
    if content_disposition:
        headers['Content-disposition'] = content_disposition

    try:
        return Response(dump_to(resource_id,
                                fmt=fmt,
                                offset=offset,
                                limit=limit,
                                options=options,
                                sort=sort,
                                search_params=search_params,
                                user=user_context),
                        mimetype='application/octet-stream',
                        headers=headers)
    except ObjectNotFound:
        abort(404, _('DataStore resource not found'))


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
    resource_id, fmt, offset, limit, options, sort, search_params, user
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
    else:
        assert False, 'Unsupported format'

    bom = options.get('bom', False)

    def start_stream_writer(fields):
        return writer_factory(fields, bom=bom)

    def stream_result_page(offs, lim):
        return get_action('datastore_search')(
            {'user': user},
            dict({
                'resource_id': resource_id,
                'limit': PAGINATE_BY
                if limit is None else min(PAGINATE_BY, lim),  # type: ignore
                'offset': offs,
                'sort': sort,
                'records_format': records_format,
                'include_total': False,
            }, **search_params)
        )

    def stream_dump(offset, limit, paginate_by, result):
        with start_stream_writer(result['fields']) as writer:
            while True:
                if limit is not None and limit <= 0:
                    break

                records = result['records']

                yield writer.write_records(records)

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

                result = stream_result_page(offset, limit)

            yield writer.end_file()

    result = stream_result_page(offset, limit)

    if result['limit'] != limit:
        # `limit` (from PAGINATE_BY) must have been more than
        # ckan.datastore.search.rows_max, so datastore_search responded
        # with a limit matching ckan.datastore.search.rows_max.
        # So we need to paginate by that amount instead, otherwise
        # we'll have gaps in the records.
        paginate_by = result['limit']
    else:
        paginate_by = PAGINATE_BY

    return stream_dump(offset, limit, paginate_by, result)


datastore.add_url_rule(u'/datastore/dump/<resource_id>', view_func=dump)
datastore.add_url_rule(
    u'/dataset/<id>/dictionary/<resource_id>',
    view_func=DictionaryView.as_view(str(u'dictionary'))
)
