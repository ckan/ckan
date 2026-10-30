from __future__ import annotations

import ckan.authz as authz
import ckan.logic as logic
import ckan.logic.auth as logic_auth
from ckan import model
from ckan.common import _
from ckan.logic.auth import get_resource_object
from ckan.types import AuthResult, Context, DataDict


@logic.auth_allow_anonymous_access
def resource_show(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get("user")
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    assert resource.package_id
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(
            _("No package found for this resource, cannot check auth.")
        )

    pkg_dict = {"id": pkg.id}
    authorized = authz.is_authorized("package_show", context, pkg_dict).get("success")

    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to read resource %s")
            % (user, resource.id),
        }
    else:
        return {"success": True}


@logic.auth_allow_anonymous_access
def format_autocomplete(context: Context, data_dict: DataDict) -> AuthResult:
    return {"success": True}


@logic.auth_allow_anonymous_access
def resource_search(context: Context, data_dict: DataDict) -> AuthResult:
    """Check if resource search is allowed.
    Allowed for all by default."""
    return {"success": True}


def resource_create(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get("user")

    package_id = data_dict.get("package_id")
    if not package_id and data_dict.get("id"):
        # This can happen when auth is deferred, eg from `resource_view_create`
        resource = logic_auth.get_resource_object(context, data_dict)
        package_id = resource.package_id

    if not package_id:
        raise logic.NotFound(_("No dataset id provided, cannot check auth."))

    # check authentication against package
    pkg = model.Package.get(package_id)
    if not pkg:
        raise logic.NotFound(
            _("No package found for this resource, cannot check auth.")
        )

    pkg_dict = {"id": pkg.id}
    authorized = authz.is_authorized("package_update", context, pkg_dict).get("success")

    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to create resources on dataset %s")
            % (str(user), package_id),
        }
    else:
        return {"success": True}


def package_resource_reorder(context: Context, data_dict: DataDict) -> AuthResult:
    # the action function runs package update so no need to run it twice
    return {"success": True}


def resource_update(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get("user")
    resource = logic_auth.get_resource_object(context, data_dict)

    # check authentication against package
    assert resource.package_id
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(
            _("No package found for this resource, cannot check auth.")
        )

    pkg_dict = {"id": pkg.id}
    authorized = authz.is_authorized("package_update", context, pkg_dict).get("success")

    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to edit resource %s")
            % (str(user), resource.id),
        }
    else:
        return {"success": True}


def resource_delete(context: Context, data_dict: DataDict) -> AuthResult:
    user = context.get("user")
    resource = get_resource_object(context, data_dict)

    # check authentication against package
    assert resource.package_id
    pkg = model.Package.get(resource.package_id)
    if not pkg:
        raise logic.NotFound(
            _("No package found for this resource, cannot check auth.")
        )

    pkg_dict = {"id": pkg.id}
    authorized = authz.is_authorized("package_delete", context, pkg_dict).get("success")

    if not authorized:
        return {
            "success": False,
            "msg": _("User %s not authorized to delete resource %s")
            % (user, resource.id),
        }
    else:
        return {"success": True}


def resource_patch(context: Context, data_dict: DataDict) -> AuthResult:
    return authz.is_authorized("resource_update", context, data_dict)
