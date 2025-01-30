# -*- coding: utf-8 -*-

import logging

import ckan.plugins.toolkit as tk
import ckan.logic.auth as auth
import ckan.model as model
import ckan.authz as authz

from ckan.logic.auth.create import package_collaborator_create
from ckan.logic.auth.delete import package_collaborator_delete
from ckan.types import (
    AuthFunction,
    Context,
    DataDict,
    AuthResult,
    Model,
)

from ckanext.collaborator_group.model import PackageGroupMember

from typing import Union, Optional


log = logging.getLogger(__name__)


def package_collaborator_create_group(
    context: Context, data_dict: DataDict
) -> AuthResult:
    """Checks if a user is allowed to add collaborators to a dataset

    See :py:func:`~ckan.authz.can_manage_collaborators` for details
    """
    return package_collaborator_create(context, data_dict)


def package_collaborator_delete_group(
    context: Context, data_dict: DataDict
) -> AuthResult:
    """Checks if a user is allowed to remove collaborators from a dataset

    See :py:func:`~ckan.authz.can_manage_collaborators` for details
    """
    return package_collaborator_delete(context, data_dict)


def package_collaborator_list_for_group(
    context: Context, data_dict: DataDict
) -> Union["dict[str, bool]", bool]:
    user = context["user"]
    package = auth.get_package_object(context, data_dict)
    user_obj = model.User.get(user)

    assert package
    assert user_obj
    is_collaborator = group_is_collaborator_on_dataset(user_obj, package.id)
    if is_collaborator:
        return {"success": True}

    if authz.can_manage_collaborators(package.id, user_obj.id):
        return {"success": True}
    return {"success": False}


@tk.chained_auth_function  # type: ignore
def package_update(
    next_auth: AuthFunction, context: Context, data_dict: DataDict
) -> Union[bool, AuthResult]:

    user = context.get("user")
    user_obj = model.User.get(user)
    package = auth.get_package_object(context, data_dict)

    collaborator_group = tk.get_action("package_collaborator_list_for_group")(
        context, package.as_dict()
    )

    if collaborator_group:
        is_collaborator = group_is_collaborator_on_dataset(
            user_obj, package.id, collaborator_group[0].get("capacity")
        )

        if is_collaborator:
            return {"success": True}
    return next_auth(context, data_dict)


def group_is_collaborator_on_dataset(
    user_obj: Optional["Model.User"],
    dataset_id: str,
    capacity: "Optional[Union[str, list[str]]]" = None,
) -> Union[bool, "dict[str, bool]"]:
    """
    Returns True if the provided user is in a group that is collaborator on
    the provided dataset.

    If capacity is provided it restricts the check to the capacity
    provided (eg `admin` or `editor`). Multiple capacities can be
    provided passing a list

    """
    if user_obj:
        group_ids = user_obj.get_group_ids()
        for id in group_ids:
            q = (
                model.Session.query(PackageGroupMember)
                .filter(PackageGroupMember.group_id == id)
                .filter(PackageGroupMember.package_id == dataset_id)
            )

            if capacity:
                if isinstance(capacity, str):
                    capacity = [capacity]
            # q = q.filter(
            #     PackageGroupMember.capacity.in_(capacity)  # type: ignore
            # )
            return model.Session.query(q.exists()).scalar()
    return False
