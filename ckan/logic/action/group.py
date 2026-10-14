from __future__ import annotations

import logging
import six
import sqlalchemy
import sqlalchemy as sqla
import ckan
import ckan.authz as authz
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.dictization.model_save as model_save
import ckan.lib.plugins as lib_plugins
import ckan.lib.uploader as uploader
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
from ckan.common import _, asbool, aslist, config
from ckan.lib.search import rebuild
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.logic import (
    NotAuthorized,
    NotFound,
    ValidationError,
    check_access as _check_access,
    fresh_context,
    fresh_context as _fresh_context,
    get_action as _get_action,
    get_or_bust as _get_or_bust,
    side_effect_free,
)
from ckan.types import ActionResult, Context, DataDict, Schema
from typing import Any, Container, Optional, Union, cast

log = logging.getLogger("ckan.logic")
_or_ = sqlalchemy.or_


def _group_or_org_create(
    context: Context, data_dict: DataDict, is_org: bool = False
) -> Union[str, dict[str, Any]]:
    user = context["user"]
    session = context["session"]
    data_dict["is_organization"] = is_org

    upload = uploader.get_uploader("group")
    upload.update_data_dict(data_dict, "image_url", "image_upload", "clear_upload")
    # get the schema
    group_type = data_dict.get("type", "organization" if is_org else "group")
    group_plugin = lib_plugins.lookup_group_plugin(group_type)

    if context.get("schema"):
        schema: Schema = context["schema"]
    else:
        schema: Schema = group_plugin.create_group_schema()

    data, errors = lib_plugins.plugin_validate(
        group_plugin,
        context,
        data_dict,
        schema,
        "organization_create" if is_org else "group_create",
    )
    log.debug(
        "group_create validate_errs=%r user=%s group=%s data_dict=%r",
        errors,
        context.get("user"),
        data_dict.get("name"),
        data_dict,
    )

    if errors:
        session.rollback()
        raise ValidationError(errors)

    group = model_save.group_dict_save(data, context)

    # Needed to let extensions know the group id
    session.flush()

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.create(group)

    user_obj = model.User.by_name(six.ensure_text(user))
    assert user_obj

    upload.upload(uploader.get_max_image_size())

    if not context.get("defer_commit"):
        model.repo.commit()
    context["group"] = group
    context["id"] = group.id

    # creator of group/org becomes an admin
    # this needs to be after the repo.commit or else revisions break
    member_dict = {
        "id": group.id,
        "object": user_obj.id,
        "object_type": "user",
        "capacity": "admin",
    }
    member_create_context = fresh_context(context)
    # We are not a member of the group at this point
    member_create_context["ignore_auth"] = True

    logic.get_action("member_create")(member_create_context, member_dict)
    log.debug("Created object %s", group.name)

    return_id_only = context.get("return_id_only", False)
    action = "organization_show" if is_org else "group_show"

    if return_id_only:
        return context["id"]

    return _get_action(action)(
        context, {"id": group.id, "include_users": "users" in data}
    )


def group_create(context: Context, data_dict: DataDict) -> ActionResult.GroupCreate:
    """Create a new group.

    You must be authorized to create groups.

    Plugins may change the parameters of this function depending on the value
    of the ``type`` parameter, see the
    :py:class:`~ckan.plugins.interfaces.IGroupForm` plugin interface.

    :param name: the name of the group, a string between 2 and 100 characters
        long, containing only lowercase alphanumeric characters, ``-`` and
        ``_``
    :type name: string
    :param id: the id of the group (optional)
    :type id: string
    :param title: the title of the group (optional)
    :type title: string
    :param description: the description of the group (optional)
    :type description: string
    :param image_url: the URL to an image to be displayed on the group's page
        (optional)
    :type image_url: string
    :param type: the type of the group (optional, default: ``'group'``),
        :py:class:`~ckan.plugins.interfaces.IGroupForm` plugins
        associate themselves with different group types and provide custom
        group handling behaviour for these types
        Cannot be 'organization'
    :type type: string
    :param state: the current state of the group, e.g. ``'active'`` or
        ``'deleted'``, only active groups show up in search results and
        other lists of groups, this parameter will be ignored if you are not
        authorized to change the state of the group (optional, default:
        ``'active'``)
    :type state: string
    :param approval_status: (optional)
    :type approval_status: string
    :param extras: the group's extras (optional), extras are arbitrary
        (key: value) metadata items that can be added to groups, each extra
        dictionary should have keys ``'key'`` (a string), ``'value'`` (a
        string), and optionally ``'deleted'``
    :type extras: list of dataset extra dictionaries
    :param packages: the datasets (packages) that belong to the group, a list
        of dictionaries each with keys ``'name'`` (string, the id or name of
        the dataset) and optionally ``'title'`` (string, the title of the
        dataset)
    :type packages: list of dictionaries
    :param groups: the groups that belong to the group, a list of dictionaries
        each with key ``'name'`` (string, the id or name of the group) and
        optionally ``'capacity'`` (string, the capacity in which the group is
        a member of the group)
    :type groups: list of dictionaries
    :param users: the users that belong to the group, a list of dictionaries
        each with key ``'name'`` (string, the id or name of the user) and
        optionally ``'capacity'`` (string, the capacity in which the user is
        a member of the group)
    :type users: list of dictionaries

    :returns: the newly created group (unless 'return_id_only' is set to True
              in the context, in which case just the group id will
              be returned)
    :rtype: dictionary

    """
    # wrapper for creating groups
    if data_dict.get("type") == "organization":
        # FIXME better exception?
        raise Exception(_("Trying to create an organization as a group"))
    _check_access("group_create", context, data_dict)
    return _group_or_org_create(context, data_dict)


