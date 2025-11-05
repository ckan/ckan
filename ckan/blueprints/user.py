# encoding: utf-8

"""User blueprint - replaces ckan.controllers.user"""

from flask import Blueprint, render_template, request, redirect, url_for, g, session, abort
import ckan.logic as logic
import ckan.model as model
import ckan.lib.helpers as h

user = Blueprint('user', __name__)


@user.route('/')
def index():
    """List all users"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        users = logic.get_action('user_list')(context, {})
        return render_template('user/list.html', users=users)
    except logic.NotAuthorized:
        abort(403)


@user.route('/<id>')
def read(id):
    """View user profile"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        user_dict = logic.get_action('user_show')(context, {'id': id})
        return render_template('user/read.html', user_dict=user_dict)
    except logic.NotFound:
        abort(404)
    except logic.NotAuthorized:
        abort(403)


@user.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if g.user:
        return redirect(url_for('home.index'))

    if request.method == 'POST':
        context = {'model': model, 'session': model.Session, 'user': None}
        try:
            data_dict = dict(request.form.items())
            user_dict = logic.get_action('user_create')(context, data_dict)
            # Log the user in
            session['user'] = user_dict['name']
            return redirect(url_for('home.index'))
        except logic.ValidationError as e:
            errors = e.error_dict
            return render_template('user/new.html',
                                 data=request.form,
                                 errors=errors)

    return render_template('user/new.html', data={}, errors={})


@user.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if g.user:
        return redirect(url_for('home.index'))

    if request.method == 'POST':
        login_name = request.form.get('login')
        password = request.form.get('password')

        # Try to authenticate
        user_obj = model.User.by_name(login_name)
        if not user_obj:
            user_obj = model.User.by_email(login_name)

        if user_obj and user_obj.validate_password(password):
            session['user'] = user_obj.name
            return redirect(url_for('home.index'))
        else:
            return render_template('user/login.html',
                                 error='Invalid username or password')

    return render_template('user/login.html', error=None)


@user.route('/_logout', methods=['POST'])
def logout():
    """User logout"""
    session.pop('user', None)
    g.user = None
    g.userobj = None
    return redirect(url_for('home.index'))


@user.route('/edit', methods=['GET', 'POST'])
@user.route('/edit/<id>', methods=['GET', 'POST'])
def edit(id=None):
    """Edit user profile"""
    if not id:
        if not g.user:
            abort(403)
        id = g.user

    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None),
               'save': 'save' in request.form}

    try:
        logic.check_access('user_update', context, {'id': id})
    except logic.NotAuthorized:
        abort(403)

    if request.method == 'POST':
        try:
            data_dict = dict(request.form.items())
            data_dict['id'] = id
            user_dict = logic.get_action('user_update')(context, data_dict)
            return redirect(url_for('user.read', id=user_dict['name']))
        except logic.ValidationError as e:
            user_dict = logic.get_action('user_show')(context, {'id': id})
            errors = e.error_dict
            return render_template('user/edit.html',
                                 user_dict=user_dict,
                                 data=request.form,
                                 errors=errors)

    user_dict = logic.get_action('user_show')(context, {'id': id})
    return render_template('user/edit.html', user_dict=user_dict, data=user_dict, errors={})


@user.route('/delete/<id>', methods=['POST'])
def delete(id):
    """Delete user"""
    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        logic.get_action('user_delete')(context, {'id': id})
        if g.user == id:
            session.pop('user', None)
            g.user = None
            g.userobj = None
        return redirect(url_for('home.index'))
    except logic.NotAuthorized:
        abort(403)
    except logic.NotFound:
        abort(404)


@user.route('/dashboard')
def dashboard():
    """User dashboard"""
    if not g.user:
        abort(403)

    context = {'model': model, 'session': model.Session,
               'user': g.user, 'auth_user_obj': getattr(g, 'userobj', None)}

    try:
        user_dict = logic.get_action('user_show')(context, {'id': g.user})
        # Get user's datasets
        datasets = logic.get_action('package_search')(
            context, {'q': 'creator_user_id:' + user_dict['id'], 'rows': 50}
        )
        return render_template('user/dashboard.html',
                             user_dict=user_dict,
                             datasets=datasets['results'])
    except Exception as e:
        abort(500)
