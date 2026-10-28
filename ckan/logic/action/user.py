from __future__ import annotations

import logging
import random
import re
from socket import error as socket_error
from typing import Any, Optional, Type

from sqlalchemy import case as _case
from sqlalchemy import func as _func
from sqlalchemy import or_ as _or_
from sqlalchemy.sql import select as _select

from ckan import authz, logic, model, plugins
from ckan.common import _, asbool, config
from ckan.lib import api_token, mailer, maintain, signals, uploader
from ckan.lib.dictization import model_dictize, model_save
from ckan.lib.navl.dictization_functions import validate
from ckan.lib.navl.dictization_functions import validate as _validate
from ckan.logic import (
    NotAuthorized,
    NotFound,
    ValidationError,
    side_effect_free,
)
from ckan.logic import check_access as _check_access
from ckan.logic import fresh_context as _fresh_context
from ckan.logic import get_action as _get_action
from ckan.logic import get_or_bust as _get_or_bust
from ckan.logic import schema as schema_
from ckan.model.follower import ModelFollowingModel
from ckan.types import ActionResult, Context, DataDict, Query, Schema

log = logging.getLogger("ckan.logic")


def user_create(context: Context, data_dict: DataDict) -> ActionResult.UserCreate:
    """Create a new user.

    You must be authorized to create users.

    :param name: the name of the new user, a string between 2 and 100
        characters in length, containing only lowercase alphanumeric
        characters, ``-`` and ``_``
    :type name: string
    :param email: the email address for the new user
    :type email: string
    :param password: the password of the new user, a string of at least 4
        characters
    :type password: string
    :param id: the id of the new user (optional)
    :type id: string
    :param fullname: the full name of the new user (optional)
    :type fullname: string
    :param about: a description of the new user (optional)
    :type about: string
    :param image_url: the URL to an image to be displayed on the user's page
        (optional)
    :type image_url: string
    :param plugin_extras: private extra user data belonging to plugins.
        Only sysadmin users may set this value. It should be a dict that can
        be dumped into JSON, and plugins should namespace their extras with
        the plugin name to avoid collisions with other plugins, eg::

            {
                "name": "test_user",
                "email": "test@example.com",
                "plugin_extras": {
                    "my_plugin": {
                        "private_extra": 1
                    },
                    "another_plugin": {
                        "another_extra": True
                    }
                }
            }
    :type plugin_extras: dict
    :param with_apitoken: whether to create an API token for the user.
                    (Optional)
    :type with_apitoken: bool

    :returns: the newly created user
    :rtype: dictionary

    """
    schema = context.get("schema") or schema_.default_user_schema()
    session = context["session"]
    with_apitoken = data_dict.pop("with_apitoken", False)

    _check_access("user_create", context, data_dict)

    author_obj = model.User.get(context.get("user"))
    if data_dict.get("id"):
        is_sysadmin = author_obj and author_obj.sysadmin
        ignore_auth = context.get("ignore_auth")
        if not (ignore_auth or is_sysadmin) or model.User.get(data_dict["id"]):
            data_dict.pop("id", None)
    context.pop("user_obj", None)

    upload = uploader.get_uploader("user")
    upload.update_data_dict(data_dict, "image_url", "image_upload", "clear_upload")
    data, errors = _validate(data_dict, schema, context)

    if errors:
        session.rollback()
        raise ValidationError(errors)

    # user schema prevents non-sysadmins from providing password_hash
    if "password_hash" in data:
        data["_password"] = data.pop("password_hash")

    user = model_save.user_dict_save(data, context)
    signals.user_created.send(user.name, user=user)

    upload.upload(uploader.get_max_image_size())

    if not context.get("defer_commit"):
        with logic.guard_against_duplicated_email(data["email"]):
            model.repo.commit()
    else:
        # The Dashboard object below needs the user id, and if we didn't
        # commit we need to flush the session in order to populate it
        session.flush()

    # A new context is required for dictizing the newly constructed user in
    # order that all the new user's data is returned, in particular, the
    # api_key.
    #
    # The context is copied so as not to clobber the caller's context dict.
    user_dictize_context = context.copy()
    user_dictize_context["keep_apikey"] = True
    user_dictize_context["keep_email"] = True

    include_plugin_extras = False
    if author_obj:
        include_plugin_extras = author_obj.sysadmin and "plugin_extras" in data
    user_dict = model_dictize.user_dictize(
        user, user_dictize_context, include_plugin_extras=include_plugin_extras
    )

    context["user_obj"] = user
    context["id"] = user.id

    # Create dashboard for user.
    dashboard = model.Dashboard(user.id)

    session.add(dashboard)
    if not context.get("defer_commit"):
        model.repo.commit()

    if with_apitoken:
        if not context["user"]:
            context["user"] = user.name

        # Create apitoken for user.
        api_token = _get_action("api_token_create")(
            context, {"user": user.name, "name": "default"}
        )
        user_dict["token"] = api_token["token"]

    log.debug("Created user %s", user.name)
    return user_dict


