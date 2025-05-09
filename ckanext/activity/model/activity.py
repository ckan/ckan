# encoding: utf-8
from __future__ import annotations

import datetime
from typing import Any, Iterable, Optional, Type, TypeVar, Union, List, Tuple
from typing_extensions import TypeAlias

from sqlalchemy.orm import relationship, backref, Mapped
from sqlalchemy import (
    types,
    Column,
    ForeignKey,
    or_,
    and_,
    not_,
    text,
    select,
    literal,
    Index,
    Table,
)

from ckan.common import config
import ckan.model as model
import ckan.model.meta as meta
import ckan.model.domain_object as domain_object
import ckan.model.types as _types
from ckan.model.base import BaseModel
from ckan.lib.dictization import table_dictize
from ckan.lib.maintain import deprecated
from ckan.types import Context, Query  # noqa
from ckan.lib.plugins import get_permission_labels


__all__ = ["Activity", "ActivityDetail"]

TActivityDetail = TypeVar("TActivityDetail", bound="ActivityDetail")
QActivity: TypeAlias = "Query[Activity]"


class Activity(domain_object.DomainObject, BaseModel):
    __table__ = Table(
        "activity",
        BaseModel.metadata,
        Column("id", types.UnicodeText, primary_key=True, default=_types.make_uuid),
        Column("timestamp", types.DateTime),
        Column("user_id", types.UnicodeText),
        Column("object_id", types.UnicodeText),
        Column("activity_type", types.UnicodeText),
        Column("data", _types.JsonDictType),
        Column("permission_labels", types.Text),
    )

    # the line below handles cases when activity table was already loaded into
    # metadata state(via stats extension). Can be removed if stats stop using
    # Table object.
    __table_args__ = {"extend_existing": True}

    id: Mapped[str]

    timestamp: Mapped[datetime.datetime]
    user_id: Mapped[Optional[str]]
    object_id: Mapped[Optional[str]]
    activity_type: Mapped[Optional[str]]
    data: Mapped[dict[str, Any]]
    permission_labels: Mapped[Optional[list[str]]]

    def __init__(
        self,
        user_id: str,
        object_id: str,
        activity_type: str,
        data: Optional[dict[str, Any]] = None,
        permission_labels: Optional[list[str]] = None
    ) -> None:
        self.id = _types.make_uuid()
        self.timestamp = datetime.datetime.utcnow()
        self.user_id = user_id
        self.object_id = object_id
        self.activity_type = activity_type
        self.permission_labels = permission_labels
        if data is None:
            self.data = {}
        else:
            self.data = data

    @classmethod
    def get(cls, id: str) -> Optional["Activity"]:
        """Returns an Activity object referenced by its id."""
        if not id:
            return None

        return meta.Session.get(cls, id)

    @classmethod
    @deprecated(
        "Use `activity_create` instead of Activity.activity_stream_item",
        since="2.11.0"
    )
    def activity_stream_item(
        cls, pkg: model.Package, activity_type: str, user_id: str
    ) -> Optional["Activity"]:
        """DEPRECATED. Create an activity for a package.

        Use `activity_create` API action instead.
        """
        import ckan.model
        import ckan.logic

        assert activity_type in ("new", "changed"), str(activity_type)

        # Handle 'deleted' objects.
        # When the user marks a package as deleted this comes through here as
        # a 'changed' package activity. We detect this and change it to a
        # 'deleted' activity.
        if activity_type == "changed" and pkg.state == "deleted":
            if (
                meta.Session.query(cls)
                .filter_by(object_id=pkg.id, activity_type="deleted")
                .all()
            ):
                # A 'deleted' activity for this object has already been emitted
                # FIXME: What if the object was deleted and then activated
                # again?
                return None
            else:
                # Emit a 'deleted' activity for this object.
                activity_type = "deleted"

        # Set activity permission labels
        permission_labels = get_permission_labels().get_dataset_labels(pkg)

        try:
            # We save the entire rendered package dict so we can support
            # viewing the past packages from the activity feed.
            dictized_package = ckan.logic.get_action("package_show")(
                {
                    # avoid ckanext-multilingual translating it
                    "for_view": False,
                    "ignore_auth": True,
                },
                {"id": pkg.id},
            )
        except ckan.logic.NotFound:
            # This happens if this package is being purged and therefore has no
            # current revision.
            # TODO: Purge all related activity stream items when a model object
            # is purged.
            return None

        actor = meta.Session.get(ckan.model.User, user_id)

        return cls(
            user_id,
            pkg.id,
            "%s package" % activity_type,
            {
                "package": dictized_package,
                # We keep the acting user name around so that actions can be
                # properly displayed even if the user is deleted in the future.
                "actor": actor.name if actor else None,
            },
            permission_labels
        )


