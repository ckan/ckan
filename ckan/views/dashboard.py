# encoding: utf-8
from __future__ import annotations

import logging
from typing import Any, cast

from flask import Blueprint

import ckan.lib.base as base
from ckan.lib.helpers import helper_functions as h
import ckan.logic as logic
import ckan.model as model
from ckan.common import _, current_user
from ckan.views.user import _extra_template_variables
from ckan.types import Context

log = logging.getLogger(__name__)

dashboard = Blueprint(u'dashboard', __name__, url_prefix=u'/dashboard')


@dashboard.before_request
def before_request() -> None:
    if current_user.is_anonymous:
        h.flash_error(_(u'Not authorized to see this page'))

        # flask types do not mention that it's possible to return a response
        # from the `before_request` callback
        return h.redirect_to(u'user.login')

    try:
        context = cast(Context, {
            "model": model,
            "user": current_user.name,
            "auth_user_obj": current_user
        })
        logic.check_access(u'site_read', context)
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))
    return None


def datasets() -> str:
    context = cast(Context, {
        u'for_view': True,
        u'user': current_user.name,
        u'auth_user_obj': current_user
    })
    data_dict: dict[str, Any] = {
        u'user_obj': current_user,
        u'include_datasets': True}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render(u'user/dashboard_datasets.html', extra_vars)


def organizations() -> str:
    context = cast(Context, {
        u'for_view': True,
        u'user': current_user.name,
        u'auth_user_obj': current_user
    })
    data_dict = {u'user_obj': current_user}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render(u'user/dashboard_organizations.html', extra_vars)


def groups() -> str:
    context = cast(Context, {
        u'for_view': True,
        u'user': current_user.name,
        u'auth_user_obj': current_user
    })
    data_dict = {u'user_obj': current_user}
    extra_vars = _extra_template_variables(context, data_dict)
    return base.render(u'user/dashboard_groups.html', extra_vars)


dashboard.add_url_rule(u'/datasets', view_func=datasets)
dashboard.add_url_rule(u'/groups', view_func=groups)
dashboard.add_url_rule(u'/organizations', view_func=organizations)
