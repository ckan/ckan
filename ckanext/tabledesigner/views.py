from flask import Blueprint, make_response
from flask.views import MethodView

from ckanext.datastore.blueprint import DictionaryView
import ckan.lib.navl.dictization_functions as dict_fns
from ckan.logic import (
    tuplize_dict,
    parse_params,
)
from ckan.plugins.toolkit import (
    get_action,
    h,
    _,
    request,
    render,
)

tabledesigner = Blueprint(u'tabledesigner', __name__)

class _TableDesignerDictionary(MethodView):
    def post(self, id, resource_id):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)

        if data_dict['resource']['url_type'] != 'tabledesigner':
            # avoid second _prepare call
            _datastore_view._prepare = lambda _i, _r: data_dict
            return _datastore_view.post(id, resource_id)

        fields = data_dict['fields']
        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        info = data.get('info')
        if not isinstance(info, list):
            info = []

        for e, f in zip(info, fields):
            e['id'] = f['id']
            e['type'] = f['type']

        primary_key = [f['id'] for f in info if f.get('pk')]

        get_action('datastore_create')(
            None, {
                'resource_id': resource_id,
                'force': True,
                'primary_key': primary_key,
                'fields': [{
                    'id': i['id'],
                    'type': i['type'],
                    'info': {
                        k:v for (k, v) in i.items()
                        if k != 'id' and k != 'type'
                    },
                } for i in info]
            }
        )
        h.flash_success(_('Table Designer fields updated.'))
        return h.redirect_to(
            'datastore.dictionary', id=id, resource_id=resource_id
        )


tabledesigner.add_url_rule(
    '/dataset/<id>/dictionary/<resource_id>',
    view_func=_TableDesignerDictionary.as_view('tabledesigner'),
)


class _TableDesignerAddRow(MethodView):
    def post(self, id, resource_id):
        pass

    def get(self, id, resource_id):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)
        return render('tabledesigner/add_row.html', data_dict)

    def post(self, id, resource_id):
        _datastore_view = DictionaryView()
        data_dict = _datastore_view._prepare(id, resource_id)

        data = dict_fns.unflatten(tuplize_dict(parse_params(request.form)))
        col = data.get('col', [])
        row = {}
        for f, c in zip(data_dict['fields'], col):
            row[f['id']] = c['value'] or None

        get_action('datastore_upsert')(
            None, {
                'resource_id': resource_id,
                'method': 'insert',
                'force': True,  # FIXME: don't require this for tabledesigner tables
                'records': [row],
            }
        )
        return h.redirect_to(data_dict['pkg_dict']['type'] + '_resource.read', id=id, resource_id=resource_id)


tabledesigner.add_url_rule(
    '/dataset/<id>/tabledesigner/<resource_id>/add-row',
    view_func=_TableDesignerAddRow.as_view('add_row'),
)
