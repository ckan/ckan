from __future__ import annotations

from typing import TYPE_CHECKING, Any
from typing_extensions import Protocol, TypeAlias

from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.query import Query
from sqlalchemy import Table

if TYPE_CHECKING:
    import ckan.model as _model  # noqa

__all__ = [
    "Model", "AlchemySession", "Query",
]

AlchemySession = ScopedSession[Any]


class Meta(Protocol):
    create_local_session: "sessionmaker[Session]"


class Model(Protocol):
    # Activity: ClassVar[Type["_model.Activity"]]
    ApiToken: TypeAlias = "_model.ApiToken"
    Dashboard: TypeAlias = "_model.Dashboard"
    DomainObject: TypeAlias = "_model.DomainObject"
    Group: TypeAlias = "_model.Group"
    Member: TypeAlias = "_model.Member"
    Package: TypeAlias = "_model.Package"
    PackageMember: TypeAlias = "_model.PackageMember"
    PackageRelationship: TypeAlias = "_model.PackageRelationship"
    PackageTag: TypeAlias = "_model.PackageTag"
    Resource: TypeAlias = "_model.Resource"
    ResourceView: TypeAlias = "_model.ResourceView"
    State: TypeAlias = "_model.State"
    System: TypeAlias = "_model.System"
    Tag: TypeAlias = "_model.Tag"
    TaskStatus: TypeAlias = "_model.TaskStatus"
    User: TypeAlias = "_model.User"
    AnonymousUser: TypeAlias = "_model.AnonymousUser"
    UserFollowingDataset: TypeAlias = "_model.UserFollowingDataset"
    UserFollowingGroup: TypeAlias = "_model.UserFollowingGroup"
    UserFollowingUser: TypeAlias = "_model.UserFollowingUser"
    Vocabulary: TypeAlias = "_model.Vocabulary"

    group_table: Table
    member_table: Table
    package_relationship_table: Table
    package_table: Table
    package_tag_table: Table
    resource_table: Table
    tag_table: Table
    term_translation_table: Table

    Session: AlchemySession
    meta: Meta | Any

    repo: "_model.Repository"

    @staticmethod
    def set_system_info(key: str, value: str) -> bool:
        ...