Index('idx_activity_user_id',
      Activity.__table__.c.user_id, Activity.__table__.c.timestamp)
Index('idx_activity_object_id',
      Activity.__table__.c.object_id, Activity.__table__.c.timestamp)


def activity_dictize(activity: Activity, context: Context) -> dict[str, Any]:
    return table_dictize(activity, context)


def activity_list_dictize(
    activity_list: Iterable[Activity], context: Context
) -> list[dict[str, Any]]:
    return [activity_dictize(activity, context) for activity in activity_list]


# deprecated
class ActivityDetail(domain_object.DomainObject, BaseModel):
    __tablename__ = "activity_detail"
    id = Column(
        "id", types.UnicodeText, primary_key=True, default=_types.make_uuid
    )
    activity_id = Column(
        "activity_id", types.UnicodeText, ForeignKey("activity.id")
    )
    object_id = Column("object_id", types.UnicodeText)
    object_type = Column("object_type", types.UnicodeText)
    activity_type = Column("activity_type", types.UnicodeText)
    data = Column("data", _types.JsonDictType)

    activity: Mapped[Activity] = relationship(
        Activity,
        backref=backref("activity_detail", cascade="all, delete-orphan"),
    )

    def __init__(
        self,
        activity_id: str,
        object_id: str,
        object_type: str,
        activity_type: str,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        self.activity_id = activity_id
        self.object_id = object_id
        self.object_type = object_type
        self.activity_type = activity_type
        if data is None:
            self.data = {}
        else:
            self.data = data

    @classmethod
    def by_activity_id(
        cls: Type[TActivityDetail], activity_id: str
    ) -> list["TActivityDetail"]:
        return (
            model.Session.query(cls).filter_by(activity_id=activity_id).all()
        )


Index('idx_activity_detail_activity_id',
      ActivityDetail.__table__.c.activity_id)


def _activities_limit(
    q: QActivity,
    limit: int,
    offset: Optional[int] = None,
    revese_order: Optional[bool] = False,
) -> QActivity:
    """
    Return an SQLAlchemy query for all activities at an offset with a limit.

    revese_order:
        if we want the last activities before a date, we must reverse the
        order before limiting.
    """
    if revese_order:
        q = q.order_by(Activity.timestamp)
    else:
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.order_by(Activity.timestamp.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)
    return q


def _activities_union_all(*qlist: QActivity) -> QActivity:
    """
    Return union of two or more activity queries sorted by timestamp,
    and remove duplicates
    """
    q, *rest = qlist
    for query in rest:
        q = q.union(query)

    return q


def _activities_from_user_query(user_id: Union[str, List[str]]) -> QActivity:
    """Return an SQLAlchemy query for all activities from user_id."""
    q = model.Session.query(Activity)
    q = q.filter(Activity.user_id.in_(_to_list(user_id)))
    return q


def _activities_about_user_query(user_id: Union[str, List[str]]) -> QActivity:
    """Return an SQLAlchemy query for all activities about user_id."""
    q = model.Session.query(Activity)
    q = q.filter(Activity.object_id.in_(_to_list(user_id)))
    return q


def _user_activity_query(
        user_id: Union[str, List[str]], limit: int) -> QActivity:
    """Return an SQLAlchemy query for all activities from or about user_id."""
    q1 = _activities_limit(_activities_from_user_query(user_id), limit)
    q2 = _activities_limit(_activities_about_user_query(user_id), limit)
    return _activities_union_all(q1, q2)


def user_activity_list(
    user_id: str,
    limit: int,
    offset: int,
    after: Optional[datetime.datetime] = None,
    before: Optional[datetime.datetime] = None,
    user_permission_labels: Optional[list[str]] = None,
) -> list[Activity]:
    """Return user_id's public activity stream.

    Return a list of all activities from or about the given user, i.e. where
    the given user is the subject or object of the activity, e.g.:

    "{USER} created the dataset {DATASET}"
    "{OTHER_USER} started following {USER}"
    etc.

    """
    q1 = _activities_from_user_query(user_id)
    q2 = _activities_about_user_query(user_id)

    q = _activities_union_all(q1, q2)

    q = _filter_activitites_from_users(q)

    q = _filter_activities_by_permission_labels(q, user_permission_labels)

    if after:
        q = q.filter(Activity.timestamp > after)
    if before:
        q = q.filter(Activity.timestamp < before)

    # revert sort queries for "only before" queries
    revese_order = after and not before
    if revese_order:
        q = q.order_by(Activity.timestamp)
    else:
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.order_by(Activity.timestamp.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

    results = q.all()

    # revert result if required
    if revese_order:
        results.reverse()

    return results


def _to_list(vals: Union[List[str], Tuple[str], str]):
    if isinstance(vals, (list, tuple)):
        return vals
    return [vals]


def _package_activity_query(package_id: Union[str, List[str]]) -> QActivity:
    """Return an SQLAlchemy query for all activities about package_id."""
    q = model.Session.query(Activity)\
        .filter(Activity.object_id.in_(_to_list(package_id)))
    return q


def package_activity_list(
    package_id: str,
    limit: int,
    offset: Optional[int] = None,
    after: Optional[datetime.datetime] = None,
    before: Optional[datetime.datetime] = None,
    include_hidden_activity: bool = False,
    activity_types: Optional[list[str]] = None,
    exclude_activity_types: Optional[list[str]] = None,
    user_permission_labels: Optional[list[str]] = None,
) -> list[Activity]:
    """Return the given dataset (package)'s public activity stream.

    Returns all activities about the given dataset, i.e. where the given
    dataset is the object of the activity, e.g.:

    "{USER} created the dataset {DATASET}"
    "{USER} updated the dataset {DATASET}"
    etc.

    """
    q = _package_activity_query(package_id)

    if not include_hidden_activity:
        q = _filter_activitites_from_users(q)

    if activity_types:
        q = _filter_activitites_from_type(
            q, include=True, types=activity_types
        )
    elif exclude_activity_types:
        q = _filter_activitites_from_type(
            q, include=False, types=exclude_activity_types
        )

    q = _filter_activities_by_permission_labels(q, user_permission_labels)

    if after:
        q = q.filter(Activity.timestamp > after)
    if before:
        q = q.filter(Activity.timestamp < before)

    # revert sort queries for "only before" queries
    revese_order = after and not before
    if revese_order:
        q = q.order_by(Activity.timestamp)
    else:
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.order_by(Activity.timestamp.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

    results = q.all()

    # revert result if required
    if revese_order:
        results.reverse()

    return results


def _group_activity_query(group_id: Union[str, List[str]]) -> QActivity:
    """Return an SQLAlchemy query for all activities about group_id.

    Returns a query for all activities whose object is either the group itself
    or one of the group's datasets.

    """

    groups = _to_list(group_id)
    q: QActivity = (
        model.Session.query(Activity)
        .outerjoin(model.Member, Activity.object_id == model.Member.table_id)
        .outerjoin(
            model.Package,
            and_(
                model.Package.id == model.Member.table_id,
                model.Package.private == False,  # noqa
            ),
        )
        .filter(
            # We only care about activity either on the group itself or on
            # packages within that group.  FIXME: This means that activity that
            # occured while a package belonged to a group but was then removed
            # will not show up. This may not be desired but is consistent with
            # legacy behaviour.
            or_(
                # active dataset in the group
                and_(
                    model.Member.group_id.in_(groups),
                    model.Member.state == "active",
                    model.Package.state == "active",
                ),
                # deleted dataset in the group
                and_(
                    model.Member.group_id.in_(groups),
                    model.Member.state == "deleted",
                    model.Package.state == "deleted",
                ),
                # (we want to avoid showing changes to an active dataset that
                # was once in this group)
                # activity the the group itself
                Activity.object_id.in_(groups),
            )
        )
    )

    return q


def _organization_activity_query(org_id: str) -> QActivity:
    """Return an SQLAlchemy query for all activities about org_id.

    Returns a query for all activities whose object is either the org itself
    or one of the org's datasets.

    """

    org = model.Group.get(org_id)
    if not org or not org.is_organization:
        # Return a query with no results.
        return model.Session.query(Activity).filter(text('0=1'))

    q: QActivity = (
        model.Session.query(Activity)
        .filter(
            # We only care about activity either on the the org itself or on
            # packages within that org.
            # FIXME: This means that activity that occured while a package
            # belonged to a org but was then removed will not show up. This may
            # not be desired but is consistent with legacy behaviour.
            #
            # Use subselect instead of outer join so that it can all
            # be indexable
            Activity.object_id.in_(
                select(model.Package.id)
                .where(
                    and_(
                        model.Package.private == False,  # noqa
                        model.Package.owner_org == org_id
                    )
                )
                .union(
                    # select the org itself
                    select(literal(org_id))
                )
            )
        )
    )

    return q


def group_activity_list(
    group_id: str,
    limit: int,
    offset: int,
    after: Optional[datetime.datetime] = None,
    before: Optional[datetime.datetime] = None,
    include_hidden_activity: bool = False,
    activity_types: Optional[list[str]] = None,
    user_permission_labels: Optional[list[str]] = None,
) -> list[Activity]:
    """Return the given group's public activity stream.

    Returns activities where the given group or one of its datasets is the
    object of the activity, e.g.:

    "{USER} updated the group {GROUP}"
    "{USER} updated the dataset {DATASET}"
    etc.

    """
    q = _group_activity_query(group_id)

    if not include_hidden_activity:
        q = _filter_activitites_from_users(q)

    if activity_types:
        q = _filter_activitites_from_type(
            q, include=True, types=activity_types
        )

    q = _filter_activities_by_permission_labels(q, user_permission_labels)

    if after:
        q = q.filter(Activity.timestamp > after)
    if before:
        q = q.filter(Activity.timestamp < before)

    # revert sort queries for "only before" queries
    revese_order = after and not before
    if revese_order:
        q = q.order_by(Activity.timestamp)
    else:
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.order_by(Activity.timestamp.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

    results = q.all()

    # revert result if required
    if revese_order:
        results.reverse()

    return results


def organization_activity_list(
    group_id: str,
    limit: int,
    offset: int,
    after: Optional[datetime.datetime] = None,
    before: Optional[datetime.datetime] = None,
    include_hidden_activity: bool = False,
    activity_types: Optional[list[str]] = None,
    user_permission_labels: Optional[list[str]] = None,
) -> list[Activity]:
    """Return the given org's public activity stream.

    Returns activities where the given org or one of its datasets is the
    object of the activity, e.g.:

    "{USER} updated the organization {ORG}"
    "{USER} updated the dataset {DATASET}"
    etc.

    """
    q = _organization_activity_query(group_id)

    if not include_hidden_activity:
        q = _filter_activitites_from_users(q)

    if activity_types:
        q = _filter_activitites_from_type(
            q, include=True, types=activity_types
        )

    q = _filter_activities_by_permission_labels(q, user_permission_labels)

    if after:
        q = q.filter(Activity.timestamp > after)
    if before:
        q = q.filter(Activity.timestamp < before)

    # revert sort queries for "only before" queries
    revese_order = after and not before
    if revese_order:
        q = q.order_by(Activity.timestamp)
    else:
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.order_by(Activity.timestamp.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

    results = q.all()

    # revert result if required
    if revese_order:
        results.reverse()

    return results


def _activities_from_users_followed_by_user_query(
    user_id: str, limit: int
) -> QActivity:
    """Return a query for all activities from users that user_id follows."""

    # Get a list of the users that the given user is following.
    follower_objects = model.UserFollowingUser.followee_list(user_id)
    if not follower_objects:
        # Return a query with no results.
        return model.Session.query(Activity).filter(text("0=1"))

    return _user_activity_query(
        [follower.object_id for follower in follower_objects],
        limit)


def _activities_from_datasets_followed_by_user_query(
    user_id: str, limit: int
) -> QActivity:
    """Return a query for all activities from datasets that user_id follows."""
    # Get a list of the datasets that the user is following.
    follower_objects = model.UserFollowingDataset.followee_list(user_id)
    if not follower_objects:
        # Return a query with no results.
        return model.Session.query(Activity).filter(text("0=1"))

    return _activities_limit(
        _package_activity_query(
            [follower.object_id for follower in follower_objects]),
        limit)


def _activities_from_groups_followed_by_user_query(
    user_id: str, limit: int
) -> QActivity:
    """Return a query for all activities about groups the given user follows.

    Return a query for all activities about the groups the given user follows,
    or about any of the group's datasets. This is the union of
    _group_activity_query(group_id) for each of the groups the user follows.

    """
    # Get a list of the group's that the user is following.
    follower_objects = model.UserFollowingGroup.followee_list(user_id)
    if not follower_objects:
        # Return a query with no results.
        return model.Session.query(Activity).filter(text("0=1"))

    return _activities_limit(
        _group_activity_query(
            [follower.object_id for follower in follower_objects]),
        limit)


def _activities_from_everything_followed_by_user_query(
    user_id: str, limit: int = 0
) -> QActivity:
    """Return a query for all activities from everything user_id follows."""
    q1 = _activities_from_users_followed_by_user_query(user_id, limit)
    q2 = _activities_from_datasets_followed_by_user_query(user_id, limit)
    q3 = _activities_from_groups_followed_by_user_query(user_id, limit)
    return _activities_union_all(q1, q2, q3)


def activities_from_everything_followed_by_user(
    user_id: str, limit: int, offset: int
) -> list[Activity]:
    """Return activities from everything that the given user is following.

    Returns all activities where the object of the activity is anything
    (user, dataset, group...) that the given user is following.

    """
    q = _activities_from_everything_followed_by_user_query(
        user_id, limit + offset
    )
    return _activities_limit(q, limit, offset).all()


def _dashboard_activity_query(user_id: str, limit: int = 0) -> QActivity:
    """Return an SQLAlchemy query for user_id's dashboard activity stream."""
    q1 = _user_activity_query(user_id, limit)
    q2 = _activities_from_everything_followed_by_user_query(user_id, limit)
    return _activities_union_all(q1, q2)


def dashboard_activity_list(
    user_id: str,
    limit: int,
    offset: int,
    before: Optional[datetime.datetime] = None,
    after: Optional[datetime.datetime] = None,
    user_permission_labels: Optional[list[str]] = None,
) -> list[Activity]:
    """Return the given user's dashboard activity stream.

    Returns activities from the user's public activity stream, plus
    activities from everything that the user is following.

    This is the union of user_activity_list(user_id) and
    activities_from_everything_followed_by_user(user_id).

    """
    q = _dashboard_activity_query(user_id)

    q = _filter_activitites_from_users(q)

    q = _filter_activities_by_permission_labels(q, user_permission_labels)

    if after:
        q = q.filter(Activity.timestamp > after)
    if before:
        q = q.filter(Activity.timestamp < before)

    # revert sort queries for "only before" queries
    revese_order = after and not before
    if revese_order:
        q = q.order_by(Activity.timestamp)
    else:
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.order_by(Activity.timestamp.desc())

    if offset:
        q = q.offset(offset)
    if limit:
        q = q.limit(limit)

    results = q.all()

    # revert result if required
    if revese_order:
        results.reverse()

    return results


def _changed_packages_activity_query() -> QActivity:
    """Return an SQLAlchemy query for all changed package activities.

    Return a query for all activities with activity_type '*package', e.g.
    'new_package', 'changed_package', 'deleted_package'.

    """
    q = model.Session.query(Activity)
    q = q.filter(Activity.activity_type.endswith("package"))
    return q


def recently_changed_packages_activity_list(
    limit: int,
    offset: int,
    user_permission_labels: Optional[list[str]] = None,
) -> list[Activity]:
    """Return the site-wide stream of recently changed package activities.

    This activity stream includes recent 'new package', 'changed package' and
    'deleted package' activities for the whole site.

    """
    q = _changed_packages_activity_query()

    q = _filter_activitites_from_users(q)

    q = _filter_activities_by_permission_labels(q, user_permission_labels)

    return _activities_limit(q, limit, offset).all()


def _filter_activitites_from_users(q: QActivity) -> QActivity:
    """
    Adds a filter to an existing query object to avoid activities from users
    defined in :ref:`ckan.hide_activity_from_users` (defaults to the site user)
    """
    users_to_avoid = _activity_stream_get_filtered_users()
    if users_to_avoid:
        # type_ignore_reason: incomplete SQLAlchemy types
        q = q.filter(Activity.user_id.notin_(users_to_avoid))

    return q


def _filter_activitites_from_type(
    q: QActivity, types: Iterable[str], include: bool = True
):
    """Adds a filter to an existing query object to include or exclude
    (include=False) activities based on a list of types.

    """
    if include:
        q = q.filter(Activity.activity_type.in_(types))
    else:
        q = q.filter(Activity.activity_type.notin_(types))
    return q


def _activity_stream_get_filtered_users() -> list[str]:
    """
    Get the list of users from the :ref:`ckan.hide_activity_from_users` config
    option and return a list of their ids. If the config is not specified,
    returns the id of the site user.
    """
    users_list = config.get("ckan.hide_activity_from_users")
    if not users_list:
        from ckan.logic import get_action

        context: Context = {"ignore_auth": True}
        site_user = get_action("get_site_user")(context, {})
        users_list = [site_user.get("name")]

    return model.User.user_ids_for_name_or_id(users_list)


def _filter_activities_by_permission_labels(
    q: QActivity,
    user_permission_labels: Optional[list[str]] = None,
):
    """Adds a filter to an existing query object to
    exclude package activities based on user permissions.
    """

    # `user_permission_labels` is None when user is sysadmin
    if user_permission_labels is not None:
        # User can access non-package activities since they don't have labels
        q = q.filter(
            or_(
                or_(Activity.activity_type.is_(None),
                    not_(Activity.activity_type.endswith("package"))),
                Activity.permission_labels.op('&&')(
                    user_permission_labels)
            )
        )

    return q
