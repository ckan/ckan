# -*- coding: utf-8 -*-

import datetime
import logging

import ckan.lib.dictization.model_dictize as model_dictize
import ckan.plugins.toolkit as tk
import ckan.authz as authz

from ckan.types import Context, DataDict, ActionResult

from ckanext.collaborator_group.model import PackageGroupMember


log = logging.getLogger(__name__)


def package_collaborator_create_group(
    context: Context, data_dict: DataDict
) -> ActionResult.PackageCollaboratorCreate:

    model = context["model"]

    package_id, group_id, capacity = tk.get_or_bust(
        data_dict, ["id", "group_id", "capacity"]
    )

    allowed_capacities = authz.get_collaborator_capacities()
    if capacity not in allowed_capacities:
        raise tk.ValidationError(
            {
                "message": tk._('Role must be one of "{}"').format(
                    ", ".join(allowed_capacities)
                )
            }
        )

    tk.check_access("package_collaborator_create_group", context, data_dict)

    package = model.Package.get(package_id)
    if not package:
        raise tk.ObjectNotFound("Dataset not found")

    group = model.Group.get(group_id)
    if not group:
        raise tk.ObjectNotFound("Group not found")

    if not authz.check_config_permission("allow_dataset_collaborators"):
        raise tk.ValidationError(
            {"message": tk._("Dataset collaborators not enabled")}
        )

    # Check if collaborator already exists
    collaborator = (
        model.Session.query(PackageGroupMember)
        .filter(PackageGroupMember.package_id == package.id)
        .filter(PackageGroupMember.group_id == group.id)
        .one_or_none()
    )
    if not collaborator:
        collaborator = PackageGroupMember(
            package_id=package.id, group_id=group.id
        )
    collaborator.capacity = capacity
    collaborator.modified = datetime.datetime.utcnow()
    model.Session.add(collaborator)
    model.repo.commit()

    log.info(
        "Group {} added as collaborator in package {} ({})".format(
            group.name, package.id, capacity
        )
    )

    return model_dictize.member_dictize(collaborator, context)  # type: ignore


def package_collaborator_delete_group(
    context: Context, data_dict: DataDict
) -> ActionResult.PackageCollaboratorDelete:

    model = context["model"]

    package_id, group_id = tk.get_or_bust(data_dict, ["id", "group_id"])

    tk.check_access("package_collaborator_delete", context, data_dict)

    if not authz.check_config_permission("allow_dataset_collaborators"):
        raise tk.ValidationError(
            {"message": tk._("Dataset collaborators not enabled")}
        )

    package = model.Package.get(package_id)
    if not package:
        raise tk.ObjectNotFound("Package not found")

    group = model.Group.get(group_id)
    if not group:
        raise tk.ObjectNotFound("Group not found")

    collaborator = (
        model.Session.query(PackageGroupMember)
        .filter(PackageGroupMember.package_id == package.id)
        .filter(PackageGroupMember.group_id == group.id)
        .one_or_none()
    )
    if not collaborator:
        raise tk.ObjectNotFound(
            "Group {} is not a collaborator on this package".format(group_id)
        )

    model.Session.delete(collaborator)
    model.repo.commit()

    log.info(
        "User {} removed as collaborator from package {}".format(
            group_id, package.id
        )
    )


def package_collaborator_list_for_group(
    context: Context, data_dict: DataDict
) -> ActionResult.PackageCollaboratorListForUser:

    model = context["model"]

    package_id = tk.get_or_bust(data_dict, "id")

    package = model.Package.get(package_id)
    if not package:
        raise tk.ObjectNotFound("Package not found")

    tk.check_access("package_collaborator_list_for_group", context, data_dict)

    if not authz.check_config_permission("allow_dataset_collaborators"):
        raise tk.ValidationError(
            {"message": tk._("Dataset collaborators not enabled")}
        )

    capacity = data_dict.get("capacity")

    allowed_capacities = authz.get_collaborator_capacities()
    if capacity and capacity not in allowed_capacities:
        raise tk.ValidationError(
            {
                "message": tk._('Capacity must be one of "{}"').format(
                    ", ".join(allowed_capacities)
                )
            }
        )

    q = model.Session.query(PackageGroupMember).filter(
        PackageGroupMember.package_id == package.id
    )

    if capacity:
        q = q.filter(PackageGroupMember.capacity == capacity)

    collaborators = q.all()

    return [collaborator.as_dict() for collaborator in collaborators]
