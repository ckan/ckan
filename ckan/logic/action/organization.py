from __future__ import annotations

from typing import cast

from ckan import authz, model
from ckan.common import asbool
from ckan.lib.dictization import model_dictize
from ckan.logic import (
    NotFound,
    side_effect_free,
)
from ckan.logic import check_access as _check_access
from ckan.logic import fresh_context as _fresh_context
from ckan.logic import get_action as _get_action
from ckan.logic import get_or_bust as _get_or_bust
from ckan.logic.action.group import (
    _group_or_org_autocomplete,
    _group_or_org_create,
    _group_or_org_delete,
    _group_or_org_list,
    _group_or_org_member_create,
    _group_or_org_member_delete,
    _group_or_org_purge,
    _group_or_org_show,
    _group_or_org_update,
)
from ckan.types import ActionResult, Context, DataDict


def organization_create(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationCreate:
    """Create a new organization.

    You must be authorized to create organizations.

    Plugins may change the parameters of this function depending on the value
    of the ``type`` parameter, see the
    :py:class:`~ckan.plugins.interfaces.IGroupForm` plugin interface.

    :param name: the name of the organization, a string between 2 and
        100 characters long, containing only lowercase alphanumeric
        characters, ``-`` and ``_``
    :type name: string
    :param id: the id of the organization (optional)
    :type id: string
    :param title: the title of the organization (optional)
    :type title: string
    :param description: the description of the organization (optional)
    :type description: string
    :param image_url: the URL to an image to be displayed on the
        organization's page (optional)
    :type image_url: string
    :param state: the current state of the organization, e.g. ``'active'`` or
        ``'deleted'``, only active organizations show up in search results and
        other lists of organizations, this parameter will be ignored if you
        are not authorized to change the state of the organization
        (optional, default: ``'active'``)
    :type state: string
    :param approval_status: (optional)
    :type approval_status: string
    :param extras: the organization's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to organizations,
        each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string), and optionally ``'deleted'``
    :type extras: list of package extra dictionaries
    :param packages: the packages that belong to the organization,
        a list of dictionaries each with keys ``'name'`` (string, the id
        or name of the package) and optionally ``'title'`` (string, the
        title of the package)
    :type packages: list of dictionaries
    :param users: the users that belong to the organization, a list
        of dictionaries each with key ``'name'`` (string, the id or name
        of the user) and optionally ``'capacity'`` (string, the capacity
        in which the user is a member of the organization)
    :type users: list of dictionaries

    :returns: the newly created organization (unless 'return_id_only' is set
              to True in the context, in which case just the organization id
              will be returned)
    :rtype: dictionary

    """
    # wrapper for creating organizations
    data_dict.setdefault("type", "organization")
    _check_access("organization_create", context, data_dict)
    return _group_or_org_create(context, data_dict, is_org=True)


@side_effect_free
def organization_list(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationList:
    """Return a list of the names of the site's organizations.

    :param type: the type of organization to list (optional,
        default: ``'organization'``),
        See docs for :py:class:`~ckan.plugins.interfaces.IGroupForm`
    :type type: string
    :param order_by: the field to sort the list by, must be ``'name'`` or
      ``'packages'`` (optional, default: ``'name'``) Deprecated use sort.
    :type order_by: string
    :param sort: sorting of the search results.  Optional.  Default:
        "title asc" string of field name and sort-order. The allowed fields are
        'name', 'package_count' and 'title'
    :type sort: string
    :param limit: the maximum number of organizations returned (optional)
        Default: ``1000`` when all_fields=false unless set in site's
        configuration ``ckan.group_and_organization_list_max``
        Default: ``25`` when all_fields=true unless set in site's
        configuration ``ckan.group_and_organization_list_all_fields_max``
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start
        returning organizations from
    :type offset: int
    :param organizations: a list of names of the organizations to return,
        if given only organizations whose names are in this list will be
        returned (optional)
    :type organizations: list of strings
    :param all_fields: return group dictionaries instead of just names. Only
        core fields are returned - get some more using the include_* options.
        Returning a list of packages is too expensive, so the `packages`
        property for each group is deprecated, but there is a count of the
        packages in the `package_count` property.
        (optional, default: ``False``)
    :type all_fields: bool
    :param include_dataset_count: if all_fields, include the full package_count
        (optional, default: ``True``)
    :type include_dataset_count: bool
    :param include_extras: if all_fields, include the organization extra fields
        (optional, default: ``False``)
    :type include_extras: bool
    :param include_groups: if all_fields, include the groups the
        organizations are in
        (optional, default: ``False``)
    :type include_groups: bool
    :param include_users: if all_fields, include the organization users
        (optional, default: ``False``).
    :type include_users: bool

    :rtype: list of strings

    """
    _check_access("organization_list", context, data_dict)
    data_dict["groups"] = data_dict.pop("organizations", [])
    data_dict.setdefault("type", "organization")
    return _group_or_org_list(context, data_dict, is_org=True)


@side_effect_free
def organization_list_for_user(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationListForUser:
    """Return the organizations that the user has a given permission for.

    Specifically it returns the list of organizations that the currently
    authorized user has a given permission (for example: "manage_group")
    against.

    By default this returns the list of organizations that the currently
    authorized user is member of, in any capacity.

    When a user becomes a member of an organization in CKAN they're given a
    "capacity" (sometimes called a "role"), for example "member", "editor" or
    "admin".

    Each of these roles has certain permissions associated with it. For example
    the admin role has the "admin" permission (which means they have permission
    to do anything). The editor role has permissions like "create_dataset",
    "update_dataset" and "delete_dataset".  The member role has the "read"
    permission.

    This function returns the list of organizations that the authorized user
    has a given permission for. For example the list of organizations that the
    user is an admin of, or the list of organizations that the user can create
    packages in. This takes account of when permissions cascade down an
    organization hierarchy.

    :param id: the name or id of the user to get the organization list for
        (optional, defaults to the currently authorized user (logged in or via
        API key))
    :type id: string

    :param permission: the permission the user has against the
        returned organizations, for example ``"read"`` or ``"create_dataset"``
        (optional, default: ``"manage_group"``)
    :type permission: string
    :param include_dataset_count: include the package_count in each org
        (optional, default: ``False``)
    :type include_dataset_count: bool

    :returns: list of organizations that the user has the given permission for
    :rtype: list of dicts

    """
    if data_dict.get("id"):
        user_obj = model.User.get(data_dict["id"])
        if not user_obj:
            raise NotFound
        user = user_obj.name
    else:
        user = context["user"]

    _check_access("organization_list_for_user", context, data_dict)
    sysadmin = authz.is_sysadmin(user)

    orgs_q = (
        model.Session.query(model.Group)
        .filter(model.Group.is_organization == True)  # noqa: E712
        .filter(model.Group.state == "active")
    )

    if sysadmin:
        orgs_and_capacities = [(org, "admin") for org in orgs_q.all()]
    else:
        # for non-Sysadmins check they have the required permission

        permission = data_dict.get("permission", "manage_group")

        roles = authz.get_roles_with_permission(permission)

        if not roles:
            return []
        user_id = authz.get_user_id_for_username(user, allow_none=True)
        if not user_id:
            return []

        q = (
            model.Session.query(model.Member, model.Group)
            .filter(model.Member.table_name == "user")
            .filter(model.Member.capacity.in_(roles))
            .filter(model.Member.table_id == user_id)
            .filter(model.Member.state == "active")
            .join(model.Group)
        )

        group_ids: set[str] = set()
        roles_that_cascade = cast(
            "list[str]",
            authz.check_config_permission("roles_that_cascade_to_sub_groups"),
        )
        group_ids_to_capacities: dict[str, str] = {}
        for member, group in q.all():
            if member.capacity in roles_that_cascade:
                children_group_ids = [
                    grp_tuple[0]
                    for grp_tuple in group.get_children_group_hierarchy(
                        type="organization"
                    )
                ]
                for group_id in children_group_ids:
                    group_ids_to_capacities[group_id] = member.capacity
                group_ids |= set(children_group_ids)

            group_ids_to_capacities[group.id] = member.capacity
            group_ids.add(group.id)

        if not group_ids:
            return []

        orgs_q = orgs_q.filter(model.Group.id.in_(group_ids))
        orgs_and_capacities = [
            (org, group_ids_to_capacities[org.id]) for org in orgs_q.all()
        ]

    context["with_capacity"] = True
    orgs_list = model_dictize.group_list_dictize(
        orgs_and_capacities,
        context,
        with_package_counts=asbool(data_dict.get("include_dataset_count")),
        with_member_counts=asbool(data_dict.get("include_member_count")),
    )
    return orgs_list


@side_effect_free
def organization_show(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationShow:
    """Return the details of an organization.

    :param id: the id or name of the organization
    :type id: string
    :param include_datasets: include a truncated list of the org's packages
         (optional, default: ``False``)
    :type include_datasets: bool
    :param include_dataset_count: include the full package_count
         (optional, default: ``True``)
    :type include_dataset_count: bool
    :param include_extras: include the organization's extra fields
         (optional, default: ``True``)
    :type include_extras: bool
    :param include_users: include the organization's users
         (optional, default: ``False``)
    :type include_users: bool
    :param include_groups: include the organization's sub groups
         (optional, default: ``True``)
    :type include_groups: bool
    :param include_followers: include the organization's number of followers
         (optional, default: ``True``)
    :type include_followers: bool


    :rtype: dictionary

    .. note:: Only its first 10 packages are returned
    """
    return _group_or_org_show(context, data_dict, is_org=True)


@side_effect_free
def organization_autocomplete(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationAutocomplete:
    """
    Return a list of organization names that contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of organizations to return (optional,
        default: ``20``)
    :type limit: int

    :rtype: a list of organization dictionaries each with keys ``'name'``,
        ``'title'``, and ``'id'``
    """

    _check_access("organization_autocomplete", context, data_dict)

    return _group_or_org_autocomplete(context, data_dict, is_org=True)


def organization_member_create(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationMemberCreate:
    """Make a user a member of an organization.

    You must be authorized to edit the organization.

    :param id: the id or name of the organization
    :type id: string
    :param username: name or id of the user to be made member of the
        organization
    :type username: string
    :param role: role of the user in the organization. One of ``member``,
        ``editor``, or ``admin``
    :type role: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary
    """
    _check_access("organization_member_create", context, data_dict)
    return _group_or_org_member_create(context, data_dict, is_org=True)


def organization_update(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationUpdate:
    """Update an organization.

    You must be authorized to edit the organization.

    .. note:: Update methods may delete parameters not explicitly provided in the
        data_dict. If you want to edit only a specific attribute use
        `organization_patch` instead.

    For further parameters see
    :py:func:`~ckan.logic.action.organization.organization_create`.

    Callers can choose to not specify packages, users or groups and they will be
    left at their existing values.

    :param id: the name or id of the organization to update
    :type id: string
    :param packages: ignored. use
        :py:func:`~ckan.logic.action.package.package_owner_org_update`
        to change package ownership

    :returns: the updated organization
    :rtype: dictionary

    """
    return _group_or_org_update(context, data_dict, is_org=True)


def organization_patch(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationPatch:
    """Patch an organization

    :param id: the id or name of the organization
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    """
    _check_access("organization_patch", context, data_dict)

    show_context: Context = _fresh_context(context)

    organization_dict = _get_action("organization_show")(
        show_context, {"id": _get_or_bust(data_dict, "id")}
    )

    patched = dict(organization_dict)
    patched.pop("display_name", None)
    patched.update(data_dict)

    patch_context = context.copy()
    return _get_action("organization_update")(patch_context, patched)


def organization_delete(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationDelete:
    """Delete an organization.

    You must be authorized to delete the organization
    and no packages should belong to the organization
    unless 'ckan.auth.create_unowned_dataset=True'

    :param id: the name or id of the organization
    :type id: string

    """
    return _group_or_org_delete(context, data_dict, is_org=True)


def organization_purge(context: Context, data_dict: DataDict) -> None:
    """Purge an organization.

    .. warning:: Purging an organization cannot be undone!

    Purging an organization completely removes the organization from the CKAN
    database, whereas deleting an organization simply marks the organization as
    deleted (it will no longer show up in the frontend, but is still in the
    db).

    Packages owned by the organization will remain, just not in an
    organization anymore.

    You must be authorized to purge the organization.

    :param id: the name or id of the organization to be purged
    :type id: string

    """
    return _group_or_org_purge(context, data_dict, is_org=True)


def organization_member_delete(context: Context, data_dict: DataDict) -> None:
    """Remove a user from an organization.

    You must be authorized to edit the organization.

    :param id: the id or name of the organization
    :type id: string
    :param username: name or id of the user to be removed
    :type username: string

    """
    _check_access("organization_member_delete", context, data_dict)
    return _group_or_org_member_delete(context, data_dict)