def user_invite(context: Context, data_dict: DataDict) -> ActionResult.UserInvite:
    """Invite a new user.

    You must be authorized to create group members.

    :param email: the email of the user to be invited to the group
    :type email: string
    :param group_id: the id or name of the group
    :type group_id: string
    :param role: role of the user in the group. One of ``member``, ``editor``,
        or ``admin``
    :type role: string

    :returns: the newly created user
    :rtype: dictionary
    """
    _check_access("user_invite", context, data_dict)

    schema = context.get("schema", schema_.default_user_invite_schema())
    data, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    group = model.Group.get(data["group_id"])
    if not group:
        raise NotFound()

    name = _get_random_username_from_email(data["email"])

    data["name"] = name
    # send the proper schema when creating a user from here
    # so the password field would be ignored.
    invite_schema = schema_.create_user_for_user_invite_schema()

    data["state"] = model.State.PENDING
    user_dict = _get_action("user_create")(
        Context(context, schema=invite_schema, ignore_auth=True), data
    )
    user = model.User.get(user_dict["id"])
    assert user
    member_dict = {"username": user.id, "id": data["group_id"], "role": data["role"]}

    org_or_group = "organization" if group.is_organization else "group"
    _get_action(f"{org_or_group}_member_create")(context, member_dict)
    group_dict = _get_action(f"{org_or_group}_show")(context, {"id": data["group_id"]})

    try:
        notification_sent = False
        for plugin in plugins.PluginImplementations(plugins.INotifier):
            notification_sent = plugin.notify_about_topic(
                notification_sent,
                "user_invited",
                {"user": user, "group": group_dict, "role": data["role"]},
            )
        if not notification_sent:
            mailer.send_invite(user, group_dict, data["role"])
    except (socket_error, mailer.MailerException) as error:
        # Email could not be sent, delete the pending user

        _get_action("user_delete")(context, {"id": user.id})

        message = _(
            "Error sending the invite email, the user was not created: {0}"
        ).format(error)
        raise ValidationError(message)

    return model_dictize.user_dictize(user, context)


def _get_random_username_from_email(email: str):
    localpart = email.split("@")[0]
    cleaned_localpart = re.sub(r"[^\w]", "-", localpart).lower()

    # if we can't create a unique user name within this many attempts
    # then something else is probably wrong and we should give up
    max_name_creation_attempts = 100

    for _i in range(max_name_creation_attempts):
        random_number = random.SystemRandom().random() * 10000
        name = "%s-%d" % (cleaned_localpart, random_number)
        if not model.User.get(name):
            return name

    return cleaned_localpart


def follow_user(context: Context, data_dict: DataDict) -> ActionResult.FollowUser:
    """Start following another user.

    You must provide your API key in the Authorization header.

    :param id: the id or name of the user to follow, e.g. ``'joeuser'``
    :type id: string

    :returns: a representation of the 'follower' relationship between yourself
        and the other user
    :rtype: dictionary

    """
    _check_access("follow_user", context, data_dict)

    userobj = model.User.get(context["user"])
    if not userobj:
        raise NotFound(_("User not found"))

    schema = context.get("schema", schema_.default_follow_user_schema())

    validated_data_dict, errors = _validate(data_dict, schema, context)

    if errors:
        msg = _("Error validating the schema of the user to follow.")
        raise ValidationError(msg)

    # Don't let a user follow herself.
    if userobj.id == validated_data_dict["id"]:
        message = _("You cannot follow yourself")
        raise ValidationError({"message": message})

    # If the user is already following, return the existing follower object
    follower = model.UserFollowingUser.get(userobj.id, validated_data_dict["id"])
    if follower:
        return model_dictize.user_following_user_dictize(follower, context)

    follower = model_save.follower_dict_save(
        validated_data_dict, context, model.UserFollowingUser
    )

    if not context.get("defer_commit"):
        model.repo.commit()

    log.debug(
        "User %s started following user %s", follower.follower_id, follower.object_id
    )

    return model_dictize.user_following_user_dictize(follower, context)


def follow_dataset(context: Context, data_dict: DataDict) -> ActionResult.FollowDataset:
    """Start following a dataset.

    You must provide your API key in the Authorization header.

    :param id: the id or name of the dataset to follow, e.g. ``'warandpeace'``
    :type id: string

    :returns: a representation of the 'follower' relationship between yourself
        and the dataset
    :rtype: dictionary

    """
    _check_access("follow_dataset", context, data_dict)

    userobj = model.User.get(context["user"])
    if not userobj:
        raise NotFound(_("User not found"))

    schema = context.get("schema") or schema_.default_follow_dataset_schema()
    validated_data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        message = _("Error validating the schema of the dataset to follow.")
        raise ValidationError({"message": message})

    # If the user is already following, return the existing follower object.
    follower = model.UserFollowingDataset.get(userobj.id, validated_data_dict["id"])
    if follower:
        return model_dictize.user_following_dataset_dictize(follower, context)

    follower = model_save.follower_dict_save(
        validated_data_dict, context, model.UserFollowingDataset
    )

    if not context.get("defer_commit"):
        model.repo.commit()

    log.debug(
        "User %s started following dataset %s", follower.follower_id, follower.object_id
    )

    return model_dictize.user_following_dataset_dictize(follower, context)


