# -*- coding: utf-8 -*-

import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model

from ckan.common import config, g
from ckan.types import Model, Context

from typing import Union
from markupsafe import Markup


def group_image(group: "Model.Group", size: int = 100):
    gravatar_default = config.get_value("ckan.gravatar_default")
    if group.image_url:
        return h.literal(
            """<img src="{url}"
                    class="image"
                    width="{size}" height="{size}" alt="{alt}" />""".format(
                url=h.sanitize_url(group.image_url), size=size, alt=group.name
            )
        )
    elif gravatar_default == "disabled":
        return h.snippet(
            "/base/images/placeholder-group.png", size=size, group=group
        )
    else:
        return h.gravatar(group.title, size, gravatar_default)


@h.core_helper
def linked_group(group_id: str, avatar: int = 20) -> Union[Markup, str, None]:
    group = model.Group.get(group_id)
    if not group:
        return

    return h.literal(
        "{icon} {link}".format(
            icon=group_image(group, size=avatar),
            link=h.link_to(
                group.display_name, h.url_for("group.read", id=group.id)
            ),
        )
    )


@h.core_helper
def get_collaborators_group(package_id: str) -> "list[tuple[str, str]]":

    context: Context = {"ignore_auth": True, "user": g.user}
    data_dict = {"id": package_id}
    _collaborators = logic.get_action("package_collaborator_list_for_group")(
        context, data_dict
    )

    collaborators = []

    for collaborator in _collaborators:
        collaborators.append(
            (collaborator["group_id"], collaborator["capacity"])
        )
    return collaborators
