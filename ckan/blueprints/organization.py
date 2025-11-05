# encoding: utf-8

"""Organization blueprint - replaces ckan.controllers.organization"""

from flask import Blueprint, render_template, request, redirect, url_for, g, abort
import ckan.logic as logic
import ckan.model as model

organization = Blueprint('organization', __name__)


@organization.route('/')
def index():
    """List all organizations"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        organizations = logic.get_action('organization_list')(
            context, {'all_fields': True, 'include_extras': True}
        )
        return render_template('organization/index.html', organizations=organizations)
    except logic.NotAuthorized:
        abort(403)


@organization.route('/list')
def list():
    """Alternative list view"""
    return index()


@organization.route('/new', methods=['GET', 'POST'])
def new():
    """Create new organization"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None),
               'save': 'save' in request.form}

    try:
        logic.check_access('organization_create', context)
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        try:
            data_dict = dict(request.form.items())
            org_dict = logic.get_action('organization_create')(context, data_dict)
            return redirect(url_for('organization.read', id=org_dict['name']))
        except logic.ValidationError as e:
            errors = e.error_dict
            return render_template('organization/new.html',
                                 data=request.form,
                                 errors=errors)

    return render_template('organization/new.html', data={}, errors={})


@organization.route('/<id>')
def read(id):
    """View organization"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        org_dict = logic.get_action('organization_show')(context, {'id': id})
        # Get organization's packages
        packages = logic.get_action('package_search')(
            context, {'fq': 'owner_org:' + org_dict['id'], 'rows': 20}
        )
        return render_template('organization/read.html',
                             organization=org_dict,
                             packages=packages['results'])
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)


@organization.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    """Edit organization"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None),
               'save': 'save' in request.form}

    try:
        logic.check_access('organization_update', context, {'id': id})
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        try:
            data_dict = dict(request.form.items())
            data_dict['id'] = id
            org_dict = logic.get_action('organization_update')(context, data_dict)
            return redirect(url_for('organization.read', id=org_dict['name']))
        except logic.ValidationError as e:
            org_dict = logic.get_action('organization_show')(context, {'id': id})
            errors = e.error_dict
            return render_template('organization/edit.html',
                                 organization=org_dict,
                                 data=request.form,
                                 errors=errors)

    org_dict = logic.get_action('organization_show')(context, {'id': id})
    return render_template('organization/edit.html',
                         organization=org_dict,
                         data=org_dict,
                         errors={})


@organization.route('/delete/<id>', methods=['POST'])
def delete(id):
    """Delete organization"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        logic.get_action('organization_delete')(context, {'id': id})
        return redirect(url_for('organization.index'))
    except logic.NotAuthorized:
        abort(403)
    except logic.NotFound:
        abort(404)


@organization.route('/about/<id>')
def about(id):
    """About organization page"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        org_dict = logic.get_action('organization_show')(context, {'id': id})
        return render_template('organization/about.html', organization=org_dict)
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)
