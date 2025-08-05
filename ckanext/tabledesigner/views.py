# encoding: utf-8
from __future__ import annotations

from typing import cast, List
from itertools import zip_longest

from flask import Blueprint
from flask.views import MethodView

from ckanext.datastore.blueprint import DictionaryView
import ckan.lib.navl.dictization_functions as dict_fns
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
from ckan.lib import base
from ckan.logic import NotAuthorized
from ckan.plugins.toolkit import (
    get_action,
    h,
    _,
    request,
    render,
    ValidationError,
)

from ckanext.tabledesigner.datastore import create_table

tabledesigner = Blueprint(u'tabledesigner', __name__)


class _TableDesignerDictionary(MethodView):
    def post(self, id: str, resource_id: str):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)

        if data_dict['resource']['url_type'] != 'tabledesigner':
            # avoid second _prepare call
            _datastore_view._prepare = lambda id, resource_id: data_dict
            return _datastore_view.post(id, resource_id)

        fields = data_dict['fields']
        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        info = data.get('info')
        if not isinstance(info, list):
            info = []
        custom = data.get('fields')
        if not isinstance(custom, list):
            return base.abort(400, _('Required fields missing'))
        info = info[:len(custom)]

        flookup = {f['id']: f for f in fields}
        new_fields = []

        for c, fi in zip_longest(custom, info):
            if not c.get('tdtype'):
                return base.abort(400, _('Required fields missing'))
            datastore_type = h.tabledesigner_column_type(c).datastore_type
            if 'id' in c:
                f = flookup.get(c['id'])
                if f:
                    datastore_type = f['type']
            new_fields.append(dict(c, type=datastore_type, info=fi))

        try:
            create_table({}, resource_id, new_fields)
        except ValidationError as e:
            fields = {f['id']: f for f in data_dict['fields']}
            data_dict['fields'] = [
                dict(
                    fields.get(d['id'], {}),
                    info=d,
                ) for d in data['fields']
            ]
            errors = e.error_dict
            field_errors = errors.get('fields')
            if not field_errors or not isinstance(field_errors, list):
                raise

            if field_errors and not isinstance(field_errors[0], dict):
                error_summary = {'id': ', '.join(
                    cast(List[str], field_errors)
                )}
            else:
                error_summary = {}
                for i, f in enumerate(field_errors, 1):
                    if isinstance(f, dict) and f:
                        error_summary[_('Field %d') % i] = ', '.join(
                            v for vals in f.values()
                            for v in vals)
            return _datastore_view.get(
                id, resource_id, data, errors, error_summary)

        h.flash_success(_('Table Designer fields updated.'))
        return h.redirect_to(
            data_dict['pkg_dict']['type'] + '_resource.read',
            id=id,
            resource_id=resource_id
        )


tabledesigner.add_url_rule(
    '/dataset/<id>/dictionary/<resource_id>',
    view_func=_TableDesignerDictionary.as_view('tabledesigner'),
)


class _TableDesignerAddRow(MethodView):
    def get(self, id: str, resource_id: str):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)
        return render(
            'tabledesigner/add_row.html', dict(data_dict, errors={}, row={})
        )

    def post(self, id: str, resource_id: str):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)

        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        col = data.get('col', [])
        row = {}
        for f, c in zip(data_dict['fields'], col):
            row[f['id']] = c['value']

        try:
            get_action('datastore_upsert')(
                {},
                {
                    'resource_id': resource_id,
                    'method': 'insert',
                    'records': [row],
                }
            )
        except ValidationError as err:
            rec_err = cast(List[str], err.error_dict.get('records', ['']))[0]
            if rec_err.startswith('duplicate key'):
                info = get_action('datastore_info')({}, {'id': resource_id})
                pk_fields = [
                    f['id'] for f in info['fields']
                    if f.get('tdpkreq') == 'pk'
                ]
                errors = {
                    k: [_('Duplicate primary key exists')] for k in pk_fields
                }
            elif rec_err.startswith('invalid input syntax'):
                bad_data = rec_err.split('"', 1)[1].rstrip('"')
                errors = {
                    f: [_("Invalid input")] for f in row if row[f] == bad_data
                }
            elif rec_err.startswith('TAB-DELIMITED\t'):
                errors = {}
                erriter = iter(rec_err.split('\t')[1:])
                for field, err in zip(erriter, erriter):
                    errors.setdefault(field, []).append(err)
            else:
                raise
            return render(
                'tabledesigner/add_row.html',
                dict(data_dict, row=row, errors=errors),
            )
        return h.redirect_to(
            data_dict['pkg_dict']['type'] + '_resource.read',
            id=id,
            resource_id=resource_id
        )