def member_create(context: Context, data_dict: DataDict) -> ActionResult.MemberCreate:
    """Make an object (e.g. a user, dataset or group) a member of a group.

    If the object is already a member of the group then the capacity of the
    membership will be updated.

    You must be authorized to edit the group.

    :param id: the id or name of the group to add the object to
    :type id: string
    :param object: the id or name of the object to add
    :type object: string
    :param object_type: the type of the object being added, e.g. ``'package'``
        or ``'user'``
    :type object_type: string
    :param capacity: the capacity of the membership
    :type capacity: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary

    """
    user = context["user"]

    group_id, obj_id, obj_type, capacity = _get_or_bust(
        data_dict, ["id", "object", "object_type", "capacity"]
    )

    group = model.Group.get(group_id)
    if not group:
        raise NotFound("Group was not found.")

    obj_class = logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound("%s was not found." % obj_type.title())

    _check_access("member_create", context, data_dict)

    # Look up existing, in case it exists
    member = (
        model.Session.query(model.Member)
        .filter(model.Member.table_name == obj_type)
        .filter(model.Member.table_id == obj.id)
        .filter(model.Member.group_id == group.id)
        .order_by(model.Member.state.asc())
        .first()
    )
    if member:
        user_obj = model.User.get(user)
        if (
            user_obj
            and member.table_name == "user"
            and member.table_id == user_obj.id
            and member.capacity == "admin"
            and capacity != "admin"
        ):
            raise NotAuthorized("Administrators cannot revoke their own admin status")
        if member.state != "active":
            member.state = "active"
    else:
        member = model.Member(
            table_name=obj_type, table_id=obj.id, group_id=group.id, state="active"
        )
        member.group = group
    member.capacity = capacity

    model.Session.add(member)
    if not context.get("defer_commit"):
        model.repo.commit()
        if isinstance(obj, model.Package):
            rebuild(obj.id)

    return model_dictize.member_dictize(member, context)


def _group_or_org_member_create(
    context: Context, data_dict: dict[str, Any], is_org: bool = False
) -> ActionResult.GroupOrOrgMemberCreate:
    # creator of group/org becomes an admin
    # this needs to be after the repo.commit or else revisions break
    user = context["user"]

    schema = ckan.logic.schema.member_schema()
    _data, errors = _validate(data_dict, schema, context)
    if errors:
        model.Session.rollback()
        raise ValidationError(errors)

    username = _get_or_bust(data_dict, "username")
    role = data_dict.get("role")
    group_id = data_dict.get("id")
    group = model.Group.get(group_id)
    if not group:
        msg = _("Organization not found") if is_org else _("Group not found")
        raise NotFound(msg)
    result = model.User.get(username)
    if result:
        user_id = result.id
    else:
        message = _("User {username} does not exist.").format(username=username)
        raise ValidationError({"message": message})
    member_dict: dict[str, Any] = {
        "id": group.id,
        "object": user_id,
        "object_type": "user",
        "capacity": role,
    }
    member_create_context: Context = {
        "user": user,
        "ignore_auth": context.get("ignore_auth", False),
    }
    return logic.get_action("member_create")(member_create_context, member_dict)


