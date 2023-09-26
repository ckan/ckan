from __future__ import annotations

from typing import Any, Optional

from typing_extensions import TypedDict

import ckan.plugins.toolkit as tk


class UserDictWithExtras(TypedDict):
    plugin_extras: Optional[dict[str, Any]]


def get_helpers():
    return {
        "oidc_pkce_is_sso_user": oidc_pkce_is_sso_user,
    }


def oidc_pkce_is_sso_user(id_or_name: str) -> bool:
    site_user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    try:
        user: UserDictWithExtras = tk.get_action("user_show")(
            {"user": site_user["name"]},
            {"id": id_or_name, "include_plugin_extras": True},
        )
    except tk.ObjectNotFound:
        return False

    extras = user["plugin_extras"] or {}
    return "oidc_pkce" in extras
