# encoding: utf-8
import logging

from flask import Blueprint

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, g, request
from ckan.views.user import _extra_template_variables

log = logging.getLogger(__name__)

dashboard = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dashboard.before_request
def before_request():
    if not g.userobj:
        h.flash_error(_('Not authorized to see this page'))
        return h.redirect_to('user.login')

    try:
        context = dict(model=model, user=g.user, auth_user_obj=g.userobj)
        logic.check_access('site_read', context)
    except logic.NotAuthorized:
        base.abort(403, _('Not authorized to see this page'))


def _get_dashboard_context(filter_type=None, filter_id=None, q=None):
    '''Return a dict needed by the dashboard view to determine context.'''

    def display_name(followee):
        '''Return a display name for a user, group or dataset dict.'''
        display_name = followee.get('display_name')
        fullname = followee.get('fullname')
        title = followee.get('title')
        name = followee.get('name')
        return display_name or fullname or title or name

    if (filter_type and filter_id):
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj,
            'for_view': True
        }
        data_dict = {'id': filter_id, 'include_num_followers': True}
        followee = None

        action_functions = {
            'dataset': 'package_show',
            'user': 'user_show',
            'group': 'group_show',
            'organization': 'organization_show',
        }
        action_function = logic.get_action(action_functions.get(filter_type))
        # Is this a valid type?
        if action_function is None:
            base.abort(404, _('Follow item not found'))
        try:
            followee = action_function(context, data_dict)
        except (logic.NotFound, logic.NotAuthorized):
            base.abort(404, _('{0} not found').format(filter_type))

        if followee is not None:
            return {
                'filter_type': filter_type,
                'q': q,
                'context': display_name(followee),
                'selected_id': followee.get('id'),
                'dict': followee,
            }

    return {
        'filter_type': filter_type,
        'q': q,
        'context': _('Everything'),
        'selected_id': False,
        'dict': None,
    }


def index(offset=0):
    context = {
        'model': model,
        'session': model.Session,
        'user': g.user,
        'auth_user_obj': g.userobj,
        'for_view': True
    }
    data_dict = {'user_obj': g.userobj, 'offset': offset}
    extra_vars = _extra_template_variables(context, data_dict)

    q = request.params.get('q', '')
    filter_type = request.params.get('type', '')
    filter_id = request.params.get('name', '')

    extra_vars['followee_list'] = logic.get_action('followee_list')(
        context, {
            'id': g.userobj.id,
            'q': q
        })
    extra_vars['dashboard_activity_stream_context'] = _get_dashboard_context(
        filter_type, filter_id, q)
    extra_vars['dashboard_activity_stream'] = h.dashboard_activity_stream(
        g.userobj.id, filter_type, filter_id, offset)

    # Mark the user's new activities as old whenever they view their
    # dashboard page.
    logic.get_action('dashboard_mark_activities_old')(context, {})

    return base.render('user/dashboard.html', extra_vars)


def datasets():
    context = {'for_view': True, 'user': g.user, 'auth_user_obj': g.userobj}
    data_dict = {'user_obj': g.userobj, 'include_datasets': True}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render('user/dashboard_datasets.html', extra_vars)


def organizations():
    context = {'for_view': True, 'user': g.user, 'auth_user_obj': g.userobj}
    data_dict = {'user_obj': g.userobj}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render('user/dashboard_organizations.html', extra_vars)


def groups():
    context = {'for_view': True, 'user': g.user, 'auth_user_obj': g.userobj}
    data_dict = {'user_obj': g.userobj}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render('user/dashboard_groups.html', extra_vars)


dashboard.add_url_rule(
    '/', view_func=index, strict_slashes=False, defaults={
        'offset': 0
    })
dashboard.add_url_rule('/<int:offset>', view_func=index)

dashboard.add_url_rule('/datasets', view_func=datasets)
dashboard.add_url_rule('/groups', view_func=groups)
dashboard.add_url_rule('/organizations', view_func=organizations)
