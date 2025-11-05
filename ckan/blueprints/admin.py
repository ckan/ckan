# encoding: utf-8

"""Admin blueprint - replaces ckan.controllers.admin"""

from flask import Blueprint, render_template, request, redirect, url_for, g, abort
import ckan.logic as logic
import ckan.model as model
from ckan.common import config

admin = Blueprint('admin', __name__)


@admin.route('/')
def index():
    """Admin dashboard"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        logic.check_access('sysadmin', context)
    except logic.NotAuthorized:
        abort(403)

    return render_template('admin/index.html')


@admin.route('/config', methods=['GET', 'POST'])
def config_page():
    """Configuration page"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        logic.check_access('sysadmin', context)
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        # Handle configuration updates
        # This would update the config database table
        return redirect(url_for('admin.index'))

    return render_template('admin/config.html', config=config)


@admin.route('/trash')
def trash():
    """View deleted items"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        logic.check_access('sysadmin', context)
    except logic.NotAuthorized:
        abort(403)

    # Get deleted packages
    deleted_packages = model.Session.query(model.Package).filter(
        model.Package.state == 'deleted'
    ).all()

    return render_template('admin/trash.html',
                         deleted_packages=deleted_packages)