def follow_group(context: Context, data_dict: DataDict) -> ActionResult.FollowGroup:
    """Start following a group.

    You must provide your API key in the Authorization header.

    :param id: the id or name of the group to follow, e.g. ``'roger'``
    :type id: string

    :returns: a representation of the 'follower' relationship between yourself
        and the group
    :rtype: dictionary

    """
    _check_access("follow_group", context, data_dict)

    userobj = model.User.get(context["user"])
    if not userobj:
        raise NotFound(_("User not found"))

    schema = context.get("schema", schema_.default_follow_group_schema())
    validated_data_dict, errors = _validate(data_dict, schema, context)

    if errors:
        message = _("Error validating the schema of the group to follow.")
        raise ValidationError({"message": message})

    # If it's already following, return the existing follower object.
    follower = model.UserFollowingGroup.get(userobj.id, validated_data_dict["id"])
    if follower:
        return model_dictize.user_following_group_dictize(follower, context)

    follower = model_save.follower_dict_save(
        validated_data_dict, context, model.UserFollowingGroup
    )

    if not context.get("defer_commit"):
        model.repo.commit()

    log.debug(
        "User %s started following group %s", follower.follower_id, follower.object_id
    )

    return model_dictize.user_following_group_dictize(follower, context)


def api_token_create(
    context: Context, data_dict: DataDict
) -> ActionResult.ApiTokenCreate:
    """Create new API Token for current user.

    Apart from the `user` and `name` field that are required by
    default implementation, there may be additional fields registered
    by extensions.

    :param user: name or id of the user who owns new API Token
    :type user: string
    :param name: distinctive name for API Token
    :type name: string
    :param created_at: datetime string for when the API Token was made.
        Only sysadmin users may set this value, used for data migrations.
    :type created_at: timestamp
    :param id: UUID of the API Token (a.k.a the encoded token).
        Only sysadmin users may set this value, used for data migrations.
    :type id: string
    :param last_access: datetime string for when the API Token was last used.
        Only sysadmin users may set this value, used for data migrations.
    :type last_access: timestamp

    :returns: Returns a dict with the key "token" containing the
              encoded token value. Extensions can provide additional
              fields via `add_extra` method of
              :py:class:`~ckan.plugins.interfaces.IApiToken`
    :rtype: dictionary

    """
    user, _name = _get_or_bust(data_dict, ["user", "name"])

    if model.User.get(user) is None:
        raise NotFound("User not found")

    _check_access("api_token_create", context, data_dict)

    schema = context.get("schema")
    if not schema:
        schema = api_token.get_schema()

    validated_data_dict, errors = _validate(data_dict, schema, context)

    if errors:
        raise ValidationError(errors)

    token_obj = model_save.api_token_save(validated_data_dict, context)
    model.Session.commit()
    data = {"jti": token_obj.id, "iat": api_token.into_seconds(token_obj.created_at)}

    data = api_token.postprocess(data, token_obj.id, validated_data_dict)
    token = api_token.encode(data)

    result = api_token.add_extra({"token": token, "id": token_obj.id})
    return result


@side_effect_free
def user_list(context: Context, data_dict: DataDict) -> ActionResult.UserList:  # noqa: C901
    """Return a list of the site's user accounts.

    :param q: filter the users returned to those whose names contain a string
      (optional)
    :type q: string
    :param email: filter the users returned to those whose email match a
      string (optional) (you must be a sysadmin to use this filter)
    :type email: string
    :param order_by: which field to sort the list by (optional, default:
      ``'display_name'``). Users can be sorted by ``'id'``, ``'name'``,
      ``'fullname'``, ``'display_name'``, ``'created'``, ``'about'``,
      ``'sysadmin'`` or ``'number_created_packages'``.
    :type order_by: string
    :param all_fields: return full user dictionaries instead of just names.
      (optional, default: ``True``)
    :type all_fields: bool
    :param include_site_user: add site_user to the result
      (optional, default: ``False``)
    :type include_site_user: bool

    :rtype: list of user dictionaries. User properties include:
      ``number_created_packages`` which excludes datasets which are private
      or draft state.

    """
    _check_access("user_list", context, data_dict)

    q = data_dict.get("q", "")
    email = data_dict.get("email")
    order_by = data_dict.get("order_by", "display_name")
    all_fields = asbool(data_dict.get("all_fields", True))

    if all_fields:
        query: "Query[Any]" = model.Session.query(
            model.User,
            model.User.name.label("name"),
            model.User.fullname.label("fullname"),
            model.User.about.label("about"),
            model.User.email.label("email"),
            model.User.created.label("created"),
            _select(_func.count(model.Package.id))
            .where(
                model.Package.creator_user_id == model.User.id,
                model.Package.state == "active",
                model.Package.private == False,  # noqa: E712
            )
            .label("number_created_packages"),
        )
    else:
        query = model.Session.query(model.User.name)

    if not asbool(data_dict.get("include_site_user", False)):
        site_id = config.get("ckan.site_id")
        query = query.filter(model.User.name != site_id)

    if q:
        query = model.User.search(q, query, user_name=context.get("user"))
    if email:
        query = query.filter(_func.lower(model.User.email) == email.lower())

    order_by_field = None
    if order_by == "edits":
        raise ValidationError({"message": "order_by=edits is no longer supported"})
    elif order_by == "number_created_packages":
        order_by_field = order_by
    elif order_by != "display_name":
        try:
            order_by_field = getattr(model.User, order_by)
        except AttributeError:
            pass
    if order_by == "display_name" or order_by_field is None:
        query = query.order_by(
            _case(
                (
                    _or_(model.User.fullname.is_(None), model.User.fullname == ""),
                    model.User.name,
                ),
                else_=model.User.fullname,
            )
        )
    elif (
        order_by_field == "number_created_packages"
        or order_by_field == "fullname"
        or order_by_field == "about"
        or order_by_field == "sysadmin"
    ):
        query = query.order_by(order_by_field, model.User.name)
    else:
        query = query.order_by(order_by_field)

    # Filter deleted users
    query = query.filter(model.User.state != model.State.DELETED)

    ## hack for pagination
    if context.get("return_query"):
        return query

    users_list: ActionResult.UserList = []

    if all_fields:
        for user in query.all():
            result_dict: Any = model_dictize.user_dictize(user[0], context)
            users_list.append(result_dict)
    else:
        for user in query.all():
            users_list.append(user[0])

    return users_list


