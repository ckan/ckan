# encoding: utf-8
from __future__ import annotations

from typing import Any, Optional, cast, Union
from itertools import zip_longest

from flask import Blueprint, Response
from flask.views import MethodView

import ckan.lib.navl.dictization_functions as dict_fns
from ckan.common import current_user
from ckan.logic import (
    check_access,
    tuplize_dict,
    parse_params,
)
from ckan.plugins.toolkit import (
    ObjectNotFound, NotAuthorized, get_action, get_validator, _, request,
    abort, render, g, h, ValidationError, asbool
)
from ckan.types import Schema, ValidatorFactory
from ckanext.datastore.logic.schema import (
    list_of_strings_or_string,
    json_validator,
    unicode_or_json_validator,
)
import ckan.plugins as p
from ckanext.datastore import formats
from ckanext.datastore.interfaces import IDatastoreDump


int_validator = get_validator(u'int_validator')
boolean_validator = get_validator(u'boolean_validator')
ignore_missing = get_validator(u'ignore_missing')
one_of = cast(ValidatorFactory, get_validator(u'one_of'))
default = cast(ValidatorFactory, get_validator(u'default'))
unicode_only = get_validator(u'unicode_only')

PAGINATE_BY = 32000

datastore = Blueprint(u'datastore', __name__)


def dump_formats():
    dump_formats = [
        formats.CSV(),
        formats.TSV(),
        formats.JSON(),
        formats.XML(),
    ]
    for plugin in p.PluginImplementations(IDatastoreDump):
        dump_formats.append(plugin())
    return dump_formats


def dump_schema() -> Schema:
    return {
        u'offset': [default(0), int_validator],
        u'limit': [ignore_missing, int_validator],
        u'format': [default(u'csv'), one_of([d.get_format() for d in dump_formats()])],
        u'bom': [default(False), boolean_validator],
        u'filters': [ignore_missing, json_validator],
        u'q': [ignore_missing, unicode_or_json_validator],
        u'distinct': [ignore_missing, boolean_validator],
        u'plain': [ignore_missing, boolean_validator],
        u'language': [ignore_missing, unicode_only],
        u'fields': [ignore_missing, list_of_strings_or_string],
        u'sort': [default(u'_id'), list_of_strings_or_string],
    }


def dump(resource_id: str):
    try:
        get_action('datastore_search')({}, {'resource_id': resource_id,
                                            'limit': 0})
    except (ObjectNotFound, NotAuthorized):
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

    for d in dump_formats():
        if fmt == d.get_format():
            format_class = d
            break
    else:
        abort(404, _('Unsupported format'))

    content_disposition = 'attachment; filename="{name}.{extension}"'.format(
        name=resource_id, extension=format_class.get_file_extension())
    content_type = format_class.get_content_type()

    headers = {}
    if content_type:
        headers['Content-Type'] = content_type
    if content_disposition:
        headers['Content-disposition'] = content_disposition

    try:
        return Response(dump_to(resource_id,
                                fmt_class=format_class,
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

    def _prepare(self, id: str, resource_id: str) -> dict[str, Any]:
        try:
            check_access(
                "datastore_create",
                context={"user": current_user.name, "auth_user_obj": current_user},
                data_dict={"resource_id": resource_id},
            )

            # resource_edit_base template uses these
            pkg_dict = get_action(u'package_show')({}, {'id': id})
            resource = get_action(u'resource_show')({}, {'id': resource_id})
            rec = get_action(u'datastore_info')({}, {
                'id': resource_id,
                'include_meta': False,
                'include_fields_schema': False,
            })
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

    def get(self,
            id: str,
            resource_id: str,
            data: Optional[dict[str, Any]] = None,
            errors: Optional[dict[str, Any]] = None,
            error_summary: Optional[dict[str, Any]] = None,
            ):
        u'''Data dictionary view: show field labels and descriptions'''

        template_vars = self._prepare(id, resource_id)
        template_vars['data'] = data or {}
        template_vars['errors'] = errors or {}
        template_vars['error_summary'] = error_summary

        # global variables for backward compatibility
        g.pkg_dict = template_vars['pkg_dict']
        g.resource = template_vars['resource']

        return render('datastore/dictionary.html', template_vars)

    def post(self, id: str, resource_id: str):
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
    resource_id: str, fmt_class: IDatastoreDump, offset: int,
    limit: Optional[int], options: dict[str, Any], sort: str,
    search_params: dict[str, Any], user: str
):
    writer_factory = fmt_class.get_writer
    records_format = fmt_class.get_records_format()
    if not records_format:
        assert False, 'Unsupported format'

    bom = options.get('bom', False)

    def start_stream_writer(fields: list[dict[str, Any]]):
        return writer_factory(fields, bom=bom)

    def stream_result_page(offs: int, lim: Union[None, int]):
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

    def stream_dump(offset: int, limit: Union[None, int],
                    paginate_by: int, result: dict[str, Any]):
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


def api_info(resource_id: str):
    try:
        get_action('datastore_search')({}, {'resource_id': resource_id,
                                            'limit': 0})
    except (ObjectNotFound, NotAuthorized):
        abort(404, _('DataStore resource not found'))

    return render('datastore/snippets/api_info.html', {
        'resource_id': resource_id,
        'embedded': asbool(request.args.get('embedded', False)),
    })


datastore.add_url_rule(u'/datastore/dump/<resource_id>', view_func=dump)
datastore.add_url_rule(
    u'/dataset/<id>/dictionary/<resource_id>',
    view_func=DictionaryView.as_view(str(u'dictionary'))
)
datastore.add_url_rule('/datastore/api_info/<resource_id>', view_func=api_info)