def group_member_create(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupMemberCreate:
    """Make a user a member of a group.

    You must be authorized to edit the group.

    :param id: the id or name of the group
    :type id: string
    :param username: name or id of the user to be made member of the group
    :type username: string
    :param role: role of the user in the group. One of ``member``, ``editor``,
        or ``admin``
    :type role: string

    :returns: the newly created (or updated) membership
    :rtype: dictionary
    """
    _check_access("group_member_create", context, data_dict)
    return _group_or_org_member_create(context, data_dict)


@side_effect_free
def member_list(context: Context, data_dict: DataDict) -> ActionResult.MemberList:
    """Return the members of a group.

    The user must have permission to 'get' the group.

    :param id: the id or name of the group
    :type id: string
    :param object_type: restrict the members returned to those of a given type,
      e.g. ``'user'`` or ``'package'`` (optional, default: ``None``)
    :type object_type: string
    :param capacity: restrict the members returned to those with a given
      capacity, e.g. ``'member'``, ``'editor'``, ``'admin'``, ``'public'``,
      ``'private'`` (optional, default: ``None``)
    :type capacity: string

    :rtype: list of (id, type, capacity) tuples

    :raises: :class:`ckan.logic.NotFound`: if the group doesn't exist

    """
    _check_access("member_list", context, data_dict)

    group = model.Group.get(_get_or_bust(data_dict, "id"))
    if not group:
        raise NotFound

    obj_type = data_dict.get("object_type", None)
    capacity = data_dict.get("capacity", None)

    # User must be able to update the group to remove a member from it
    _check_access("group_show", context, data_dict)

    q = model.Session.query(model.Member)
    if obj_type:
        q = model.Member.all(obj_type)

    q = q.filter(model.Member.group_id == group.id).filter(
        model.Member.state == "active"
    )

    if capacity:
        q = q.filter(model.Member.capacity == capacity)

    trans = authz.roles_trans()

    def translated_capacity(capacity: str):
        try:
            return trans[capacity]
        except KeyError:
            return capacity

    return [
        (m.table_id, m.table_name, translated_capacity(m.capacity)) for m in q.all()
    ]


@side_effect_free
def member_roles_list(
    context: Context, data_dict: DataDict
) -> ActionResult.MemberRolesList:
    """Return the possible roles for members of groups and organizations.

    :param group_type: the group type, either ``"group"`` or ``"organization"``
        (optional, default ``"organization"``)
    :type group_type: string
    :returns: a list of dictionaries each with two keys: ``"text"`` (the
        display name of the role, e.g. ``"Admin"``) and ``"value"`` (the
        internal name of the role, e.g. ``"admin"``)
    :rtype: list of dictionaries

    """
    group_type = data_dict.get("group_type", "organization")
    roles_list = authz.roles_list()
    if group_type == "group":
        roles_list = [role for role in roles_list if role["value"] != "editor"]

    _check_access("member_roles_list", context, data_dict)
    return roles_list


def _unpick_search(
    sort: str,
    allowed_fields: Optional["Container[str]"] = None,
    total: Optional[int] = None,
) -> list[tuple[str, str]]:
    """This is a helper function that takes a sort string
    eg 'name asc, last_modified desc' and returns a list of
    split field order eg [('name', 'asc'), ('last_modified', 'desc')]
    allowed_fields can limit which field names are ok.
    total controls how many sorts can be specified"""
    sorts: list[tuple[str, str]] = []
    split_sort = sort.split(",")
    for part in split_sort:
        split_part = part.strip().split()
        field = split_part[0]
        if len(split_part) > 1:
            order = split_part[1].lower()
        else:
            order = "asc"
        if allowed_fields:
            if field not in allowed_fields:
                raise ValidationError({"message": "Cannot sort by field `%s`" % field})
        if order not in ["asc", "desc"]:
            raise ValidationError({"message": "Invalid sort direction `%s`" % order})
        sorts.append((field, order))
    if total and len(sorts) > total:
        raise ValidationError("Too many sort criteria provided only %s allowed" % total)
    return sorts


def _group_or_org_list(context: Context, data_dict: DataDict, is_org: bool = False):
    api = context.get("api_version")
    groups = data_dict.get("groups")
    group_type = data_dict.get("type", "group")
    ref_group_by = "id" if api == 2 else "name"
    pagination_dict = {}
    limit = data_dict.get("limit")
    if limit:
        pagination_dict["limit"] = data_dict["limit"]
    offset = data_dict.get("offset")
    if offset:
        pagination_dict["offset"] = data_dict["offset"]
    if pagination_dict:
        pagination_dict, errors = _validate(
            data_dict, ckan.logic.schema.default_pagination_schema(), context
        )
        if errors:
            raise ValidationError(errors)
    sort = data_dict.get("sort") or config.get("ckan.default_group_sort")
    q = data_dict.get("q", "").strip()

    all_fields = asbool(data_dict.get("all_fields", None))

    if all_fields:
        # all_fields is really computationally expensive, so need a tight limit
        try:
            max_limit = config.get("ckan.group_and_organization_list_all_fields_max")
        except ValueError:
            max_limit = 25
    else:
        try:
            max_limit = config.get("ckan.group_and_organization_list_max")
        except ValueError:
            max_limit = 1000

    if limit is None or int(limit) > max_limit:
        limit = max_limit

    # order_by deprecated in ckan 1.8
    # if it is supplied and sort isn't use order_by and raise a warning
    order_by = data_dict.get("order_by", "")
    if order_by:
        log.warning("`order_by` deprecated please use `sort`")
        if not data_dict.get("sort"):
            sort = order_by

    # if the sort is packages and no sort direction is supplied we want to do a
    # reverse sort to maintain compatibility.
    if sort.strip() in ("packages", "package_count"):
        sort = "package_count desc"

    sort_info = _unpick_search(
        sort, allowed_fields=["name", "packages", "package_count", "title"], total=1
    )

    if sort_info and sort_info[0][0] == "package_count":
        query = model.Session.query(
            model.Group.id, model.Group.name, sqlalchemy.func.count(model.Group.id)
        )

        query = (
            query.filter(model.Member.group_id == model.Group.id)
            .filter(model.Member.table_id == model.Package.id)
            .filter(model.Member.table_name == "package")
            .filter(model.Package.state == "active")
        )
    else:
        query = model.Session.query(model.Group.id, model.Group.name)

    query = query.filter(model.Group.state == "active")

    if groups:
        groups = aslist(groups, sep=",")
        query = query.filter(model.Group.name.in_(groups))
    if q:
        q = "%{0}%".format(q)
        query = query.filter(
            _or_(
                model.Group.name.ilike(q),
                model.Group.title.ilike(q),
                model.Group.description.ilike(q),
            )
        )

    query = query.filter(model.Group.is_organization == is_org)
    query = query.filter(model.Group.type == group_type)

    if sort_info:
        sort_field = sort_info[0][0]
        sort_direction = sort_info[0][1]
        sort_model_field: Any = sqlalchemy.func.count(model.Group.id)
        if sort_field == "package_count":
            query = query.group_by(model.Group.id, model.Group.name)
        elif sort_field == "name":
            sort_model_field = model.Group.name
        elif sort_field == "title":
            sort_model_field = model.Group.title

        if sort_direction == "asc":
            query = query.order_by(sqlalchemy.asc(sort_model_field))
        else:
            query = query.order_by(sqlalchemy.desc(sort_model_field))

    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)

    groups = query.all()

    if all_fields:
        # enforce permission filter based on user
        user = context.get("auth_user_obj")
        if context.get("ignore_auth") or (user and authz.is_sysadmin(user.name)):
            labels = None
        else:
            labels = lib_plugins.get_permission_labels().get_user_dataset_labels(user)

        counts = model_dictize.get_group_dataset_counts(
            fq="entity_type:package", permissions_labels=labels
        )

        # won't call get_packages_for_this_group in group_dictize
        show_context = cast(Context, dict(context, dataset_counts=counts))

        action = "organization_show" if is_org else "group_show"
        group_list = []
        for group in groups:
            data_dict["id"] = group.id
            for key in (
                "include_extras",
                "include_users",
                "include_groups",
                "include_followers",
            ):
                if key not in data_dict:
                    data_dict[key] = False

            group_list.append(logic.get_action(action)(show_context, data_dict))
    else:
        group_list = [getattr(group, ref_group_by) for group in groups]

    return group_list