@side_effect_free
def user_show(context: Context, data_dict: DataDict) -> ActionResult.UserShow:
    """Return a user account.

    Either the ``id`` should be passed or the user should be logged in.

    :param id: the id or name of the user (optional)
    :type id: string
    :param include_datasets: Include a list of datasets the user has created.
        If it is the same user or a sysadmin requesting, it includes datasets
        that are draft or private.
        (optional, default:``False``, limit:50)
    :type include_datasets: bool
    :param include_num_followers: Include the number of followers the user has
        (optional, default:``False``)
    :type include_num_followers: bool
    :param include_password_hash: Include the stored password hash
        (sysadmin only, optional, default:``False``)
    :type include_password_hash: bool
    :param include_plugin_extras: Include the internal plugin extras object
        (sysadmin only, optional, default:``False``)
    :type include_plugin_extras: bool


    :returns: the details of the user. Includes email_hash and
        number_created_packages (which excludes draft or private datasets
        unless it is the same user or sysadmin making the request). Excludes
        the password (hash) and reset_key. If it is the same user or a
        sysadmin requesting, the email and apikey are included.
    :rtype: dictionary

    """
    if "user" in context and "id" not in data_dict:
        data_dict["id"] = context.get("user")

    id = data_dict.get("id", None)
    if id:
        user_obj = model.User.get(id)
    else:
        user_obj = None

    if user_obj:
        context["user_obj"] = user_obj

    _check_access("user_show", context, data_dict)

    if not user_obj:
        raise NotFound

    # include private and draft datasets?
    requester = context.get("user")
    sysadmin = False
    if requester:
        sysadmin = authz.is_sysadmin(requester)
        requester_looking_at_own_account = requester == user_obj.name
        include_private_and_draft_datasets = (
            sysadmin or requester_looking_at_own_account
        )
    else:
        include_private_and_draft_datasets = False
    context["count_private_and_draft_datasets"] = include_private_and_draft_datasets

    include_password_hash = sysadmin and asbool(
        data_dict.get("include_password_hash", False)
    )

    include_plugin_extras = sysadmin and asbool(
        data_dict.get("include_plugin_extras", False)
    )

    user_dict = model_dictize.user_dictize(
        user_obj, context, include_password_hash, include_plugin_extras
    )

    if asbool(data_dict.get("include_datasets", False)):
        user_dict["datasets"] = []

        fq = "+creator_user_id:{0}".format(user_dict["id"])

        search_dict: dict[str, Any] = {"rows": 50}

        if include_private_and_draft_datasets:
            search_dict.update({"include_private": True, "include_drafts": True})

        search_dict.update({"fq": fq})

        user_dict["datasets"] = logic.get_action("package_search")(
            context, search_dict
        ).get("results")

    if asbool(data_dict.get("include_num_followers", False)):
        user_dict["num_followers"] = logic.get_action("user_follower_count")(
            {"session": model.Session}, {"id": user_dict["id"]}
        )

    return user_dict


@side_effect_free
@logic.validate(schema_.default_autocomplete_schema)
def user_autocomplete(
    context: Context, data_dict: DataDict
) -> ActionResult.UserAutocomplete:
    """Return a list of user names that contain a string.

    :param q: the string to search for
    :type q: string
    :param limit: the maximum number of user names to return (optional,
        default: ``20``)
    :type limit: int

    :rtype: a list of user dictionaries each with keys ``'name'``,
        ``'fullname'``, and ``'id'``

    """
    user = context["user"]

    _check_access("user_autocomplete", context, data_dict)

    q = data_dict["q"]
    limit = data_dict.get("limit", 20)
    ignore_self = data_dict.get("ignore_self", False)

    query = model.User.search(q, user_name=user)
    query = query.filter(model.User.state != model.State.DELETED)

    if ignore_self:
        query = query.filter(model.User.name != user)

    query = query.limit(limit)

    user_list: ActionResult.UserAutocomplete = []
    for user in query.all():
        result_dict = {}
        for k in ["id", "name", "fullname"]:
            result_dict[k] = getattr(user, k)

        user_list.append(result_dict)

    return user_list


def _follower_count(
    context: Context,
    data_dict: DataDict,
    default_schema: Schema,
    ModelClass: Type["ModelFollowingModel[Any, Any]"],
):
    schema = context.get("schema", default_schema)
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)
    return ModelClass.follower_count(data_dict["id"])