tabledesigner.add_url_rule(
    '/dataset/<id>/tabledesigner/<resource_id>/add-row',
    view_func=_TableDesignerAddRow.as_view('add_row'),
)


class _TableDesignerEditRow(MethodView):
    def get(self, id: str, resource_id: str):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)
        _id = request.args['_id']

        try:
            r = get_action('datastore_search')(
                {},
                {
                    'resource_id': resource_id,
                    'filters': {'_id': _id},
                }
            )
        except NotAuthorized:
            return base.abort(403, _('Not authorized to see this page'))
        if not r['records']:
            return base.abort(404, _('Row not found'))
        data_dict['row'] = r['records'][0]
        data_dict['errors'] = {}
        return render('tabledesigner/edit_row.html', data_dict)

    def post(self, id: str, resource_id: str):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)
        _id = request.args['_id']

        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        col = data.get('col', [])
        row = {'_id': _id}
        for f, c in zip(data_dict['fields'], col):
            row[f['id']] = c['value']

        try:
            get_action('datastore_upsert')(
                {},
                {
                    'resource_id': resource_id,
                    'method': 'update',
                    'records': [row],
                }
            )
        except ValidationError as err:
            rec_err = cast(List[str], err.error_dict.get('records', ['']))[0]
            if rec_err.startswith('duplicate key'):
                info = get_action('datastore_info')({}, {'id': resource_id})
                pk_fields = [
                    f['id'] for f in info['fields']
                    if f.get('tdpkreq') == 'pk'
                ]
                errors = {
                    k: [_('Duplicate primary key exists')] for k in pk_fields
                }
            elif rec_err.startswith('invalid input syntax'):
                bad_data = rec_err.split('"', 1)[1].rstrip('"')
                errors = {
                    f: [_("Invalid input")] for f in row if row[f] == bad_data
                }
            elif rec_err.startswith('TAB-DELIMITED\t'):
                errors = {}
                erriter = iter(rec_err.split('\t')[1:])
                for field, err in zip(erriter, erriter):
                    errors.setdefault(field, []).append(err)
            else:
                raise
            return render(
                'tabledesigner/edit_row.html',
                dict(data_dict, row=row, errors=errors),
            )
        return h.redirect_to(
            data_dict['pkg_dict']['type'] + '_resource.read',
            id=id,
            resource_id=resource_id
        )


tabledesigner.add_url_rule(
    '/dataset/<id>/tabledesigner/<resource_id>/edit-row',
    view_func=_TableDesignerEditRow.as_view('edit_row'),
)


class _TableDesignerDeleteRows(MethodView):
    def get(self, id: str, resource_id: str):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)
        _ids = request.args.getlist('_id')

        try:
            r = get_action('datastore_search')(
                {}, {
                    'resource_id': resource_id,
                    'filters': {'_id': _ids},
                }
            )
        except NotAuthorized:
            return base.abort(403, _('Not authorized to see this page'))
        if len(r['records']) != len(_ids):
            return base.abort(404, _('Row(s) not found'))
        data_dict['records'] = r['records']
        return render('tabledesigner/delete_rows.html', data_dict)

    def post(self, id: str, resource_id: str):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)
        _ids = request.args.getlist('_id')

        try:
            get_action('datastore_delete')(
                {}, {
                    'resource_id': resource_id,
                    'filters': {'_id': _ids},
                }
            )
        except NotAuthorized:
            return base.abort(403, _('Not authorized to see this page'))
        return h.redirect_to(
            data_dict['pkg_dict']['type'] + '_resource.read',
            id=id,
            resource_id=resource_id
        )


tabledesigner.add_url_rule(
    '/dataset/<id>/tabledesigner/<resource_id>/delete-rows',
    view_func=_TableDesignerDeleteRows.as_view('delete_rows'),
)
