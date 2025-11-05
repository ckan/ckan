# encoding: utf-8

"""Group blueprint - replaces ckan.controllers.group"""

from flask import Blueprint, render_template, request, redirect, url_for, g, abort
import ckan.logic as logic
import ckan.model as model

group = Blueprint('group', __name__)


@group.route('/')
def index():
    """List all groups"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        groups = logic.get_action('group_list')(
            context, {'all_fields': True, 'include_extras': True}
        )
        return render_template('group/index.html', groups=groups)
    except logic.NotAuthorized:
        abort(403)


@group.route('/list')
def list():
    """Alternative list view"""
    return index()


@group.route('/new', methods=['GET', 'POST'])
def new():
    """Create new group"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None),
               'save': 'save' in request.form}

    try:
        logic.check_access('group_create', context)
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        try:
            data_dict = dict(request.form.items())
            group_dict = logic.get_action('group_create')(context, data_dict)
            return redirect(url_for('group.read', id=group_dict['name']))
        except logic.ValidationError as e:
            errors = e.error_dict
            return render_template('group/new.html',
                                 data=request.form,
                                 errors=errors)

    return render_template('group/new.html', data={}, errors={})


@group.route('/<id>')
def read(id):
    """View group"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        group_dict = logic.get_action('group_show')(context, {'id': id})
        # Get group's packages
        packages = logic.get_action('group_package_show')(
            context, {'id': id, 'limit': 20}
        )
        return render_template('group/read.html',
                             group_dict=group_dict,
                             packages=packages)
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)


@group.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id):
    """Edit group"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None),
               'save': 'save' in request.form}

    try:
        logic.check_access('group_update', context, {'id': id})
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        try:
            data_dict = dict(request.form.items())
            data_dict['id'] = id
            group_dict = logic.get_action('group_update')(context, data_dict)
            return redirect(url_for('group.read', id=group_dict['name']))
        except logic.ValidationError as e:
            group_dict = logic.get_action('group_show')(context, {'id': id})
            errors = e.error_dict
            return render_template('group/edit.html',
                                 group_dict=group_dict,
                                 data=request.form,
                                 errors=errors)

    group_dict = logic.get_action('group_show')(context, {'id': id})
    return render_template('group/edit.html',
                         group_dict=group_dict,
                         data=group_dict,
                         errors={})


@group.route('/delete/<id>', methods=['POST'])
def delete(id):
    """Delete group"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        logic.get_action('group_delete')(context, {'id': id})
        return redirect(url_for('group.index'))
    except logic.NotAuthorized:
        abort(403)
    except logic.NotFound:
        abort(404)


@group.route('/about/<id>')
def about(id):
    """About group page"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        group_dict = logic.get_action('group_show')(context, {'id': id})
        return render_template('group/about.html', group_dict=group_dict)
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)
