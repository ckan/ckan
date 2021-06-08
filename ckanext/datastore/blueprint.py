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

int_validator = get_validator(u'int_validator')
boolean_validator = get_validator(u'boolean_validator')
ignore_missing = get_validator(u'ignore_missing')
one_of = get_validator(u'one_of')
default = get_validator(u'default')
unicode_only = get_validator(u'unicode_only')

DUMP_FORMATS = u'csv', u'tsv', u'json', u'xml'
PAGINATE_BY = 32000

datastore = Blueprint(u'datastore', __name__)


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
        u'fields': [ignore_missing, list_of_strings_or_string],
        u'sort': [default(u'_id'), list_of_strings_or_string],
    }


def dump(resource_id):
    data, errors = dict_fns.validate(request.args.to_dict(), dump_schema())
    if errors:
        abort(
            400, u'\n'.join(
                u'{0}: {1}'.format(k, u' '.join(e)) for k, e in errors.items()
            )
        )

    response = make_response()
    response.headers[u'content-type'] = u'application/octet-stream'

    try:
        dump_to(
            resource_id,
            response,
            fmt=data[u'format'],
            offset=data[u'offset'],
            limit=data.get(u'limit'),
            options={u'bom': data[u'bom']},
            sort=data[u'sort'],
            search_params={
                k: v
                for k, v in data.items()
                if k in [
                    u'filters', u'q', u'distinct', u'plain', u'language',
                    u'fields'
                ]
            },
        )
    except ObjectNotFound:
        abort(404, _(u'DataStore resource not found'))
    return response


class DictionaryView(MethodView):

    def _prepare(self, id, resource_id):
        try:
            # resource_edit_base template uses these
            pkg_dict = get_action(u'package_show')(None, {u'id': id})
            resource = get_action(u'resource_show')(None, {u'id': resource_id})
            rec = get_action(u'datastore_search')(
                None, {
                    u'resource_id': resource_id,
                    u'limit': 0
                }
            )
            return {
                u'pkg_dict': pkg_dict,
                u'resource': resource,
                u'fields': [
                    f for f in rec[u'fields'] if not f[u'id'].startswith(u'_')
                ]
            }

        except (ObjectNotFound, NotAuthorized):
            abort(404, _(u'Resource not found'))

    def get(self, id, resource_id):
        u'''Data dictionary view: show field labels and descriptions'''

        data_dict = self._prepare(id, resource_id)

        # global variables for backward compatibility
        c.pkg_dict = data_dict[u'pkg_dict']
        c.resource = data_dict[u'resource']

        return render(u'datastore/dictionary.html', data_dict)

    def post(self, id, resource_id):
        u'''Data dictionary view: edit field labels and descriptions'''
        data_dict = self._prepare(id, resource_id)
        fields = data_dict[u'fields']
        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        info = data.get(u'info')
        if not isinstance(info, list):
            info = []
        info = info[:len(fields)]

        get_action(u'datastore_create')(
            None, {
                u'resource_id': resource_id,
                u'force': True,
                u'fields': [{
                    u'id': f[u'id'],
                    u'type': f[u'type'],
                    u'info': fi if isinstance(fi, dict) else {}
                } for f, fi in zip_longest(fields, info)]
            }
        )

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
        return writer_factory(output, fields, resource_id, bom)

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