@side_effect_free
def group_list(context: Context, data_dict: DataDict) -> ActionResult.GroupList:
    """Return a list of the names of the site's groups.

    :param type: the type of group to list (optional, default: ``'group'``),
        See docs for :py:class:`~ckan.plugins.interfaces.IGroupForm`
    :type type: string
    :param order_by: the field to sort the list by, must be ``'name'`` or
      ``'packages'`` (optional, default: ``'name'``) Deprecated use sort.
    :type order_by: string
    :param sort: sorting of the search results.  Optional.  Default:
        "title asc" string of field name and sort-order. The allowed fields are
        'name', 'package_count' and 'title'
    :type sort: string
    :param limit: the maximum number of groups returned (optional)
        Default: ``1000`` when all_fields=false unless set in site's
        configuration ``ckan.group_and_organization_list_max``
        Default: ``25`` when all_fields=true unless set in site's
        configuration ``ckan.group_and_organization_list_all_fields_max``
    :type limit: int
    :param offset: when ``limit`` is given, the offset to start
        returning groups from
    :type offset: int
    :param groups: a list of names of the groups to return, if given only
        groups whose names are in this list will be returned (optional)
    :type groups: list of strings
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
    :param include_extras: if all_fields, include the group extra fields
        (optional, default: ``False``)
    :type include_extras: bool
    :param include_groups: if all_fields, include the groups the groups are in
        (optional, default: ``False``).
    :type include_groups: bool
    :param include_users: if all_fields, include the group users
        (optional, default: ``False``).
    :type include_users: bool

    :rtype: list of strings
    """
    _check_access("group_list", context, data_dict)
    return _group_or_org_list(context, data_dict)


