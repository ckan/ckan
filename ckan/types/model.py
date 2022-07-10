# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, Callable, ClassVar, Type
from typing_extensions import Protocol

from sqlalchemy.orm.scoping import ScopedSession
from sqlalchemy.orm import Query, sessionmaker
from sqlalchemy import Table

if TYPE_CHECKING:
    import ckan.model as _model  # noqa


AlchemySession = ScopedSession
Query = Query


class Meta(Protocol):
    create_local_session: sessionmaker


class Model(Protocol):
    # Activity: ClassVar[Type["_model.Activity"]]
    ApiToken: ClassVar[Type["_model.ApiToken"]]
    Dashboard: ClassVar[Type["_model.Dashboard"]]
    DomainObject: ClassVar[Type["_model.DomainObject"]]
    Group: ClassVar[Type["_model.Group"]]
    Member: ClassVar[Type["_model.Member"]]
    Package: ClassVar[Type["_model.Package"]]
    PackageMember: ClassVar[Type["_model.PackageMember"]]
    PackageRelationship: ClassVar[Type["_model.PackageRelationship"]]
    PackageTag: ClassVar[Type["_model.PackageTag"]]
    Resource: ClassVar[Type["_model.Resource"]]
    ResourceView: ClassVar[Type["_model.ResourceView"]]
    State: ClassVar[Type["_model.State"]]
    System: ClassVar[Type["_model.System"]]
    Tag: ClassVar[Type["_model.Tag"]]
    TaskStatus: ClassVar[Type["_model.TaskStatus"]]
    TrackingSummary: ClassVar[Type["_model.TrackingSummary"]]
    User: ClassVar[Type["_model.User"]]
    AnonymousUser: ClassVar[Type["_model.AnonymousUser"]]
    UserFollowingDataset: ClassVar[Type["_model.UserFollowingDataset"]]
    UserFollowingGroup: ClassVar[Type["_model.UserFollowingGroup"]]
    UserFollowingUser: ClassVar[Type["_model.UserFollowingUser"]]
    Vocabulary: ClassVar[Type["_model.Vocabulary"]]

    group_table: ClassVar[Table]
    member_table: ClassVar[Table]
    package_extra_table: ClassVar[Table]
    package_relationship_table: ClassVar[Table]
    package_table: ClassVar[Table]
    package_tag_table: ClassVar[Table]
    resource_table: ClassVar[Table]
    tag_table: ClassVar[Table]
    term_translation_table: ClassVar[Table]

    Session: ClassVar[AlchemySession]
    meta: ClassVar[Meta]

    set_system_info: Callable[[str, str], bool]
    repo: ClassVar["_model.Repository"]
