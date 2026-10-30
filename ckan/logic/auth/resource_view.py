from __future__ import annotations

import ckan.authz as authz
import ckan.logic as logic
from ckan import model
from ckan.common import _
from ckan.types import AuthResult, Context, DataDict


@logic.auth_allow_anonymous_access
def resource_view_show(context: Context, data_dict: DataDict) -> AuthResult:
    resource_view = model.ResourceView.get(data_dict["id"])
    if not resource_view:
        raise logic.NotFound(_("Resource view not found, cannot check auth."))
    resource = model.Resource.get(resource_view.resource_id)

    assert resource
    return authz.is_authorized("resource_show", context, {"id": resource.id})


@logic.auth_allow_anonymous_access
def resource_view_list(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("resource_show", context, data_dict)


def resource_view_create(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized(
        "resource_create", context, {"id": data_dict["resource_id"]}
    )


def resource_create_default_resource_views(
    context: Context, data_dict: DataDict
) -> AuthResult:
    return authz.is_authorized(
        "resource_create", context, {"id": data_dict["resource"]["id"]}
    )


def package_create_default_resource_views(
    context: Context, data_dict: DataDict
) -> AuthResult:
    return authz.is_authorized("package_update", context, data_dict["package"])


def resource_view_update(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized(
        "resource_update", context, {"id": data_dict["resource_id"]}
    )


def resource_view_reorder(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized(
        "resource_update", context, {"id": data_dict["resource_id"]}
    )


def resource_view_delete(context: Context, data_dict: DataDict) -> AuthResult:
    resource_view = model.ResourceView.get(data_dict["id"])
    if not resource_view:
        raise logic.NotFound(_("Resource view not found, cannot check auth."))
    resource_id = resource_view.resource_id

    return authz.is_authorized("resource_delete", context, {"id": resource_id})


def resource_view_clear(context: Context, data_dict: DataDict) -> AuthResult:
    # sysadmins only
    return {"success": False}