@side_effect_free
def group_list_authz(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupListAuthz:
    """Return the list of groups that the user is authorized to edit.

    :param available_only: remove the existing groups in the package
      (optional, default: ``False``)
    :type available_only: bool

    :param am_member: if ``True`` return only the groups the logged-in user is
      a member of, otherwise return all groups that the user is authorized to
      edit (for example, sysadmin users are authorized to edit all groups)
      (optional, default: ``False``)
    :type am_member: bool

    :returns: list of dictized groups that the user is authorized to edit
    :rtype: list of dicts

    """
    user = context["user"]
    available_only = data_dict.get("available_only", False)
    am_member = data_dict.get("am_member", False)

    _check_access("group_list_authz", context, data_dict)

    sysadmin = authz.is_sysadmin(user)
    roles = authz.get_roles_with_permission("manage_group")
    if not roles:
        return []
    user_id = authz.get_user_id_for_username(user, allow_none=True)
    if not user_id:
        return []

    group_ids: list[str] = []
    if not sysadmin or am_member:
        q: Any = (
            model.Session.query(model.Member.group_id)
            .filter(model.Member.table_name == "user")
            .filter(model.Member.capacity.in_(roles))
            .filter(model.Member.table_id == user_id)
            .filter(model.Member.state == "active")
        )
        group_ids = []
        for row in q:
            group_ids.append(row.group_id)

        if not group_ids:
            return []

    q = (
        model.Session.query(model.Group)
        .filter(model.Group.is_organization == False)
        .filter(model.Group.state == "active")
    )

    if not sysadmin or am_member:
        q = q.filter(model.Group.id.in_(group_ids))

    groups = q.all()

    if available_only:
        package = context.get("package")
        if package:
            groups = set(groups) - set(package.get_groups())

    group_list = model_dictize.group_list_dictize(
        groups,
        context,
        with_package_counts=asbool(data_dict.get("include_dataset_count")),
        with_member_counts=asbool(data_dict.get("include_member_count")),
    )
    return group_list


def _group_or_org_show(
    context: Context, data_dict: DataDict, is_org: bool = False
) -> dict[str, Any]:
    id = _get_or_bust(data_dict, "id")

    group = model.Group.get(id)

    if asbool(data_dict.get("include_datasets", False)):
        packages_field = "datasets"
    elif asbool(data_dict.get("include_dataset_count", True)):
        packages_field = "dataset_count"
    else:
        packages_field = None

    try:
        include_users = asbool(data_dict.get("include_users", False))
        include_groups = asbool(data_dict.get("include_groups", True))
        include_extras = asbool(data_dict.get("include_extras", True))
        include_followers = asbool(data_dict.get("include_followers", True))
        include_member_count = asbool(data_dict.get("include_member_count", False))
    except ValueError:
        raise logic.ValidationError({"message": _("Parameter is not an bool")})

    if group is None:
        raise NotFound
    if is_org and not group.is_organization:
        raise NotFound
    if not is_org and group.is_organization:
        raise NotFound

    context["group"] = group

    if is_org:
        _check_access("organization_show", context, data_dict)
    else:
        _check_access("group_show", context, data_dict)

    group_dict = model_dictize.group_dictize(
        group,
        context,
        packages_field=packages_field,
        include_extras=include_extras,
        include_groups=include_groups,
        include_users=include_users,
        include_member_count=include_member_count,
    )

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.read(group)

    group_plugin = lib_plugins.lookup_group_plugin(group_dict["type"])

    if context.get("schema"):
        schema: Schema = context["schema"]
    else:
        schema: Schema = group_plugin.show_group_schema()

    if include_followers:
        context = plugins.toolkit.fresh_context(context)
        group_dict["num_followers"] = logic.get_action("group_follower_count")(
            context, {"id": group_dict["id"]}
        )
    else:
        group_dict["num_followers"] = 0

    group_dict, _errors = lib_plugins.plugin_validate(
        group_plugin,
        context,
        group_dict,
        schema,
        "organization_show" if is_org else "group_show",
    )
    return group_dict


@side_effect_free
def group_show(context: Context, data_dict: DataDict) -> ActionResult.GroupShow:
    """Return the details of a group.

    :param id: the id or name of the group
    :type id: string
    :param include_datasets: include a truncated list of the group's datasets
         (optional, default: ``False``)
    :type include_datasets: bool
    :param include_dataset_count: include the full package_count
         (optional, default: ``True``)
    :type include_dataset_count: bool
    :param include_extras: include the group's extra fields
         (optional, default: ``True``)
    :type include_extras: bool
    :param include_users: include the group's users
         (optional, default: ``False``)
    :type include_users: bool
    :param include_groups: include the group's sub groups
         (optional, default: ``True``)
    :type include_groups: bool
    :param include_followers: include the group's number of followers
         (optional, default: ``True``)
    :type include_followers: bool

    :rtype: dictionary

    .. note:: Only its first 1000 datasets are returned

    """
    return _group_or_org_show(context, data_dict)


@side_effect_free
def group_package_show(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupPackageShow:
    """Return the datasets (packages) of a group.

    :param id: the id or name of the group
    :type id: string
    :param limit: the maximum number of datasets to return (optional)
    :type limit: int

    :rtype: list of dictionaries

    """
    _check_access("group_package_show", context, data_dict)

    group_id = _get_or_bust(data_dict, "id")

    limit = data_dict.get("limit", "")
    if limit:
        try:
            limit = int(limit)
            if limit < 0:
                raise logic.ValidationError(
                    {"message": "Limit must be a positive integer"}
                )
        except ValueError:
            raise logic.ValidationError({"message": "Limit must be a positive integer"})

    group = model.Group.get(group_id)
    if group is None:
        raise NotFound
    context["group"] = group

    _check_access("group_show", context, data_dict)

    result = logic.get_action("package_search")(
        context,
        {
            "fq": "groups:{0}".format(group.name),
            "rows": limit,
        },
    )

    return result["results"]


def _group_or_org_autocomplete(
    context: Context, data_dict: DataDict, is_org: bool
) -> list[dict[str, str]]:

    q = data_dict["q"]
    limit = data_dict.get("limit", 20)

    query = model.Group.search_by_name_or_title(
        q, group_type=None, is_org=is_org, limit=limit
    )

    group_list: list[dict[str, Any]] = []
    for group in query.all():
        result_dict = {}
        for k in ["id", "name", "title"]:
            result_dict[k] = getattr(group, k)
        group_list.append(result_dict)

    return group_list


@side_effect_free
def group_autocomplete(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupAutocomplete:
    """
    Return a list of group names that contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of groups to return (optional,
        default: 20)
    :type limit: int

    :rtype: a list of group dictionaries each with keys ``'name'``,
        ``'title'``, and ``'id'``
    """

    _check_access("group_autocomplete", context, data_dict)

    return _group_or_org_autocomplete(context, data_dict, is_org=False)


def _group_or_org_update(context: Context, data_dict: DataDict, is_org: bool = False):
    session = context["session"]
    id = _get_or_bust(data_dict, "id")

    group = model.Group.get(id)
    if group is None:
        raise NotFound(_("Group was not found."))
    context["group"] = group

    data_dict_type = data_dict.get("type")
    if data_dict_type is None:
        data_dict["type"] = group.type
    else:
        if data_dict_type != group.type:
            raise ValidationError({"type": _("Type cannot be updated")})

    # get the schema
    group_plugin = lib_plugins.lookup_group_plugin(group.type)

    if context.get("schema"):
        schema: Schema = context["schema"]
    else:
        schema: Schema = group_plugin.update_group_schema()

    upload = uploader.get_uploader("group")
    upload.update_data_dict(data_dict, "image_url", "image_upload", "clear_upload")

    if is_org:
        _check_access("organization_update", context, data_dict)
    else:
        _check_access("group_update", context, data_dict)

    data, errors = lib_plugins.plugin_validate(
        group_plugin,
        context,
        data_dict,
        schema,
        "organization_update" if is_org else "group_update",
    )

    group = context.get("group")
    log.debug(
        "group_update validate_errs=%r user=%s group=%s data_dict=%r",
        errors,
        context.get("user"),
        group.name if group else "",
        data_dict,
    )

    if errors:
        session.rollback()
        raise ValidationError(errors)

    contains_packages = "packages" in data_dict

    group = model_save.group_dict_save(
        data, context, prevent_packages_update=is_org or not contains_packages
    )

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.edit(group)

    upload.upload(uploader.get_max_image_size())

    if not context.get("defer_commit"):
        model.repo.commit()

    return model_dictize.group_dictize(group, context)


def group_update(context: Context, data_dict: DataDict) -> ActionResult.GroupUpdate:
    """Update a group.

    You must be authorized to edit the group.

    .. note:: Update methods may delete parameters not explicitly provided in the
        data_dict. If you want to edit only a specific attribute use `group_patch`
        instead.

    Plugins may change the parameters of this function depending on the value
    of the group's ``type`` attribute, see the
    :py:class:`~ckan.plugins.interfaces.IGroupForm` plugin interface.

    For further parameters see
    :py:func:`~ckan.logic.action.create.group_create`.

    Callers can choose to not specify packages, users or groups and they will be
    left at their existing values.

    :param id: the name or id of the group to update
    :type id: string

    :returns: the updated group
    :rtype: dictionary
    """
    return _group_or_org_update(context, data_dict)


def group_patch(context: Context, data_dict: DataDict) -> ActionResult.GroupPatch:
    """Patch a group

    :param id: the id or name of the group
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    """
    _check_access("group_patch", context, data_dict)

    show_context: Context = _fresh_context(context)

    group_dict = _get_action("group_show")(
        show_context, {"id": _get_or_bust(data_dict, "id")}
    )

    patched = dict(group_dict)
    patched.pop("display_name", None)
    patched.update(data_dict)

    patch_context = context.copy()
    return _get_action("group_update")(patch_context, patched)


def member_delete(context: Context, data_dict: DataDict) -> ActionResult.MemberDelete:
    """Remove an object (e.g. a user, dataset or group) from a group.

    You must be authorized to edit a group to remove objects from it.

    :param id: the id of the group
    :type id: string
    :param object: the id or name of the object to be removed
    :type object: string
    :param object_type: the type of the object to be removed, e.g. ``package``
        or ``user``
    :type object_type: string

    """
    group_id, obj_id, obj_type = _get_or_bust(
        data_dict, ["id", "object", "object_type"]
    )

    group = model.Group.get(group_id)
    if not group:
        raise NotFound("Group was not found.")

    obj_class = ckan.logic.model_name_to_class(model, obj_type)
    obj = obj_class.get(obj_id)
    if not obj:
        raise NotFound("%s was not found." % obj_type.title())

    _check_access("member_delete", context, data_dict)

    member = (
        model.Session.query(model.Member)
        .filter(model.Member.table_name == obj_type)
        .filter(model.Member.table_id == obj.id)
        .filter(model.Member.group_id == group.id)
        .filter(model.Member.state == "active")
        .first()
    )
    if member:
        member.delete()
        model.repo.commit()
        if isinstance(obj, model.Package):
            rebuild(obj.id)


def _group_or_org_delete(context: Context, data_dict: DataDict, is_org: bool = False):
    """Delete a group.

    You must be authorized to delete the group.

    :param id: the name or id of the group
    :type id: string

    """
    from sqlalchemy import or_

    id = _get_or_bust(data_dict, "id")

    group = model.Group.get(id)
    if group is None:
        raise NotFound("Group was not found.")
    context["group"] = group

    if is_org:
        _check_access("organization_delete", context, data_dict)
    else:
        _check_access("group_delete", context, data_dict)

    # organization delete will not occur while all datasets for that org are
    # not deleted
    if is_org:
        dataset_ids = (
            model.Session.query(model.Package.id)
            .filter_by(owner_org=group.id)
            .filter(model.Package.state != "deleted")
        )
        if dataset_ids.count():
            if not authz.check_config_permission("ckan.auth.create_unowned_dataset"):
                raise ValidationError(
                    {
                        "message": _(
                            "Organization cannot be deleted while it still has datasets"
                        )
                    }
                )

            for d in dataset_ids:
                _get_action("package_patch")(
                    ckan.logic.fresh_context(context), {"id": d, "owner_org": ""}
                )

    # The group's Member objects are deleted
    # (including hierarchy connections to parent and children groups)
    for member in (
        model.Session.query(model.Member)
        .filter(or_(model.Member.table_id == id, model.Member.group_id == id))
        .filter(model.Member.state == "active")
        .all()
    ):
        member.delete()
        if not is_org and member.table_name == "package":
            assert member.table_id
            ckan.logic.index_update_package(context, member.table_id)

    group.delete()

    if is_org:
        plugin_type = plugins.IOrganizationController
    else:
        plugin_type = plugins.IGroupController

    for item in plugins.PluginImplementations(plugin_type):
        item.delete(group)

    model.repo.commit()


def group_delete(context: Context, data_dict: DataDict) -> ActionResult.GroupDelete:
    """Delete a group.

    You must be authorized to delete the group.

    :param id: the name or id of the group
    :type id: string

    """
    return _group_or_org_delete(context, data_dict)


def _group_or_org_purge(context: Context, data_dict: DataDict, is_org: bool = False):
    """Purge a group or organization.

    The group or organization will be completely removed from the database.
    This cannot be undone!

    Only sysadmins can purge groups or organizations.

    :param id: the name or id of the group or organization to be purged
    :type id: string

    :param is_org: you should pass is_org=True if purging an organization,
        otherwise False (optional, default: False)
    :type is_org: bool

    """
    id = _get_or_bust(data_dict, "id")

    group = model.Group.get(id)
    if group is None:
        if is_org:
            raise NotFound("Organization was not found")
        else:
            raise NotFound("Group was not found")
    context["group"] = group

    if is_org:
        _check_access("organization_purge", context, data_dict)
    else:
        _check_access("group_purge", context, data_dict)

    if is_org:
        # Clear the owner_org field
        dataset_ids = (
            model.Session.query(model.Package.id)
            .filter_by(owner_org=group.id)
            .filter(model.Package.state != "deleted")
        )
        if dataset_ids.count():
            if not authz.check_config_permission("ckan.auth.create_unowned_dataset"):
                raise ValidationError(
                    {
                        "message": "Organization cannot be purged while it "
                        "still has datasets"
                    }
                )
            for d in dataset_ids:
                _get_action("package_patch")(
                    ckan.logic.fresh_context(context), {"id": d, "owner_org": ""}
                )

    # Delete related Memberships
    members = model.Session.query(model.Member).filter(
        sqla.or_(model.Member.group_id == group.id, model.Member.table_id == group.id)
    )
    reindex = set()
    if members.count() > 0:
        for m in members.all():
            m.purge()
            if not is_org and m.table_name == "package":
                reindex.add(m.table_id)
        model.repo.commit_and_remove()

    if reindex:
        for r in reindex:
            ckan.logic.index_update_package(context, r)

    group = model.Group.get(id)
    assert group
    group.purge()
    model.repo.commit_and_remove()


def group_purge(context: Context, data_dict: DataDict) -> None:
    """Purge a group.

    .. warning:: Purging a group cannot be undone!

    Purging a group completely removes the group from the CKAN database,
    whereas deleting a group simply marks the group as deleted (it will no
    longer show up in the frontend, but is still in the db).

    Datasets in the group will remain, just not in the purged group.

    You must be authorized to purge the group.

    :param id: the name or id of the group to be purged
    :type id: string

    """
    return _group_or_org_purge(context, data_dict, is_org=False)


def _group_or_org_member_delete(context: Context, data_dict: DataDict) -> None:
    user = context["user"]

    group_id = data_dict.get("id")
    group = model.Group.get(group_id)
    user_id = data_dict.get("username")
    user_id = data_dict.get("user_id") if user_id is None else user_id
    assert group
    member_dict = {
        "id": group.id,
        "object": user_id,
        "object_type": "user",
    }
    member_context: Context = {"user": user}
    _get_action("member_delete")(member_context, member_dict)


def group_member_delete(context: Context, data_dict: DataDict) -> None:
    """Remove a user from a group.

    You must be authorized to edit the group.

    :param id: the id or name of the group
    :type id: string
    :param username: name or id of the user to be removed
    :type username: string

    """
    _check_access("group_member_delete", context, data_dict)
    return _group_or_org_member_delete(context, data_dict)
