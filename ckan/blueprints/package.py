# encoding: utf-8

"""Package (Dataset) blueprint - replaces ckan.controllers.package"""

from flask import Blueprint, render_template, request, redirect, url_for, g, abort
import ckan.logic as logic
import ckan.model as model
import ckan.lib.helpers as h

package = Blueprint('package', __name__)


@package.route('/')
@package.route('/search')
def search():
    """Search datasets"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    q = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    sort = request.args.get('sort', 'metadata_modified desc')

    data_dict = {
        'q': q,
        'rows': limit,
        'start': (page - 1) * limit,
        'sort': sort,
        'fq': request.args.get('fq', '')
    }

    try:
        query = logic.get_action('package_search')(context, data_dict)
        return render_template('package/search.html',
                             q=q,
                             count=query['count'],
                             results=query['results'],
                             page=page,
                             search_facets=query.get('search_facets', {}))
    except logic.NotAuthorized:
        abort(403)
    except Exception as e:
        abort(500)


@package.route('/new', methods=['GET', 'POST'])
def new():
    """Create new dataset"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None),
               'save': 'save' in request.form}

    try:
        logic.check_access('package_create', context)
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        try:
            data_dict = dict(request.form.items())
            pkg = logic.get_action('package_create')(context, data_dict)
            return redirect(url_for('package.read', id=pkg['name']))
        except logic.ValidationError as e:
            errors = e.error_dict
            return render_template('package/new.html',
                                 data=request.form,
                                 errors=errors)

    return render_template('package/new.html', data={}, errors={})


@package.route('/<id>')
def read(id):
    """Read/view dataset"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        pkg_dict = logic.get_action('package_show')(context, {'id': id})
        return render_template('package/read.html', pkg=pkg_dict)
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)


@package.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    """Edit dataset"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None),
               'save': 'save' in request.form}

    try:
        logic.check_access('package_update', context, {'id': id})
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        try:
            data_dict = dict(request.form.items())
            data_dict['id'] = id
            pkg = logic.get_action('package_update')(context, data_dict)
            return redirect(url_for('package.read', id=pkg['name']))
        except logic.ValidationError as e:
            pkg_dict = logic.get_action('package_show')(context, {'id': id})
            errors = e.error_dict
            return render_template('package/edit.html',
                                 pkg=pkg_dict,
                                 data=request.form,
                                 errors=errors)

    pkg_dict = logic.get_action('package_show')(context, {'id': id})
    return render_template('package/edit.html', pkg=pkg_dict, data=pkg_dict, errors={})


@package.route('/delete/<id>', methods=['POST'])
def delete(id):
    """Delete dataset"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        logic.get_action('package_delete')(context, {'id': id})
        return redirect(url_for('package.search'))
    except logic.NotAuthorized:
        abort(403)
    except logic.NotFound:
        abort(404)


@package.route('/<id>/resource/<resource_id>')
def resource_read(id, resource_id):
    """View resource"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        resource = logic.get_action('resource_show')(context, {'id': resource_id})
        pkg_dict = logic.get_action('package_show')(context, {'id': id})
        return render_template('package/resource_read.html',
                             pkg=pkg_dict,
                             resource=resource)
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)


@package.route('/<id>/resource/<resource_id>/download')
@package.route('/<id>/resource/<resource_id>/download/<filename>')
def resource_download(id, resource_id, filename=None):
    """Download resource"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        resource = logic.get_action('resource_show')(context, {'id': resource_id})
        # Redirect to the actual resource URL
        return redirect(resource['url'])
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)
