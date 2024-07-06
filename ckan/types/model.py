from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type
from typing_extensions import Protocol

from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.query import Query
from sqlalchemy import Table

if TYPE_CHECKING:
    import ckan.model as _model  # noqa

__all__ = [
    "Model", "AlchemySession", "Query",
]

AlchemySession = ScopedSession


class Meta(Protocol):
    create_local_session: "sessionmaker[Session]"


class Model(Protocol):
    # Activity: ClassVar[Type["_model.Activity"]]
    ApiToken: Type["_model.ApiToken"]
    Dashboard: Type["_model.Dashboard"]
    DomainObject: Type["_model.DomainObject"]
    Group: Type["_model.Group"]
    Member: Type["_model.Member"]
    Package: Type["_model.Package"]
    PackageMember: Type["_model.PackageMember"]
    PackageRelationship: Type["_model.PackageRelationship"]
    PackageTag: Type["_model.PackageTag"]
    Resource: Type["_model.Resource"]
    ResourceView: Type["_model.ResourceView"]
    State: Type["_model.State"]
    System: Type["_model.System"]
    Tag: Type["_model.Tag"]
    TaskStatus: Type["_model.TaskStatus"]
    User: Type["_model.User"]
    AnonymousUser: Type["_model.AnonymousUser"]
    UserFollowingDataset: Type["_model.UserFollowingDataset"]
    UserFollowingGroup: Type["_model.UserFollowingGroup"]
    UserFollowingUser: Type["_model.UserFollowingUser"]
    Vocabulary: Type["_model.Vocabulary"]

    group_table: Table
    group_extra_table: Table
    member_table: Table
    package_extra_table: Table
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
