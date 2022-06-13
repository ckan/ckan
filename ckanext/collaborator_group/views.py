# -*- coding: utf-8 -*-

import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as tk
import ckan.lib.helpers as h
import ckan.authz as authz
import ckan.lib.navl.dictization_functions as dict_fns

from ckan.common import g, request
from ckan.types import Context, Response

from typing import Any, Union, cast
from flask.views import MethodView
from flask import Blueprint


collaborator_group = Blueprint("collaborator_group", __name__)


def collaborator_delete():
    pass


class CollaboratorEditView(MethodView):
    def post(self, id: str) -> Response:  # noqa
        context = cast(Context, {"model": model, "user": g.user})
        data_dict = dict()

        try:
            form_dict = logic.clean_dict(
                dict_fns.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))
                )
            )

            if form_dict["group"]:
                group = logic.get_action("group_show")(
                    context, {"id": form_dict["group"]}
                )
                data_dict: dict[str, Any] = {
                    "id": id,
                    "group_id": group["id"],
                    "capacity": form_dict["capacity"],
                }

                logic.get_action("package_collaborator_create_group")(
                    context, data_dict
                )

            else:
                user = logic.get_action("user_show")(
                    context, {"id": form_dict["username"]}
                )

                data_dict: dict[str, Any] = {
                    "id": id,
                    "user_id": user["id"],
                    "capacity": form_dict["capacity"],
                }

                logic.get_action("package_collaborator_create")(
                    context, data_dict
                )

        except dict_fns.DataError:
            return tk.base.abort(400, tk._("Integrity Error"))
        except tk.NotAuthorized:
            message = tk._("Unauthorized to edit collaborators {}").format(id)
            return tk.base.abort(401, tk._(message))
        except tk.ObjectNotFound:
            h.flash_error(tk._("User not found"))
            return h.redirect_to("dataset.new_collaborator", id=id)
        except tk.ValidationError as e:
            h.flash_error(e.error_summary)
            return h.redirect_to("dataset.new_collaborator", id=id)
        else:
            h.flash_success(tk._("User added to collaborators"))

        return h.redirect_to("dataset.collaborators_read", id=id)

    def get(self, id: str) -> Union[Response, str]:  # noqa
        context = cast(Context, {"model": model, "user": g.user})
        data_dict = {"id": id}

        try:
            logic.check_access("package_collaborator_list", context, data_dict)
            # needed to ckan_extend package/edit_base.html
            pkg_dict = logic.get_action("package_show")(context, data_dict)
        except tk.NotAuthorized:
            message = "Unauthorized to read collaborators {}".format(id)
            return tk.base.abort(401, tk._(message))
        except tk.ObjectNotFound:
            return tk.base.abort(404, tk._("Resource not found"))

        user = request.args.get("user_id")
        group = request.args.get("group_id")
        user_capacity = "member"
        group_capacity = "member"

        if user:
            collaborators = logic.get_action("package_collaborator_list")(
                context, data_dict
            )
            for c in collaborators:
                if c["user_id"] == user:
                    user_capacity = c["capacity"]
            user = logic.get_action("user_show")(context, {"id": user})

        if group:
            collaborators = logic.get_action(
                "package_collaborator_list_for_group"
            )(context, data_dict)
            for c in collaborators:
                if c["group_id"] == group:
                    group_capacity = c["capacity"]
            group = logic.get_action("group_show")(context, {"id": group})

        capacities: list[dict[str, str]] = []
        if authz.check_config_permission("allow_admin_collaborators"):
            capacities.append({"name": "admin", "value": "admin"})
        capacities.extend(
            [
                {"name": "editor", "value": "editor"},
                {"name": "member", "value": "member"},
            ]
        )

        extra_vars: dict[str, Any] = {
            "capacities": capacities,
            "user_capacity": user_capacity,
            "user": user,
            "group_capacity": group_capacity,
            "group": group,
            "pkg_dict": pkg_dict,
        }

        return tk.base.render(
            "/package/collaborators/collaborator_new.html", extra_vars
        )


collaborator_group.add_url_rule(
    "/dataset/collaborators/<id>/new",
    view_func=CollaboratorEditView.as_view(str("new_collaborator")),
    methods=[
        "GET",
        "POST",
    ],
)
collaborator_group.add_url_rule(
    rule="/collaborators/<id>/delete/<user_id>",
    view_func=collaborator_delete,
    methods=[
        "POST",
    ],
)