@side_effect_free
def user_follower_count(
    context: Context, data_dict: DataDict
) -> ActionResult.UserFollowerCount:
    """Return the number of followers of a user.

    :param id: the id or name of the user
    :type id: string

    :rtype: int

    """
    _check_access("user_follower_count", context, data_dict)
    return _follower_count(
        context,
        data_dict,
        schema_.default_follow_user_schema(),
        model.UserFollowingUser,
    )


@side_effect_free
def dataset_follower_count(
    context: Context, data_dict: DataDict
) -> ActionResult.DatasetFollowerCount:
    """Return the number of followers of a dataset.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: int

    """
    _check_access("dataset_follower_count", context, data_dict)
    return _follower_count(
        context,
        data_dict,
        schema_.default_follow_dataset_schema(),
        model.UserFollowingDataset,
    )


@side_effect_free
def group_follower_count(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupFollowerCount:
    """Return the number of followers of a group.

    :param id: the id or name of the group
    :type id: string

    :rtype: int

    """
    _check_access("group_follower_count", context, data_dict)
    return _follower_count(
        context,
        data_dict,
        schema_.default_follow_group_schema(),
        model.UserFollowingGroup,
    )


@side_effect_free
def organization_follower_count(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationFollowerCount:
    """Return the number of followers of an organization.

    :param id: the id or name of the organization
    :type id: string

    :rtype: int

    """
    _check_access("organization_follower_count", context, data_dict)
    return group_follower_count(context, data_dict)


def _follower_list(
    context: Context,
    data_dict: DataDict,
    default_schema: Schema,
    FollowerClass: Type["ModelFollowingModel[Any, Any]"],
):
    schema = context.get("schema", default_schema)
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    # Get the list of Follower objects.
    object_id = data_dict.get("id")
    followers = FollowerClass.follower_list(object_id)

    # Convert the list of Follower objects to a list of User objects.
    users = [model.User.get(follower.follower_id) for follower in followers]
    users = [user for user in users if user is not None]

    # Dictize the list of User objects.
    return model_dictize.user_list_dictize(users, context)


@side_effect_free
def user_follower_list(
    context: Context, data_dict: DataDict
) -> ActionResult.UserFollowerList:
    """Return the list of users that are following the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    """
    _check_access("user_follower_list", context, data_dict)
    return _follower_list(
        context,
        data_dict,
        schema_.default_follow_user_schema(),
        model.UserFollowingUser,
    )


@side_effect_free
def dataset_follower_list(
    context: Context, data_dict: DataDict
) -> ActionResult.DatasetFollowerList:
    """Return the list of users that are following the given dataset.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: list of dictionaries

    """
    _check_access("dataset_follower_list", context, data_dict)
    return _follower_list(
        context,
        data_dict,
        schema_.default_follow_dataset_schema(),
        model.UserFollowingDataset,
    )


@side_effect_free
def group_follower_list(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupFollowerList:
    """Return the list of users that are following the given group.

    :param id: the id or name of the group
    :type id: string

    :rtype: list of dictionaries

    """
    _check_access("group_follower_list", context, data_dict)
    return _follower_list(
        context,
        data_dict,
        schema_.default_follow_group_schema(),
        model.UserFollowingGroup,
    )


@side_effect_free
def organization_follower_list(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationFollowerList:
    """Return the list of users that are following the given organization.

    :param id: the id or name of the organization
    :type id: string

    :rtype: list of dictionaries

    """
    _check_access("organization_follower_list", context, data_dict)
    return _follower_list(
        context,
        data_dict,
        schema_.default_follow_group_schema(),
        model.UserFollowingGroup,
    )


def _am_following(
    context: Context,
    data_dict: DataDict,
    default_schema: Schema,
    FollowerClass: Type["ModelFollowingModel[Any, Any]"],
):
    schema = context.get("schema", default_schema)
    data_dict, errors = _validate(data_dict, schema, context)
    if errors:
        raise ValidationError(errors)

    if "user" not in context:
        raise NotAuthorized

    userobj = model.User.get(context["user"])
    if not userobj:
        raise NotAuthorized

    object_id: Optional[str] = data_dict.get("id")

    return FollowerClass.is_following(userobj.id, object_id)


@side_effect_free
def am_following_user(
    context: Context, data_dict: DataDict
) -> ActionResult.AmFollowingUser:
    """Return ``True`` if you're following the given user, ``False`` if not.

    :param id: the id or name of the user
    :type id: string

    :rtype: bool

    """
    _check_access("am_following_user", context, data_dict)
    return _am_following(
        context,
        data_dict,
        schema_.default_follow_user_schema(),
        model.UserFollowingUser,
    )


@side_effect_free
def am_following_dataset(
    context: Context, data_dict: DataDict
) -> ActionResult.AmFollowingDataset:
    """Return ``True`` if you're following the given dataset, ``False`` if not.

    :param id: the id or name of the dataset
    :type id: string

    :rtype: bool

    """
    _check_access("am_following_dataset", context, data_dict)
    return _am_following(
        context,
        data_dict,
        schema_.default_follow_dataset_schema(),
        model.UserFollowingDataset,
    )


@side_effect_free
def am_following_group(
    context: Context, data_dict: DataDict
) -> ActionResult.AmFollowingGroup:
    """Return ``True`` if you're following the given group, ``False`` if not.

    :param id: the id or name of the group
    :type id: string

    :rtype: bool

    """
    _check_access("am_following_group", context, data_dict)
    return _am_following(
        context,
        data_dict,
        schema_.default_follow_group_schema(),
        model.UserFollowingGroup,
    )


def _followee_count(
    context: Context,
    data_dict: DataDict,
    FollowerClass: Type["ModelFollowingModel[Any ,Any]"],
    is_org: bool = False,
) -> int:
    if not context.get("skip_validation"):
        schema = context.get("schema", schema_.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)

    followees = _group_or_org_followee_list(context, data_dict, is_org)

    return len(followees)


@side_effect_free
def followee_count(context: Context, data_dict: DataDict) -> ActionResult.FolloweeCount:
    """Return the number of objects that are followed by the given user.

    Counts all objects, of any type, that the given user is following
    (e.g. followed users, followed datasets, followed groups).

    :param id: the id of the user
    :type id: string

    :rtype: int

    """
    _check_access("followee_count", context, data_dict)
    followee_users = _followee_count(context, data_dict, model.UserFollowingUser)

    # followee_users has validated data_dict so the following functions don't
    # need to validate it again.
    context["skip_validation"] = True

    followee_datasets = _followee_count(context, data_dict, model.UserFollowingDataset)
    followee_groups = _followee_count(context, data_dict, model.UserFollowingGroup)

    return sum((followee_users, followee_datasets, followee_groups))


@side_effect_free
def user_followee_count(
    context: Context, data_dict: DataDict
) -> ActionResult.UserFolloweeCount:
    """Return the number of users that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    """
    _check_access("user_followee_count", context, data_dict)
    return _followee_count(context, data_dict, model.UserFollowingUser)


@side_effect_free
def dataset_followee_count(
    context: Context, data_dict: DataDict
) -> ActionResult.DatasetFolloweeCount:
    """Return the number of datasets that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    """
    _check_access("dataset_followee_count", context, data_dict)
    return _followee_count(context, data_dict, model.UserFollowingDataset)


@side_effect_free
def group_followee_count(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupFolloweeCount:
    """Return the number of groups that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    """
    _check_access("group_followee_count", context, data_dict)
    return _followee_count(context, data_dict, model.UserFollowingGroup, is_org=False)


@side_effect_free
def organization_followee_count(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationFolloweeCount:
    """Return the number of organizations that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: int

    """
    _check_access("organization_followee_count", context, data_dict)
    return _followee_count(context, data_dict, model.UserFollowingGroup, is_org=True)


@side_effect_free
@logic.validate(schema_.default_follow_user_schema)
def followee_list(context: Context, data_dict: DataDict) -> ActionResult.FolloweeList:
    """Return the list of objects that are followed by the given user.

    Returns all objects, of any type, that the given user is following
    (e.g. followed users, followed datasets, followed groups.. ).

    :param id: the id of the user
    :type id: string

    :param q: a query string to limit results by, only objects whose display
        name begins with the given string (case-insensitive) will be returned
        (optional)
    :type q: string

    :rtype: list of dictionaries, each with keys ``'type'`` (e.g. ``'user'``,
        ``'dataset'`` or ``'group'``), ``'display_name'`` (e.g. a user's
        display name, or a package's title) and ``'dict'`` (e.g. a dict
        representing the followed user, package or group, the same as the dict
        that would be returned by :py:func:`user_show`,
        :py:func:`package_show` or :py:func:`group_show`)

    """
    _check_access("followee_list", context, data_dict)

    def display_name(followee: dict[str, Any]) -> Optional[str]:
        """Return a display name for the given user, group or dataset dict."""
        display_name = followee.get("display_name")
        fullname = followee.get("fullname")
        title = followee.get("title")
        name = followee.get("name")
        return display_name or fullname or title or name

    # Get the followed objects.
    # TODO: Catch exceptions raised by these *_followee_list() functions?
    # FIXME should we be changing the context like this it seems dangerous
    followee_dicts: ActionResult.FolloweeList = []
    context["skip_validation"] = True
    context["ignore_auth"] = True
    for followee_list_function, followee_type in (
        (user_followee_list, "user"),
        (dataset_followee_list, "dataset"),
        (group_followee_list, "group"),
        (organization_followee_list, "organization"),
    ):
        dicts = followee_list_function(context, data_dict)
        for d in dicts:
            followee_dicts.append(
                {"type": followee_type, "display_name": display_name(d), "dict": d}
            )

    followee_dicts.sort(key=lambda d: d["display_name"])

    q = data_dict.get("q")
    if q:
        q = q.strip().lower()
        matching_followee_dicts = []
        for followee_dict in followee_dicts:
            if followee_dict["display_name"].strip().lower().startswith(q):
                matching_followee_dicts.append(followee_dict)
        followee_dicts = matching_followee_dicts

    return followee_dicts


@side_effect_free
def user_followee_list(
    context: Context, data_dict: DataDict
) -> ActionResult.UserFolloweeList:
    """Return the list of users that are followed by the given user.

    :param id: the id of the user
    :type id: string

    :rtype: list of dictionaries

    """
    _check_access("user_followee_list", context, data_dict)

    if not context.get("skip_validation"):
        schema = context.get("schema") or (schema_.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)

    # Get the list of Follower objects.
    user_id = _get_or_bust(data_dict, "id")
    followees = model.UserFollowingUser.followee_list(user_id)

    # Convert the list of Follower objects to a list of User objects.
    users = [model.User.get(followee.object_id) for followee in followees]
    users = [user for user in users if user is not None]

    # Dictize the list of User objects.
    return model_dictize.user_list_dictize(users, context)


@side_effect_free
def dataset_followee_list(
    context: Context, data_dict: DataDict
) -> ActionResult.DatasetFolloweeList:
    """Return the list of datasets that are followed by the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    """
    _check_access("dataset_followee_list", context, data_dict)

    if not context.get("skip_validation"):
        schema = context.get("schema") or (schema_.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)

    # Get the list of Follower objects.
    user_id = _get_or_bust(data_dict, "id")
    followees = model.UserFollowingDataset.followee_list(user_id)

    # Convert the list of Follower objects to a list of Package objects.
    datasets = [model.Package.get(followee.object_id) for followee in followees]
    datasets = [dataset for dataset in datasets if dataset is not None]

    # Safety check: check which datasets the user can actually access
    check_context = logic.fresh_context(context, ignore_auth=False)
    datasets = [
        dataset
        for dataset in datasets
        if authz.is_authorized_boolean(
            "package_show", check_context, {"id": dataset.id}
        )
    ]

    # Dictize the list of Package objects.
    return [model_dictize.package_dictize(dataset, context) for dataset in datasets]


@side_effect_free
def group_followee_list(
    context: Context, data_dict: DataDict
) -> ActionResult.GroupFolloweeList:
    """Return the list of groups that are followed by the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    """
    _check_access("group_followee_list", context, data_dict)

    return _group_or_org_followee_list(context, data_dict, is_org=False)


@side_effect_free
def organization_followee_list(
    context: Context, data_dict: DataDict
) -> ActionResult.OrganizationFolloweeList:
    """Return the list of organizations that are followed by the given user.

    :param id: the id or name of the user
    :type id: string

    :rtype: list of dictionaries

    """

    _check_access("organization_followee_list", context, data_dict)

    return _group_or_org_followee_list(context, data_dict, is_org=True)


@side_effect_free
def api_token_list(context: Context, data_dict: DataDict) -> ActionResult.ApiTokenList:
    """Return list of all available API Tokens for current user.

    :param string user_id: The user ID or name

    :returns: collection of all API Tokens from oldest to newest
    :rtype: list

    .. versionadded:: 2.9
    """
    # Support "user" for backwards compatibility
    id_or_name = data_dict.get("user_id", data_dict.get("user"))
    if not id_or_name:
        raise ValidationError({"user_id": ["Missing value"]})

    _check_access("api_token_list", context, data_dict)
    user = model.User.get(id_or_name)
    if user is None:
        raise NotFound("User not found")
    tokens = model.Session.query(model.ApiToken).filter_by(user_id=user.id)
    tokens = tokens.order_by(model.ApiToken.created_at)
    return model_dictize.api_token_list_dictize(tokens, context)


def _group_or_org_followee_list(
    context: Context, data_dict: DataDict, is_org: bool = False
):

    if not context.get("skip_validation"):
        schema = context.get("schema", schema_.default_follow_user_schema())
        data_dict, errors = _validate(data_dict, schema, context)
        if errors:
            raise ValidationError(errors)

    # Get the list of UserFollowingGroup objects.
    user_id = _get_or_bust(data_dict, "id")
    followees = model.UserFollowingGroup.followee_list(user_id)

    # Convert the UserFollowingGroup objects to a list of Group objects.
    groups = [model.Group.get(followee.object_id) for followee in followees]
    groups = [
        group
        for group in groups
        if group is not None and group.is_organization == is_org
    ]

    # Dictize the list of Group objects.
    return [model_dictize.group_dictize(group, context) for group in groups]


def user_update(context: Context, data_dict: DataDict) -> ActionResult.UserUpdate:
    """Update a user account.

    Normal users can only update their own user accounts. Sysadmins can update
    any user account and modify existing usernames.

    .. note:: Update methods may delete parameters not explicitly provided in the
        data_dict. If you want to edit only a specific attribute use `user_patch`
        instead.

    For further parameters see
    :py:func:`~ckan.logic.action.user.user_create`.

    :param id: the name or id of the user to update
    :type id: string

    :returns: the updated user account
    :rtype: dictionary

    """
    user = context["user"]
    session = context["session"]
    schema = context.get("schema") or schema_.default_update_user_schema()
    id = _get_or_bust(data_dict, "id")

    user_obj = model.User.get(id)
    if user_obj is None:
        raise NotFound(_("User was not found."))
    context["user_obj"] = user_obj

    _check_access("user_update", context, data_dict)

    upload = uploader.get_uploader("user")
    upload.update_data_dict(data_dict, "image_url", "image_upload", "clear_upload")

    data, errors = _validate(data_dict, schema, context)
    if errors:
        session.rollback()
        raise ValidationError(errors)

    # user schema prevents non-sysadmins from providing password_hash
    if "password_hash" in data:
        data["_password"] = data.pop("password_hash")

    user = model_save.user_dict_save(data, context)

    upload.upload(uploader.get_max_image_size())

    if not context.get("defer_commit"):
        with logic.guard_against_duplicated_email(data_dict["email"]):
            model.repo.commit()

    author_obj = model.User.get(context.get("user"))
    include_plugin_extras = False
    if author_obj:
        include_plugin_extras = author_obj.sysadmin and "plugin_extras" in data
    user_dict = model_dictize.user_dictize(
        user, context, include_plugin_extras=include_plugin_extras
    )

    return user_dict


def user_patch(context: Context, data_dict: DataDict) -> ActionResult.UserPatch:
    """Patch a user

    :param id: the id or name of the user
    :type id: string

    The difference between the update and patch methods is that the patch will
    perform an update of the provided parameters, while leaving all other
    parameters unchanged, whereas the update methods deletes all parameters
    not explicitly provided in the data_dict
    """
    _check_access("user_patch", context, data_dict)

    show_context: Context = _fresh_context(context)

    user_dict = _get_action("user_show")(
        show_context, {"id": _get_or_bust(data_dict, "id")}
    )

    patched = dict(user_dict)
    patched.pop("display_name", None)
    patched.update(data_dict)
    return _get_action("user_update")(context, patched)


def user_delete(context: Context, data_dict: DataDict) -> ActionResult.UserDelete:
    """Delete a user.

    Only sysadmins can delete users.

    :param id: the id or name of the user to delete
    :type id: string
    """

    _check_access("user_delete", context, data_dict)

    user_id = _get_or_bust(data_dict, "id")
    user = model.User.get(user_id)

    if user is None:
        raise NotFound('User "{id}" was not found.'.format(id=user_id))

    user.delete()

    user_memberships = (
        model.Session.query(model.Member).filter(model.Member.table_id == user.id).all()
    )

    for membership in user_memberships:
        membership.delete()

    datasets_where_user_is_collaborator = (
        model.Session.query(model.PackageMember)
        .filter(model.PackageMember.user_id == user.id)
        .all()
    )
    for collaborator in datasets_where_user_is_collaborator:
        collaborator.delete()

    model.repo.commit()


def _unfollow(
    context: Context,
    data_dict: DataDict,
    schema: Schema,
    FollowerClass: Type["ModelFollowingModel[Any, Any]"],
):

    userobj = model.User.get(context["user"])
    if not userobj:
        raise NotFound(_("User not found"))

    follower_id = userobj.id

    validated_data_dict, errors = validate(data_dict, schema, context)
    if errors:
        msg = _("Error validating the schema of the object to unfollow.")
        raise ValidationError(msg)

    object_id = validated_data_dict.get("id")
    follower_id = userobj.id
    follower_obj = FollowerClass.get(follower_id, object_id)
    if follower_obj is None:
        return

    follower_obj.delete()

    model.repo.commit()


def unfollow_user(context: Context, data_dict: DataDict) -> None:
    """Stop following a user.

    :param id: the id or name of the user to stop following
    :type id: string

    """
    schema = context.get("schema") or (schema_.default_follow_user_schema())
    _check_access("unfollow_user", context, data_dict)
    _unfollow(context, data_dict, schema, model.UserFollowingUser)


def unfollow_dataset(context: Context, data_dict: DataDict) -> None:
    """Stop following a dataset.

    :param id: the id or name of the dataset to stop following
    :type id: string

    """
    schema = context.get("schema") or (schema_.default_follow_dataset_schema())
    _check_access("unfollow_dataset", context, data_dict)
    _unfollow(context, data_dict, schema, model.UserFollowingDataset)


def unfollow_group(context: Context, data_dict: DataDict) -> None:
    """Stop following a group.

    :param id: the id or name of the group to stop following
    :type id: string

    """
    schema = context.get("schema", schema_.default_follow_group_schema())
    _check_access("unfollow_group", context, data_dict)
    _unfollow(context, data_dict, schema, model.UserFollowingGroup)


def api_token_revoke(
    context: Context, data_dict: DataDict
) -> ActionResult.ApiTokenRevoke:
    """Delete API Token.

    :param string token: Token to remove (required if `jti` not specified).
    :param string jti: ID of the token to remove (overrides `token` if
        specified).

    .. versionadded:: 3.0
    """
    jti = data_dict.get("jti")
    if not jti:
        token = _get_or_bust(data_dict, "token")
        decoders = plugins.PluginImplementations(plugins.IApiToken)
        for plugin in decoders:
            data = plugin.decode_api_token(token)
            if data:
                break
        else:
            data = api_token.decode(token)

        if data:
            jti = data.get("jti")

    _check_access("api_token_revoke", context, {"jti": jti})
    model.ApiToken.revoke(jti)


@maintain.deprecated(
    "Use `ckan.plugins.toolkit.get_site_user()` instead.", since="3.0.0"
)
def get_site_user(context: Context, data_dict: DataDict) -> ActionResult.GetSiteUser:
    """Return the ckan site user.

    .. deprecated:: 3.0
        Use :py:func:`ckan.plugins.toolkit.get_site_user` instead.

    Only internal services are allowed to call this action.
    """
    _check_access("get_site_user", context, data_dict)
    user = model.User.get_site_user()
    return {
        "name": user.name,
        "id": user.id,
        "apikey": user.apikey,
    }
