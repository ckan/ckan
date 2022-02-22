# encoding: utf-8
from __future__ import annotations

import logging
from typing import Any, Optional, cast

from flask import Blueprint

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, g, request
from ckan.views.user import _extra_template_variables
from ckan.types import Context

log = logging.getLogger(__name__)

dashboard = Blueprint(u'dashboard', __name__, url_prefix=u'/dashboard')


@dashboard.before_request
def before_request() -> None:
    if not g.userobj:
        h.flash_error(_(u'Not authorized to see this page'))

        # flask types do not mention that it's possible to return a response
        # from the `before_request` callback
        return h.redirect_to(u'user.login')  # type: ignore

    try:
        context = cast(Context, {
            "model": model, "user": g.user, "auth_user_obj": g.userobj
        })
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))
    return None


def _get_dashboard_context(
        filter_type: Optional[str] = None,
        filter_id: Optional[str] = None,
        q: Optional[str] = None) -> dict[str, Any]:
    u'''Return a dict needed by the dashboard view to determine context.'''

    def display_name(followee: dict[str, Any]) -> Optional[str]:
        u'''Return a display name for a user, group or dataset dict.'''
        display_name = followee.get(u'display_name')
        fullname = followee.get(u'fullname')
        title = followee.get(u'title')
        name = followee.get(u'name')
        return display_name or fullname or title or name

    if (filter_type and filter_id):
        context = cast(Context, {
            u'model': model,
            u'session': model.Session,
            u'user': g.user,
            u'auth_user_obj': g.userobj,
            u'for_view': True
        })
        data_dict: dict[str, Any] = {
            u'id': filter_id,
            u'include_num_followers': True}
        followee = None

        action_functions = {
            u'dataset': u'package_show',
            u'user': u'user_show',
            u'group': u'group_show',
            u'organization': u'organization_show',
        }
        action_name = action_functions.get(filter_type)
        if action_name is None:
            base.abort(404, _(u'Follow item not found'))

        action_function = logic.get_action(action_name)
        try:
            followee = action_function(context, data_dict)
        except (logic.NotFound, logic.NotAuthorized):
            base.abort(404, _(u'{0} not found').format(filter_type))

        if followee is not None:
            return {
                u'filter_type': filter_type,
                u'q': q,
                u'context': display_name(followee),
                u'selected_id': followee.get(u'id'),
                u'dict': followee,
            }

    return {
        u'filter_type': filter_type,
        u'q': q,
        u'context': _(u'Everything'),
        u'selected_id': False,
        u'dict': None,
    }


def index(offset: int = 0) -> str:
    context = cast(Context, {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'auth_user_obj': g.userobj,
        u'for_view': True
    })
    data_dict: dict[str, Any] = {
        u'user_obj': g.userobj,
        u'offset': offset}
    extra_vars = _extra_template_variables(context, data_dict)

    q = request.args.get(u'q', u'')
    filter_type = request.args.get(u'type', u'')
    filter_id = request.args.get(u'name', u'')

    extra_vars[u'followee_list'] = logic.get_action(u'followee_list')(
        context, {
            u'id': g.userobj.id,
            u'q': q
        })
    extra_vars[u'dashboard_activity_stream_context'] = _get_dashboard_context(
        filter_type, filter_id, q)
    extra_vars[u'dashboard_activity_stream'] = h.dashboard_activity_stream(
        g.userobj.id, filter_type, filter_id, offset)

    # Mark the user's new activities as old whenever they view their
    # dashboard page.
    logic.get_action(u'dashboard_mark_activities_old')(context, {})

    return base.render(u'user/dashboard.html', extra_vars)


def datasets() -> str:
    context: Context = {
        u'for_view': True, u'user': g.user, u'auth_user_obj': g.userobj}
    data_dict: dict[str, Any] = {
        u'user_obj': g.userobj,
        u'include_datasets': True}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render(u'user/dashboard_datasets.html', extra_vars)


def organizations() -> str:
    context: Context = {
        u'for_view': True, u'user': g.user, u'auth_user_obj': g.userobj}
    data_dict = {u'user_obj': g.userobj}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render(u'user/dashboard_organizations.html', extra_vars)


def groups() -> str:
    context: Context = {
        u'for_view': True, u'user': g.user, u'auth_user_obj': g.userobj}
    data_dict = {u'user_obj': g.userobj}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render(u'user/dashboard_groups.html', extra_vars)


dashboard.add_url_rule(
    u'/', view_func=index, strict_slashes=False, defaults={
        u'offset': 0
    })
dashboard.add_url_rule(u'/<int:offset>', view_func=index)

dashboard.add_url_rule(u'/datasets', view_func=datasets)
dashboard.add_url_rule(u'/groups', view_func=groups)
dashboard.add_url_rule(u'/organizations', view_func=organizations)
